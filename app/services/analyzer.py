"""
Intent Analyzer Service.

Classifies a customer comment into one of four intents:
  POTENTIAL_BUYER  — showing purchase interest ("ราคาเท่าไหร่", "มีสีอื่นไหม")
  GENERAL_INQUIRY  — asking general questions without clear buying signal
  COMPLAINT        — expressing dissatisfaction or reporting a problem
  SPAM             — irrelevant, promotional, or bot content

Why keep classification separate from generation?
  Single Responsibility Principle. The analyzer produces structured data;
  the generator consumes it. Swapping the classifier (e.g. rule-based →
  ML model) never touches the generator.
"""

import json
import re
from dataclasses import dataclass
from typing import List

from app.core.config import settings
from app.core.llm_client import OllamaClient, OllamaError
from app.core.profile_loader import ShopProfile, load_profile
from app.utils.logger import get_logger

logger = get_logger(__name__)

VALID_INTENTS = {"POTENTIAL_BUYER", "GENERAL_INQUIRY", "SPAM", "COMPLAINT"}


@dataclass
class AnalysisResult:
    """Structured output from the analyzer."""

    intent: str
    confidence: float
    key_signals: List[str]
    sentiment: str
    raw_comment: str
    error: str = ""  # non-empty when analysis failed


def _extract_json(text: str) -> dict:
    """
    Parse JSON from LLM output, handling markdown code fences.

    LLMs sometimes wrap JSON in ```json ... ``` — this strips that safely.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    return json.loads(cleaned)


class CommentAnalyzer:
    """
    Analyses Thai customer comments and returns structured intent data.

    Usage:
        analyzer = CommentAnalyzer()
        result = analyzer.analyze("ราคาเท่าไหร่คะ")
    """

    def __init__(self, client: OllamaClient | None = None, profile: ShopProfile | None = None) -> None:
        # Dependency injection: pass a mock client in tests, real one in prod
        self.client = client or OllamaClient()
        self.profile = profile or load_profile()  # load shop_profile.yaml once

    def analyze(self, comment: str) -> AnalysisResult:
        """
        Classify the intent of a single comment.

        Args:
            comment: Raw customer comment text.

        Returns:
            AnalysisResult dataclass. On failure, intent defaults to
            GENERAL_INQUIRY so the pipeline continues gracefully.
        """
        if not comment or not comment.strip():
            return AnalysisResult(
                intent="SPAM",
                confidence=1.0,
                key_signals=["empty_comment"],
                sentiment="neutral",
                raw_comment=comment,
            )

        user_prompt = settings.analyzer_user_prompt_template.format(comment=comment)

        # Inject shop context so the model understands what products are being discussed
        system_prompt = settings.analyzer_system_prompt.format(
            shop_context=self.profile.to_prompt_context()
        )

        try:
            raw_response = self.client.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # low temp = deterministic, consistent classification
            )
            logger.debug("Analyzer raw response: %s", raw_response)

            data = _extract_json(raw_response)

            intent = str(data.get("intent", "GENERAL_INQUIRY")).upper()
            if intent not in VALID_INTENTS:
                logger.warning("Unknown intent '%s', defaulting to GENERAL_INQUIRY", intent)
                intent = "GENERAL_INQUIRY"

            return AnalysisResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                key_signals=list(data.get("key_signals", [])),
                sentiment=str(data.get("sentiment", "neutral")),
                raw_comment=comment,
            )

        except OllamaError as exc:
            logger.error("Ollama unavailable during analysis: %s", exc)
            return AnalysisResult(
                intent="GENERAL_INQUIRY",
                confidence=0.0,
                key_signals=[],
                sentiment="neutral",
                raw_comment=comment,
                error=str(exc),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("Failed to parse analyzer response: %s | raw=%s", exc, raw_response if 'raw_response' in dir() else 'N/A')
            return AnalysisResult(
                intent="GENERAL_INQUIRY",
                confidence=0.0,
                key_signals=[],
                sentiment="neutral",
                raw_comment=comment,
                error=f"ParseError: {exc}",
            )
