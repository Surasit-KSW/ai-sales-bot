"""
Reply Generator Service.

Takes a classified comment and generates a high-conversion Thai sales reply.

Design note:
  The generator is intentionally "dumb" about classification — it trusts
  the AnalysisResult from the analyzer and focuses only on crafting the
  best possible reply. This separation lets you A/B test different reply
  strategies (e.g. formal vs. casual) without touching classification.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.core.llm_client import OllamaClient, OllamaError
from app.core.profile_loader import ShopProfile, load_profile
from app.services.analyzer import AnalysisResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Comments classified as SPAM get this canned response — no LLM call needed.
# This saves ~1-2s per spam comment and avoids unnecessary API load.
SPAM_SKIP_MARKER = "SKIP"


@dataclass
class GeneratedReply:
    """Structured output from the generator."""

    reply: str
    was_skipped: bool = False   # True for SPAM comments
    error: str = ""


class ReplyGenerator:
    """
    Generates Thai sales replies based on comment intent.

    Usage:
        generator = ReplyGenerator()
        result = generator.generate(analysis_result)
    """

    def __init__(self, client: OllamaClient | None = None, profile: ShopProfile | None = None) -> None:
        self.client = client or OllamaClient()
        self.profile = profile or load_profile()  # load shop_profile.yaml once

    def generate(self, analysis: AnalysisResult) -> GeneratedReply:
        """
        Generate a contextual reply for a classified comment.

        Args:
            analysis: The AnalysisResult produced by CommentAnalyzer.

        Returns:
            GeneratedReply containing the reply text.
            SPAM comments return was_skipped=True with an empty reply.
        """
        # Fast-path: don't waste tokens on spam
        if analysis.intent == "SPAM":
            logger.info("Skipping SPAM comment: %.50s…", analysis.raw_comment)
            return GeneratedReply(reply="", was_skipped=True)

        # If analysis itself failed (Ollama was down), skip gracefully
        if analysis.error and not analysis.raw_comment.strip():
            return GeneratedReply(
                reply="",
                was_skipped=True,
                error=analysis.error,
            )

        user_prompt = settings.generator_user_prompt_template.format(
            comment=analysis.raw_comment,
            intent=analysis.intent,
            sentiment=analysis.sentiment,
        )

        # Build system prompt with real shop data injected
        system_prompt = settings.generator_system_prompt.format(
            shop_context=self.profile.to_prompt_context(),
            style_instructions=self.profile.to_style_instructions(),
        )

        try:
            reply_text = self.client.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=settings.temperature,
            )

            # If the model explicitly signals SKIP, honour it
            if reply_text.strip().upper() == SPAM_SKIP_MARKER:
                return GeneratedReply(reply="", was_skipped=True)

            logger.info(
                "Generated reply for [%s] | %.60s…",
                analysis.intent,
                reply_text,
            )
            return GeneratedReply(reply=reply_text)

        except OllamaError as exc:
            logger.error("Ollama unavailable during generation: %s", exc)
            return GeneratedReply(reply="", error=str(exc))
