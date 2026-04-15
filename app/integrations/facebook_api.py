"""
Facebook Graph API client.

Handles outbound calls to the Facebook Graph API:
  - post_comment_reply        : Reply to a specific comment
  - get_page_comments         : Fetch comments on a post
  - validate_webhook_signature: Verify X-Hub-Signature-256 on incoming requests
  - mark_comment_read         : No-op (Graph API does not support this)

Error handling:
  - Token expired  → log actionable alert + report to N8N workflow 05
  - Rate limit     → exponential backoff (2 s → 4 s → 8 s), then N8N alert
  - Network errors → log and return False / empty list (never raises)

N8N integration:
  - Every unrecoverable error fires a POST to N8N workflow 05 (error handler)
    at {N8N_WEBHOOK_URL}/webhook/error-handler.
  - The call is fire-and-forget; failure to reach N8N is silently swallowed.
"""

import base64
import hashlib
import hmac
import os
import time
from typing import Any, Optional

import requests

from app.utils.logger import get_logger

logger = get_logger(__name__)

_GRAPH_VERSION = "v19.0"
_GRAPH_BASE = f"https://graph.facebook.com/{_GRAPH_VERSION}"

# Facebook error codes that mean the token is expired / invalid
_TOKEN_EXPIRED_CODES = {190, 102, 463, 467}
# Facebook error codes / HTTP status that mean we're rate-limited
_RATE_LIMIT_CODES = {32, 4, 17, 341}

# Exponential backoff: attempt 0 → 2s, attempt 1 → 4s, attempt 2 → 8s
_BACKOFF_BASE = 2
_MAX_RETRIES = 3


class FacebookAPIError(Exception):
    """Raised internally; never propagates to callers."""


class FacebookAPI:
    """
    Thin wrapper around the Facebook Graph API.

    Usage:
        api = FacebookAPI()
        ok = api.post_comment_reply("123456789_987654321", "สวัสดีค่ะ!")
        valid = api.validate_webhook_signature(raw_body, request.headers["X-Hub-Signature-256"])
    """

    def __init__(self) -> None:
        self.access_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
        if not self.access_token:
            logger.warning(
                "FB_PAGE_ACCESS_TOKEN is not set — Facebook API calls will fail"
            )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def post_comment_reply(self, comment_id: str, message: str) -> bool:
        """
        Post a reply to a Facebook comment.

        Args:
            comment_id: The comment's ID (e.g. "123456789_987654321").
            message:    The reply text.

        Returns:
            True on success, False on any failure.
        """
        if not message or not message.strip():
            logger.warning("post_comment_reply called with empty message — skipped")
            return False

        url = f"{_GRAPH_BASE}/{comment_id}/comments"
        payload = {"message": message, "access_token": self.access_token}

        return self._post(url, data=payload, context=f"reply to {comment_id}")

    def get_page_comments(
        self, post_id: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        """
        Fetch recent comments on a page post.

        Args:
            post_id: The post's ID.
            limit:   Maximum number of comments to return (default 25).

        Returns:
            List of comment dicts, or empty list on failure.
        """
        url = f"{_GRAPH_BASE}/{post_id}/comments"
        params = {
            "fields": "id,message,from,created_time",
            "limit": limit,
            "access_token": self.access_token,
        }

        try:
            response = self._request("GET", url, params=params)
            comments: list = response.get("data", [])
            logger.info("Fetched %d comments for post %s", len(comments), post_id)
            return comments
        except FacebookAPIError:
            return []

    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify the X-Hub-Signature-256 header on incoming Facebook webhook requests.

        Facebook signs the raw request body with the App Secret using HMAC-SHA256
        and sends it as ``sha256=<hex_digest>``.

        Args:
            payload:   Raw request body bytes.
            signature: X-Hub-Signature-256 header value.

        Returns:
            True if the signature is valid, False otherwise.
        """
        app_secret = os.getenv("FB_APP_SECRET", "")
        if not app_secret:
            logger.error(
                "FB_APP_SECRET not set — webhook signature cannot be validated. "
                "Set FB_APP_SECRET in your .env file."
            )
            return False

        if not signature.startswith("sha256="):
            logger.warning(
                "Facebook webhook: unexpected signature format (expected sha256=…)"
            )
            return False

        try:
            expected = hmac.new(
                app_secret.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature[7:])
        except Exception as exc:
            logger.error("Facebook signature validation error: %s", exc)
            return False

    def mark_comment_read(self, comment_id: str) -> bool:
        """
        Mark a comment as read (no-op — Graph API does not support this).

        Returns:
            Always True.
        """
        logger.debug(
            "mark_comment_read called for %s — not supported by Graph API, skipped",
            comment_id,
        )
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _post(self, url: str, data: dict, context: str = "") -> bool:
        """Execute a POST and return True on success."""
        try:
            self._request("POST", url, data=data)
            logger.info("Facebook POST success | %s", context)
            return True
        except FacebookAPIError:
            return False

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        _attempt: int = 0,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request against the Graph API with exponential backoff.

        Retry schedule on rate-limit:
          attempt 0 → wait 2 s → attempt 1
          attempt 1 → wait 4 s → attempt 2
          attempt 2 → wait 8 s → attempt 3
          attempt 3 → give up, report to N8N

        Args:
            _attempt: Internal retry counter (0-based).
        """
        if not self.access_token:
            logger.error("Facebook API call skipped — FB_PAGE_ACCESS_TOKEN not set")
            raise FacebookAPIError("missing access token")

        try:
            resp = requests.request(
                method, url, params=params, data=data, timeout=15
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Facebook API network error: %s", exc)
            raise FacebookAPIError("network error") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Facebook API request timed out: %s", exc)
            raise FacebookAPIError("timeout") from exc

        # --- Rate limiting ---
        if resp.status_code == 429 or _is_rate_limited(resp):
            if _attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE ** (_attempt + 1)
                logger.warning(
                    "Facebook rate limit hit — backing off %ds (attempt %d/%d)",
                    wait,
                    _attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(wait)
                return self._request(method, url, params=params, data=data, _attempt=_attempt + 1)

            logger.error("Facebook rate limit persists after %d retries — giving up", _MAX_RETRIES)
            self._report_to_n8n(
                error_type="rate_limit_exhausted",
                detail=f"Rate limit persisted after {_MAX_RETRIES} retries",
                context=f"{method} {url}",
            )
            raise FacebookAPIError("rate limited")

        try:
            body = resp.json()
        except Exception:
            body = {}

        if not resp.ok:
            error = body.get("error", {})
            code = error.get("code", 0)

            if code in _TOKEN_EXPIRED_CODES:
                logger.error(
                    "Facebook access token expired or invalid (code %d). "
                    "Please refresh FB_PAGE_ACCESS_TOKEN in your .env file.",
                    code,
                )
                self._report_to_n8n(
                    error_type="token_expired",
                    detail=f"OAuthException code={code} — rotate FB_PAGE_ACCESS_TOKEN",
                    context=f"{method} {url}",
                )
            else:
                logger.error(
                    "Facebook API error | status=%d code=%d message=%s",
                    resp.status_code,
                    code,
                    error.get("message", "unknown"),
                )
            raise FacebookAPIError(f"HTTP {resp.status_code} code={code}")

        return body

    def _report_to_n8n(self, error_type: str, detail: str, context: str = "") -> None:
        """
        Fire-and-forget error report to N8N workflow 05 (error handler).

        Sends a POST to {N8N_WEBHOOK_URL}/webhook/error-handler.
        Silently swallows any failure so callers are never blocked.
        """
        n8n_base = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
        endpoint = f"{n8n_base}/webhook/error-handler"
        payload = {
            "source": "facebook_api",
            "severity": "error",
            "error_type": error_type,
            "detail": detail,
            "context": context,
        }
        try:
            requests.post(endpoint, json=payload, timeout=5)
            logger.debug("Error report sent to N8N | type=%s", error_type)
        except Exception as exc:
            logger.debug("Could not reach N8N error handler (N8N may be down): %s", exc)


def _is_rate_limited(resp: requests.Response) -> bool:
    """Check Graph API error body for rate-limit error codes."""
    try:
        code = resp.json().get("error", {}).get("code", 0)
        return int(code) in _RATE_LIMIT_CODES
    except Exception:
        return False
