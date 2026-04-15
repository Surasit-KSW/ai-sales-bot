"""
CommentProcessor — orchestrates the analyze → generate → reply pipeline.

Flow:
  1. Analyze comment intent   (CommentAnalyzer)
  2. Generate reply text      (ReplyGenerator)
  3. Post reply to Facebook   (FacebookAPI) — only when AUTO_REPLY=True

AUTO_REPLY flag (set in .env):
  AUTO_REPLY=True   → actually post the reply via Facebook API
  AUTO_REPLY=False  → generate reply and log it, but do NOT send (safe for testing)
"""

import os
from typing import Optional

from app.integrations.facebook_api import FacebookAPI
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _auto_reply_enabled() -> bool:
    """Read AUTO_REPLY from env; default False for safety."""
    return os.getenv("AUTO_REPLY", "False").strip().lower() == "true"


class CommentProcessor:
    """
    Wraps CommentAnalyzer + ReplyGenerator + FacebookAPI into a single call.

    Usage:
        processor = CommentProcessor()
        reply = processor.process("ราคาเท่าไหร่คะ", comment_id="123_456")
    """

    def __init__(self) -> None:
        self.analyzer = CommentAnalyzer()
        self.generator = ReplyGenerator(client=self.analyzer.client)
        self.fb_api = FacebookAPI()

    def process(
        self,
        comment: str,
        comment_id: str = "",
        from_name: str = "",
    ) -> Optional[str]:
        """
        Analyze a comment, generate a reply, and optionally post it.

        Args:
            comment:    Raw comment text from the customer.
            comment_id: Facebook comment ID — required for auto-reply.
            from_name:  Customer display name (used in logging only).

        Returns:
            Reply text if one was generated, None otherwise.
        """
        label = f"{from_name}: " if from_name else ""
        logger.info("Processing comment | %s%.60s…", label, comment)

        try:
            analysis = self.analyzer.analyze(comment)
            logger.info(
                "Analysis result | intent=%s confidence=%.2f",
                analysis.intent,
                analysis.confidence,
            )

            result = self.generator.generate(analysis)

            if result.was_skipped:
                logger.info("Reply skipped | intent=%s", analysis.intent)
                return None

            if result.error:
                logger.warning("Generator error | %s", result.error)
                return None

            reply = result.reply
            self._dispatch_reply(reply, comment_id=comment_id)
            return reply

        except Exception as exc:
            logger.error("Unexpected error in CommentProcessor: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dispatch_reply(self, reply: str, comment_id: str) -> None:
        """Post the reply or log it, depending on AUTO_REPLY setting."""
        if _auto_reply_enabled():
            if not comment_id:
                logger.warning(
                    "AUTO_REPLY is enabled but comment_id is missing — cannot post reply"
                )
                return
            success = self.fb_api.post_comment_reply(comment_id, reply)
            if success:
                logger.info("Reply posted to Facebook | comment_id=%s", comment_id)
            else:
                logger.error(
                    "Failed to post reply to Facebook | comment_id=%s", comment_id
                )
        else:
            logger.info(
                "[AUTO_REPLY=False] Reply NOT sent (dry-run) | comment_id=%s | reply=%.120s…",
                comment_id or "n/a",
                reply,
            )
