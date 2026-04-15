"""
MessageRouter — unified entry point for all incoming messages.

Normalises raw events from any channel into a single unified format,
runs them through the channel-agnostic AI pipeline, then:
  - Dispatches reply to the correct channel API  (AUTO_REPLY_<CHANNEL>=True)
  - Saves to SQLite for dashboard review          (AUTO_REPLY_<CHANNEL>=False)
  - Fires N8N sub-workflow notifications          (fire-and-forget)

Unified message format:
{
    "channel":      "facebook" | "line",
    "message_id":   str,      # platform message/comment ID
    "user_id":      str,      # platform user ID
    "user_name":    str,      # display name
    "text":         str,      # raw message text
    "reply_token":  str,      # LINE only
    "comment_id":   str,      # Facebook only
    "post_id":      str,      # Facebook only
    "timestamp":    str,      # ISO 8601
}

N8N sub-workflows (fire-and-forget, never blocks pipeline):
  Workflow 03  /webhook/lead-capture  → POTENTIAL_BUYER / GENERAL_INQUIRY
  Workflow 04  /webhook/owner-notify  → COMPLAINT / escalated

Fallback: this router IS the fallback when N8N is down. All processing
is done locally; N8N calls simply log at DEBUG and are silently skipped.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests as _requests

from app.core import database as db
from app.integrations.facebook_api import FacebookAPI
from app.integrations.line_api import LineAPI
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Intents that trigger lead capture in N8N workflow 03
_LEAD_INTENTS = {"POTENTIAL_BUYER", "GENERAL_INQUIRY"}
# Intents / states that trigger owner notification via N8N workflow 04
_NOTIFY_INTENTS = {"COMPLAINT"}


def _auto_reply(channel: str) -> bool:
    """
    Check if auto-reply is enabled for a specific channel.

    Priority:
      1. AUTO_REPLY_FACEBOOK / AUTO_REPLY_LINE  (per-channel)
      2. AUTO_REPLY                              (global fallback)
    """
    key = f"AUTO_REPLY_{channel.upper()}"
    val = os.getenv(key, os.getenv("AUTO_REPLY", "False"))
    return val.strip().lower() == "true"


def _n8n_base_url() -> str:
    return os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")


class MessageRouter:
    """
    Single entry point for messages from all channels.

    The analyzer and generator are channel-agnostic — they operate on plain
    text and return plain text. All channel-specific I/O happens here.

    Usage:
        router = MessageRouter()
        reply = router.route(unified_msg)
    """

    def __init__(self) -> None:
        db.init_db()
        self.analyzer = CommentAnalyzer()
        self.generator = ReplyGenerator(client=self.analyzer.client)
        self.fb_api = FacebookAPI()
        self.line_api = LineAPI()

    def route(self, msg: dict) -> Optional[str]:
        """
        Process a unified message and dispatch the reply.

        Returns the generated reply text, or None if skipped / failed.
        """
        channel = msg.get("channel", "unknown")
        text = msg.get("text", "").strip()
        user_name = msg.get("user_name", "")

        if not text:
            logger.debug("MessageRouter: empty text — skipped | channel=%s", channel)
            return None

        logger.info(
            "MessageRouter | channel=%s user=%s text=%.60s…",
            channel, user_name, text,
        )

        try:
            # ── 1. Channel-agnostic AI pipeline ──────────────────────
            analysis = self.analyzer.analyze(text)
            logger.info(
                "Analysis | intent=%s confidence=%.2f",
                analysis.intent, analysis.confidence,
            )

            result = self.generator.generate(analysis)

            if result.was_skipped:
                logger.info("Reply skipped | intent=SPAM | channel=%s", channel)
                return None

            if not result.reply and not result.is_escalated:
                logger.warning(
                    "No reply generated | channel=%s error=%s", channel, result.error
                )
                return None

            # ── 2. Persist to SQLite ──────────────────────────────────
            record = self._build_record(msg, analysis, result)

            if _auto_reply(channel):
                self._dispatch(msg, result.reply, analysis)
                record["status"] = "sent"
            else:
                record["status"] = "pending"

            db.save_message(record)

            # ── 3. N8N sub-workflows (fire-and-forget) ────────────────
            self._notify_n8n(msg, analysis, result)

            return result.reply or None

        except Exception as exc:
            logger.error("MessageRouter unexpected error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Channel dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, msg: dict, reply: str, analysis) -> None:
        """Send reply immediately via the correct channel API."""
        channel = msg.get("channel", "")

        if channel == "facebook":
            comment_id = msg.get("comment_id", "")
            if comment_id:
                self.fb_api.post_comment_reply(comment_id, reply)
                logger.info("FB reply sent | comment_id=%s", comment_id)
            else:
                logger.warning("FB auto-reply skipped: no comment_id")

        elif channel == "line":
            reply_token = msg.get("reply_token", "")
            user_id = msg.get("user_id", "")
            self.line_api.reply_message(reply_token, reply, user_id=user_id)

        else:
            logger.warning("Unknown channel '%s' — reply not sent", channel)

    # ------------------------------------------------------------------
    # N8N sub-workflow notifications
    # ------------------------------------------------------------------

    def _notify_n8n(self, msg: dict, analysis, result) -> None:
        """Fire N8N sub-workflow POSTs after processing. Never raises."""
        if analysis.intent in _LEAD_INTENTS:
            self._post_to_n8n(
                "/webhook/lead-capture",
                {
                    "channel":    msg.get("channel"),
                    "user_id":    msg.get("user_id"),
                    "user_name":  msg.get("user_name"),
                    "text":       msg.get("text"),
                    "intent":     analysis.intent,
                    "confidence": round(analysis.confidence, 2),
                    "sentiment":  analysis.sentiment,
                    "timestamp":  msg.get("timestamp", datetime.now().isoformat()),
                },
                label="lead-capture",
            )

        if analysis.intent in _NOTIFY_INTENTS or result.is_escalated:
            self._post_to_n8n(
                "/webhook/owner-notify",
                {
                    "channel":      msg.get("channel"),
                    "user_id":      msg.get("user_id"),
                    "user_name":    msg.get("user_name"),
                    "text":         msg.get("text"),
                    "intent":       analysis.intent,
                    "is_escalated": result.is_escalated,
                    "sentiment":    analysis.sentiment,
                    "key_signals":  analysis.key_signals,
                    "timestamp":    msg.get("timestamp", datetime.now().isoformat()),
                },
                label="owner-notify",
            )

    def _post_to_n8n(self, path: str, payload: dict, label: str = "") -> None:
        """Fire-and-forget POST to N8N. Silently ignores all errors."""
        url = _n8n_base_url() + path
        try:
            resp = _requests.post(url, json=payload, timeout=5)
            logger.debug("N8N %s | status=%d", label, resp.status_code)
        except Exception as exc:
            logger.debug("N8N %s unreachable (fallback mode): %s", label, exc)

    # ------------------------------------------------------------------
    # Record builder
    # ------------------------------------------------------------------

    def _build_record(self, msg: dict, analysis, result) -> dict:
        """Build the dict passed to db.save_message()."""
        return {
            "id":          msg.get("message_id", ""),
            "timestamp":   msg.get("timestamp", datetime.now().isoformat()),
            "channel":     msg.get("channel", "unknown"),
            "user_id":     msg.get("user_id", ""),
            "user_name":   msg.get("user_name", ""),
            "text":        msg.get("text", ""),
            "intent":      analysis.intent,
            "confidence":  round(analysis.confidence, 2),
            "sentiment":   analysis.sentiment,
            "key_signals": analysis.key_signals,
            "reply":       result.reply,
            "is_escalated": result.is_escalated,
            "comment_id":  msg.get("comment_id", ""),
            "post_id":     msg.get("post_id", ""),
            "error":       result.error or analysis.error,
        }
