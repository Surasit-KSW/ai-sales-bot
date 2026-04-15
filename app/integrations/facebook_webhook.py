"""
Facebook Webhook Integration.

Handles two types of requests from the Facebook Graph API:

  GET  /webhook  — Verification handshake when first registering the webhook.
  POST /webhook  — Real-time comment events (entry → changes → value).
  GET  /health   — Liveness check.

All AI processing and channel routing is delegated to MessageRouter,
keeping this module focused on Facebook-specific parsing only.

Reference: https://developers.facebook.com/docs/graph-api/webhooks
"""

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.services.message_router import MessageRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Lazily initialised — Ollama may not be running at import time
_message_router: MessageRouter | None = None


def _get_router() -> MessageRouter:
    global _message_router
    if _message_router is None:
        _message_router = MessageRouter()
    return _message_router


# ---------------------------------------------------------------------------
# GET /webhook  — Facebook verification handshake
# ---------------------------------------------------------------------------

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """
    Facebook calls this once when registering the webhook URL.
    Must return hub.challenge as plain text with HTTP 200.
    """
    expected_token = os.getenv("FB_VERIFY_TOKEN", "")
    if not expected_token:
        logger.error("FB_VERIFY_TOKEN is not set in environment")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Facebook webhook verified successfully")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning(
        "Webhook verification failed | mode=%s token_match=%s",
        hub_mode,
        hub_verify_token == expected_token,
    )
    raise HTTPException(status_code=403, detail="Verification failed")


# ---------------------------------------------------------------------------
# POST /webhook  — Incoming comment events
# ---------------------------------------------------------------------------

@router.post("/webhook", status_code=200)
async def receive_event(request: Request) -> dict[str, Any]:
    """
    Receive Facebook feed events.  Walk entry → changes → value and
    forward each new comment to MessageRouter as a unified message.
    """
    try:
        payload = await request.json()
    except Exception:
        logger.warning("Failed to parse Facebook payload as JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("object") != "page":
        return {"status": "ignored", "reason": "not a page event"}

    replies_generated = 0

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value: dict = change.get("value", {})

            # Only process new comments, not edits/deletes
            if value.get("item") != "comment" or value.get("verb") != "add":
                continue

            comment_id = value.get("comment_id", "")
            message    = value.get("message", "").strip()
            from_name  = value.get("from", {}).get("name", "unknown")
            user_id    = value.get("from", {}).get("id", "")
            post_id    = value.get("post_id", "")

            if not message:
                continue

            logger.info(
                "FB comment received | comment_id=%s post_id=%s from=%s",
                comment_id,
                post_id,
                from_name,
            )

            unified = {
                "channel":     "facebook",
                "message_id":  comment_id,
                "user_id":     user_id,
                "user_name":   from_name,
                "text":        message,
                "reply_token": "",
                "comment_id":  comment_id,
                "post_id":     post_id,
                "timestamp":   datetime.now().isoformat(),
            }

            reply = _get_router().route(unified)
            if reply:
                replies_generated += 1

    return {"status": "ok", "replies_generated": replies_generated}


# ---------------------------------------------------------------------------
# GET /health  — Liveness check
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check() -> dict[str, str]:
    """Returns 200 OK when the service is up."""
    return {"status": "ok", "service": "ai-sales-bot"}
