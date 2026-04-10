"""
Robust Ollama LLM client wrapper.

Why wrap the HTTP call instead of using ollama-python directly?
  1. We own the retry logic — exponential backoff prevents hammering a
     temporarily-busy Ollama server.
  2. We own the error surface — all LLM errors become OllamaError, so
     callers don't need to know about requests.exceptions internals.
  3. Swappability — replace the internals with an OpenAI call later and
     ZERO service code changes (Adapter / Strategy pattern).
"""

import json
import time
from typing import Optional

import requests

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an unexpected response."""


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/chat endpoint.

    Supports:
      - System + user message structure
      - Configurable retries with backoff
      - Structured JSON response parsing
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.request_timeout_seconds
        self.max_retries = settings.max_retries
        self._chat_endpoint = f"{self.base_url}/api/chat"

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a chat request to Ollama and return the raw text response.

        Args:
            system_prompt: Sets the model's persona and rules.
            user_prompt:   The actual task / question.
            temperature:   Override default temperature if needed.

        Returns:
            The model's text response (stripped).

        Raises:
            OllamaError: If all retries are exhausted.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,  # simpler to handle; streaming is a V2 feature
            "options": {
                "temperature": temperature or settings.temperature,
            },
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):  # +2: retries + initial try
            try:
                logger.debug(
                    "Ollama request | model=%s | attempt=%d", self.model, attempt
                )
                response = requests.post(
                    self._chat_endpoint,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                content: str = data["message"]["content"].strip()
                logger.debug("Ollama response received (%d chars)", len(content))
                return content

            except requests.exceptions.ConnectionError as exc:
                last_error = exc
                logger.warning(
                    "Ollama unreachable (attempt %d/%d). Is Ollama running?",
                    attempt,
                    self.max_retries + 1,
                )
            except requests.exceptions.Timeout as exc:
                last_error = exc
                logger.warning(
                    "Ollama request timed out (attempt %d/%d).", attempt, self.max_retries + 1
                )
            except (requests.exceptions.HTTPError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.error("Unexpected Ollama response: %s", exc)
                break  # non-retriable error — don't waste time retrying

            # Exponential backoff: 1s, 2s, 4s …
            if attempt <= self.max_retries:
                wait = 2 ** (attempt - 1)
                logger.info("Retrying in %ds…", wait)
                time.sleep(wait)

        raise OllamaError(
            f"Ollama failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )

    def is_healthy(self) -> bool:
        """
        Quick health-check against Ollama's root endpoint.

        Returns:
            True if Ollama is responding, False otherwise.
        """
        try:
            resp = requests.get(self.base_url, timeout=5)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False
