"""
LINE Messaging API client.

Wraps the LINE Bot SDK v3 to send messages back to users.

Sending methods:
  reply_message     — uses reply_token from webhook event (valid ~1 min)
  push_message      — uses user_id; works any time but costs push quota
  send_flex_message — rich card using LINE Flex Message format
  send_quick_reply  — reply with tappable quick-reply buttons (reply_token)
  push_quick_reply  — quick-reply buttons via push (no reply_token)
  verify_signature  — verify X-Line-Signature on incoming webhook requests

Flex Message template builders (module-level):
  product_flex(...)   — product card with image, price, and order button
  promotion_flex(...) — promotional banner with hero image and CTA
  quick_reply_flex(...)— text bubble with quick-reply button options

Error handling:
  - Expired reply_token → automatic fallback to push_message (if user_id given)
  - Rate limit (429)   → exponential backoff: 2 s → 4 s → 8 s
"""

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Exponential backoff: attempt 0 → 2s, attempt 1 → 4s, attempt 2 → 8s
_BACKOFF_BASE = 2
_MAX_RETRIES = 3


class LineAPI:
    """
    Thin wrapper around LINE Messaging API v3.

    Usage:
        api = LineAPI()
        api.reply_message(reply_token, "สวัสดีค่ะ!")
        api.push_message(user_id, "ข้อความสำคัญ")
        api.send_flex_message(reply_token, product_flex("สบู่", "99", img_url, desc, url))
    """

    def __init__(self) -> None:
        self._access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        if not self._access_token:
            logger.warning(
                "LINE_CHANNEL_ACCESS_TOKEN is not set — LINE API calls will fail"
            )

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify the X-Line-Signature header on incoming LINE webhook requests.

        LINE signs the raw request body with the Channel Secret using HMAC-SHA256
        and base64-encodes the result.

        Args:
            body:      Raw request body bytes.
            signature: X-Line-Signature header value.

        Returns:
            True if the signature is valid, False otherwise.
        """
        channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
        if not channel_secret:
            logger.error(
                "LINE_CHANNEL_SECRET not set — webhook signature cannot be validated"
            )
            return False

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
            logger.error("LINE signature validation error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Text messaging
    # ------------------------------------------------------------------

    def reply_message(
        self,
        reply_token: str,
        message_text: str,
        user_id: str = "",
    ) -> bool:
        """
        Reply using a webhook reply_token (valid for ~1 minute).

        Falls back to push_message if the token is expired and user_id is given.

        Args:
            reply_token:  Token from the LINE webhook event.
            message_text: Text to send.
            user_id:      LINE user ID — used as fallback if token expired.

        Returns:
            True on success, False on failure.
        """
        if not message_text.strip():
            return False

        try:
            from linebot.v3.messaging import (
                ApiClient,
                Configuration,
                MessagingApi,
                ReplyMessageRequest,
                TextMessage,
            )

            config = Configuration(access_token=self._access_token)
            with ApiClient(config) as client:
                api = MessagingApi(client)
                api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=message_text)],
                    )
                )
            logger.info("LINE reply sent | reply_token=%.20s…", reply_token)
            return True

        except Exception as exc:
            if _is_invalid_token(exc):
                logger.warning(
                    "LINE reply_token expired — falling back to push_message | user_id=%s",
                    user_id,
                )
                if user_id:
                    return self.push_message(user_id, message_text)
                logger.error("LINE reply failed: token expired and no user_id for fallback")
                return False
            if _is_rate_limited(exc):
                return self._retry_with_backoff(
                    lambda: self.reply_message(reply_token, message_text, user_id)
                )
            logger.error("LINE reply_message failed: %s", exc)
            return False

    def push_message(self, user_id: str, message_text: str) -> bool:
        """
        Push a message directly to a user (no reply_token required).

        Args:
            user_id:      LINE user ID (starts with 'U').
            message_text: Text to send.

        Returns:
            True on success, False on failure.
        """
        if not message_text.strip() or not user_id:
            return False

        try:
            from linebot.v3.messaging import (
                ApiClient,
                Configuration,
                MessagingApi,
                PushMessageRequest,
                TextMessage,
            )

            config = Configuration(access_token=self._access_token)
            with ApiClient(config) as client:
                api = MessagingApi(client)
                api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=message_text)],
                    )
                )
            logger.info("LINE push sent | user_id=%s", user_id)
            return True

        except Exception as exc:
            if _is_rate_limited(exc):
                return self._retry_with_backoff(lambda: self.push_message(user_id, message_text))
            logger.error("LINE push_message failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Flex Messages
    # ------------------------------------------------------------------

    def send_flex_message(
        self,
        reply_token: str,
        flex_content: dict,
        alt_text: str = "ข้อความจากร้าน",
        user_id: str = "",
    ) -> bool:
        """
        Send a Flex Message using a reply_token.

        Use the module-level builders (product_flex, promotion_flex, etc.)
        to generate the flex_content dict, or build one manually.

        Args:
            reply_token:  Token from the LINE webhook event.
            flex_content: Flex Message container dict (type, header, body, footer…).
            alt_text:     Text shown in notification preview (≤ 400 chars).
            user_id:      Fallback user_id if reply_token expires.

        Returns:
            True on success, False on failure.
        """
        try:
            from linebot.v3.messaging import (
                ApiClient,
                Configuration,
                FlexMessage,
                MessagingApi,
                ReplyMessageRequest,
            )
            from linebot.v3.messaging.models import FlexContainer

            config = Configuration(access_token=self._access_token)
            with ApiClient(config) as client:
                api = MessagingApi(client)
                api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[
                            FlexMessage(
                                alt_text=alt_text[:400],
                                contents=FlexContainer.from_dict(flex_content),
                            )
                        ],
                    )
                )
            logger.info(
                "LINE flex message sent | alt_text=%.40s | reply_token=%.20s…",
                alt_text,
                reply_token,
            )
            return True

        except Exception as exc:
            if _is_invalid_token(exc):
                logger.warning("LINE flex reply_token expired — push not supported for flex, skipping")
                return False
            if _is_rate_limited(exc):
                return self._retry_with_backoff(
                    lambda: self.send_flex_message(reply_token, flex_content, alt_text, user_id)
                )
            logger.error("LINE send_flex_message failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Quick reply
    # ------------------------------------------------------------------

    def send_quick_reply(
        self,
        reply_token: str,
        message_text: str,
        options: list[str],
        user_id: str = "",
    ) -> bool:
        """
        Send a message with quick-reply buttons using a reply_token.

        Args:
            reply_token:  Token from the LINE webhook event.
            message_text: Main message text shown above the buttons.
            options:      List of button labels (max 13, each ≤ 20 chars).
            user_id:      Fallback user_id if reply_token expires.

        Returns:
            True on success, False on failure.
        """
        if not options:
            return self.reply_message(reply_token, message_text, user_id)

        try:
            from linebot.v3.messaging import (
                ApiClient,
                Configuration,
                MessageAction,
                MessagingApi,
                QuickReply,
                QuickReplyItem,
                ReplyMessageRequest,
                TextMessage,
            )

            items = [
                QuickReplyItem(action=MessageAction(label=opt[:20], text=opt))
                for opt in options[:13]
            ]
            config = Configuration(access_token=self._access_token)
            with ApiClient(config) as client:
                api = MessagingApi(client)
                api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[
                            TextMessage(
                                text=message_text,
                                quick_reply=QuickReply(items=items),
                            )
                        ],
                    )
                )
            logger.info(
                "LINE quick-reply sent | %d options | reply_token=%.20s…",
                len(items),
                reply_token,
            )
            return True

        except Exception as exc:
            if _is_invalid_token(exc):
                logger.warning("LINE quick_reply token expired — falling back to push")
                if user_id:
                    return self.push_message(user_id, message_text + "\n\n" + " | ".join(options))
                return False
            if _is_rate_limited(exc):
                return self._retry_with_backoff(
                    lambda: self.send_quick_reply(reply_token, message_text, options, user_id)
                )
            logger.error("LINE send_quick_reply failed: %s", exc)
            return False

    def push_quick_reply(
        self,
        user_id: str,
        message_text: str,
        options: list[str],
    ) -> bool:
        """
        Push a message with quick-reply buttons (no reply_token required).

        Args:
            user_id:      LINE user ID (starts with 'U').
            message_text: Main message text shown above the buttons.
            options:      List of button labels (max 13, each ≤ 20 chars).

        Returns:
            True on success, False on failure.
        """
        if not options:
            return self.push_message(user_id, message_text)
        if not user_id or not message_text.strip():
            return False

        try:
            from linebot.v3.messaging import (
                ApiClient,
                Configuration,
                MessageAction,
                MessagingApi,
                PushMessageRequest,
                QuickReply,
                QuickReplyItem,
                TextMessage,
            )

            items = [
                QuickReplyItem(action=MessageAction(label=opt[:20], text=opt))
                for opt in options[:13]
            ]
            config = Configuration(access_token=self._access_token)
            with ApiClient(config) as client:
                api = MessagingApi(client)
                api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[
                            TextMessage(
                                text=message_text,
                                quick_reply=QuickReply(items=items),
                            )
                        ],
                    )
                )
            logger.info(
                "LINE push quick-reply sent | %d options | user_id=%s",
                len(items),
                user_id,
            )
            return True

        except Exception as exc:
            if _is_rate_limited(exc):
                return self._retry_with_backoff(
                    lambda: self.push_quick_reply(user_id, message_text, options)
                )
            logger.error("LINE push_quick_reply failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Bot info
    # ------------------------------------------------------------------

    def get_bot_info(self) -> dict:
        """Fetch LINE bot profile info. Returns empty dict on failure."""
        if not self._access_token:
            return {}
        try:
            import requests as _requests

            resp = _requests.get(
                "https://api.line.me/v2/bot/info",
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=5,
            )
            if resp.ok:
                return resp.json()
            logger.debug("LINE get_bot_info HTTP %d", resp.status_code)
        except Exception as exc:
            logger.debug("LINE get_bot_info failed: %s", exc)
        return {}

    def get_follower_count(self) -> int | None:
        """Fetch the number of LINE OA followers. Returns None if unavailable."""
        if not self._access_token:
            return None
        try:
            import requests as _requests

            resp = _requests.get(
                "https://api.line.me/v2/bot/followers/count",
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                if data.get("status") == "ready":
                    return data.get("count")
        except Exception as exc:
            logger.debug("LINE get_follower_count failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _retry_with_backoff(self, fn, _attempt: int = 0) -> bool:
        """
        Retry fn() with exponential backoff on rate-limit.

        Schedule: attempt 0 → 2 s, attempt 1 → 4 s, attempt 2 → 8 s.
        """
        if _attempt >= _MAX_RETRIES:
            logger.error("LINE rate limit persists after %d retries — giving up", _MAX_RETRIES)
            return False
        wait = _BACKOFF_BASE ** (_attempt + 1)
        logger.warning(
            "LINE rate limit hit — backing off %ds (attempt %d/%d)",
            wait,
            _attempt + 1,
            _MAX_RETRIES,
        )
        time.sleep(wait)
        try:
            return fn()
        except Exception as exc:
            logger.error("LINE retry %d failed: %s", _attempt + 1, exc)
            return False


# ---------------------------------------------------------------------------
# Flex Message template builders
# ---------------------------------------------------------------------------

def product_flex(
    name: str,
    price: str,
    image_url: str,
    description: str,
    order_url: str,
) -> dict:
    """
    Build a product recommendation Flex Message (bubble).

    Renders as a card with a hero image, product name, price, description,
    and an "สั่งซื้อเลย" button linking to order_url.

    Args:
        name:        Product name.
        price:       Price string (e.g. "฿299" or "299 บาท").
        image_url:   URL of the product image (HTTPS required by LINE).
        description: Short product description (1-2 sentences).
        order_url:   URL opened when the user taps the order button.

    Returns:
        Flex Message container dict suitable for send_flex_message().
    """
    return {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": name,
                    "weight": "bold",
                    "size": "xl",
                    "wrap": True,
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ราคา",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0,
                        },
                        {
                            "type": "text",
                            "text": price,
                            "weight": "bold",
                            "size": "xl",
                            "color": "#e8534a",
                            "margin": "sm",
                        },
                    ],
                },
                {
                    "type": "text",
                    "text": description,
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True,
                    "margin": "md",
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1DB446",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "สั่งซื้อเลย",
                        "uri": order_url,
                    },
                },
            ],
        },
    }


def promotion_flex(
    title: str,
    description: str,
    image_url: str,
    action_text: str,
    action_url: str,
) -> dict:
    """
    Build a promotional banner Flex Message (bubble, hero style).

    Renders as a full-width image banner with title, description, and CTA button.

    Args:
        title:       Promotion headline (e.g. "ลด 30% ทุกวันศุกร์").
        description: Promotion details.
        image_url:   Banner image URL (HTTPS, recommended 1040×585 px).
        action_text: CTA button label (e.g. "ดูโปรโมชั่น").
        action_url:  URL opened when the user taps the CTA button.

    Returns:
        Flex Message container dict suitable for send_flex_message().
    """
    return {
        "type": "bubble",
        "size": "mega",
        "hero": {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "uri": action_url,
            },
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "xl",
                    "color": "#e8534a",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": description,
                    "size": "sm",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "md",
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "uri",
                        "label": action_text,
                        "uri": action_url,
                    },
                }
            ],
        },
    }


def quick_reply_flex(message_text: str, options: list[dict]) -> dict:
    """
    Build a Flex Message bubble with quick-action buttons in the footer.

    Unlike LINE's native quick-reply (which floats above the keyboard),
    this embeds buttons directly inside a flex bubble — useful for persistent
    choices that should remain visible in the chat history.

    Args:
        message_text: Main message shown in the bubble body.
        options:      List of button dicts, each with keys:
                        - label (str): Button label text (≤ 20 chars)
                        - text  (str): Message sent when tapped
                      Maximum 5 buttons (LINE footer limit).

    Returns:
        Flex Message container dict suitable for send_flex_message().

    Example:
        flex = quick_reply_flex(
            "เลือกข้อมูลที่ต้องการ:",
            [
                {"label": "ราคา", "text": "ราคาสินค้า"},
                {"label": "โปรโมชั่น", "text": "โปรโมชั่นล่าสุด"},
                {"label": "สั่งซื้อ", "text": "วิธีสั่งซื้อ"},
            ]
        )
    """
    buttons = [
        {
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": opt["label"][:20],
                "text": opt["text"],
            },
        }
        for opt in options[:5]
    ]

    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": message_text,
                    "wrap": True,
                    "size": "md",
                }
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": buttons,
        },
    }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _is_invalid_token(exc: Exception) -> bool:
    """Return True when the exception indicates an expired/invalid reply token."""
    exc_str = str(exc).lower()
    return "invalid reply token" in exc_str or (
        hasattr(exc, "status") and exc.status == 400  # type: ignore[attr-defined]
        and "reply token" in exc_str
    )


def _is_rate_limited(exc: Exception) -> bool:
    """Return True when the exception indicates rate limiting (HTTP 429)."""
    return hasattr(exc, "status") and exc.status == 429  # type: ignore[attr-defined]
