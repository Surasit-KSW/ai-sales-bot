"""
LINE Webhook Integration.

Handles incoming events from the LINE Messaging API:

  POST /webhook/line — All LINE bot events (messages, follows, etc.)
                        Must verify X-Line-Signature on every request.
                        Returns HTTP 200 immediately (LINE requirement).

Event types handled:
  TextMessage  → AI pipeline → reply
  FollowEvent  → welcome message
  UnfollowEvent → log only
  PostbackEvent → placeholder (Phase 2)
  Everything else → silently ignored

Reference: https://developers.line.biz/en/docs/messaging-api/receiving-messages/
"""

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.integrations.line_api import LineAPI
from app.services.message_router import MessageRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Welcome message sent when a user first follows the LINE OA
_WELCOME_TEXT = (
    "สวัสดีค่ะ! ยินดีต้อนรับสู่ {shop_name} 🎉\n\n"
    "พิมพ์ถามได้เลยนะคะ เช่น:\n"
    "• ราคาสินค้า / โปรโมชั่น\n"
    "• สอบถามสินค้า\n"
    "• ช่องทางสั่งซื้อ\n\n"
    "ทีมงานพร้อมตอบทุกวัน 😊"
)

# Lazily initialised — avoids Ollama startup delay at import time
_router: MessageRouter | None = None
_line_api: LineAPI | None = None


def _get_router() -> MessageRouter:
    global _router
    if _router is None:
        _router = MessageRouter()
    return _router


def _get_line_api() -> LineAPI:
    global _line_api
    if _line_api is None:
        _line_api = LineAPI()
    return _line_api


def _get_channel_secret() -> str:
    return os.getenv("LINE_CHANNEL_SECRET", "")


# ---------------------------------------------------------------------------
# POST /webhook/line
# ---------------------------------------------------------------------------

@router.post("/webhook/line", status_code=200)
async def line_webhook(request: Request) -> dict[str, Any]:
    """
    Receive and process all LINE bot events.

    LINE requires HTTP 200 to be returned quickly — we process events
    synchronously but keep handlers lightweight to stay within LINE's
    timeout window.
    """
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    # ── Signature verification ─────────────────────────────────────────
    channel_secret = _get_channel_secret()
    if not channel_secret:
        logger.error("LINE_CHANNEL_SECRET is not set")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if not _verify_signature(channel_secret, body, signature):
        logger.warning("LINE webhook: invalid X-Line-Signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # ── Parse events ───────────────────────────────────────────────────
    try:
        from linebot.v3.webhook import WebhookParser
        from linebot.v3.exceptions import InvalidSignatureError

        parser = WebhookParser(channel_secret)
        # Pass empty string for signature — we already verified manually above
        # so we parse without re-verification (body is bytes, parser needs str)
        events = parser.parse(body.decode("utf-8"), signature)
    except Exception as exc:
        logger.error("Failed to parse LINE events: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid payload")

    processed = 0
    for event in events:
        try:
            _handle_event(event)
            processed += 1
        except Exception as exc:
            logger.error("Error handling LINE event %s: %s", type(event).__name__, exc)
            # Continue processing remaining events — never crash the whole batch

    return {"status": "ok", "events_processed": processed}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def _handle_event(event: Any) -> None:
    """Dispatch a single LINE event to the appropriate handler."""
    from linebot.v3.webhooks import (
        MessageEvent,
        FollowEvent,
        UnfollowEvent,
        PostbackEvent,
        TextMessageContent,
    )

    if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
        _handle_text_message(event)
    elif isinstance(event, FollowEvent):
        _handle_follow(event)
    elif isinstance(event, UnfollowEvent):
        _handle_unfollow(event)
    elif isinstance(event, PostbackEvent):
        logger.debug("PostbackEvent received — Phase 2 handler not yet implemented")
    else:
        logger.debug("Unhandled LINE event type: %s", type(event).__name__)


def _handle_text_message(event: Any) -> None:
    """Run the AI pipeline and reply to a text message."""
    user_id = event.source.user_id if event.source else ""
    reply_token = event.reply_token or ""
    text = event.message.text.strip()
    message_id = event.message.id

    if not text:
        return

    logger.info(
        "LINE TextMessage | user_id=%s message_id=%s text=%.60s…",
        user_id,
        message_id,
        text,
    )

    unified = {
        "channel":      "line",
        "message_id":   message_id,
        "user_id":      user_id,
        "user_name":    "",          # LINE doesn't send display name in webhook
        "text":         text,
        "reply_token":  reply_token,
        "comment_id":   "",
        "post_id":      "",
        "timestamp":    datetime.now().isoformat(),
    }

    _get_router().route(unified)


def _handle_follow(event: Any) -> None:
    """Send a welcome message when a user follows the LINE OA."""
    user_id = event.source.user_id if event.source else ""
    reply_token = event.reply_token or ""

    logger.info("LINE FollowEvent | user_id=%s", user_id)

    # Load shop name for personalised welcome
    try:
        from app.core.profile_loader import load_profile
        shop_name = load_profile().shop_name
    except Exception:
        shop_name = "ร้านค้าของเรา"

    welcome = _WELCOME_TEXT.format(shop_name=shop_name)
    _get_line_api().reply_message(reply_token, welcome, user_id=user_id)


def _handle_unfollow(event: Any) -> None:
    """Log when a user unfollows — no reply possible."""
    user_id = event.source.user_id if event.source else "unknown"
    logger.info("LINE UnfollowEvent | user_id=%s", user_id)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_signature(channel_secret: str, body: bytes, signature: str) -> bool:
    """
    Verify X-Line-Signature using HMAC-SHA256.

    LINE signs the raw request body with the channel secret.
    Reference: https://developers.line.biz/en/docs/messaging-api/receiving-messages/#verifying-signatures
    """
    import base64
    import hashlib
    import hmac

    if not signature:
        return False

    try:
        digest = hmac.new(
            channel_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        logger.error("Signature verification error: %s", exc)
        return False
