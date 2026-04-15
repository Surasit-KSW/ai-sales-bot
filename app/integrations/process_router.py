"""
Process Router — unified AI processing endpoints for N8N integration.

N8N workflows call these endpoints instead of calling Ollama directly,
so all AI logic stays in Python while N8N handles routing and persistence.

Routes:
    POST /process/comment   — single comment (Facebook, LINE, or any channel)
    POST /process/batch     — array of comments for manual batch runs
    GET  /health            — Ollama + model liveness check
"""

import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm_client import OllamaClient
from app.core.profile_loader import ShopProfile, load_profile
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons — initialized on first request, shared across all requests.
# Re-creating OllamaClient + loading the profile on every call would be slow.
# ---------------------------------------------------------------------------
_client: Optional[OllamaClient] = None
_analyzer: Optional[CommentAnalyzer] = None
_generator: Optional[ReplyGenerator] = None


def _get_services() -> tuple[CommentAnalyzer, ReplyGenerator]:
    """Return (analyzer, generator), creating them once if needed."""
    global _client, _analyzer, _generator
    if _client is None:
        profile: ShopProfile = load_profile()
        _client = OllamaClient()
        _analyzer = CommentAnalyzer(client=_client, profile=profile)
        _generator = ReplyGenerator(client=_client, profile=profile)
        logger.info(
            "AI services initialised | model=%s | shop=%s",
            _client.model,
            profile.shop_name,
        )
    return _analyzer, _generator   # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CommentRequest(BaseModel):
    """Unified comment format accepted from N8N (any channel)."""
    channel: str = "facebook"           # "facebook" | "line"
    text: str
    user_name: str = "ลูกค้า"
    comment_id: Optional[str] = None    # Facebook comment ID
    reply_token: Optional[str] = None   # LINE reply token
    user_id: Optional[str] = None
    post_id: Optional[str] = None
    timestamp: Optional[str] = None     # ISO 8601 — defaults to now


class CommentResult(BaseModel):
    """Full processing result returned to N8N."""
    success: bool
    intent: str
    confidence: float
    sentiment: str
    key_signals: List[str]
    reply: str
    was_skipped: bool
    should_escalate: bool
    lead_data: dict
    processing_time_ms: int
    error: str = ""


# ---------------------------------------------------------------------------
# Core processing function (sync — FastAPI runs it in a threadpool)
# ---------------------------------------------------------------------------

def _process_one(req: CommentRequest) -> CommentResult:
    """Run the full analyze → generate pipeline for one comment."""
    analyzer, generator = _get_services()

    start = time.monotonic()
    analysis  = analyzer.analyze(req.text)
    generated = generator.generate(analysis)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    lead_data = {
        "timestamp":      req.timestamp or datetime.now(timezone.utc).isoformat(),
        "channel":        req.channel,
        "user_name":      req.user_name,
        "user_id":        req.user_id or "",
        "comment_text":   req.text,
        "comment_id":     req.comment_id or "",
        "post_id":        req.post_id or "",
        "intent":         analysis.intent,
        "confidence":     analysis.confidence,
        "sentiment":      analysis.sentiment,
        "reply_sent":     generated.reply,
        "was_skipped":    generated.was_skipped,
        "should_escalate": generated.is_escalated,
        "shop_name":      generator.profile.shop_name,
    }

    logger.info(
        "Processed [%s] %s/%s | intent=%s conf=%.2f escalate=%s skip=%s | %dms",
        req.channel,
        req.user_name,
        req.text[:40],
        analysis.intent,
        analysis.confidence,
        generated.is_escalated,
        generated.was_skipped,
        elapsed_ms,
    )

    return CommentResult(
        success=not bool(analysis.error or generated.error),
        intent=analysis.intent,
        confidence=analysis.confidence,
        sentiment=analysis.sentiment,
        key_signals=analysis.key_signals,
        reply=generated.reply,
        was_skipped=generated.was_skipped,
        should_escalate=generated.is_escalated,
        lead_data=lead_data,
        processing_time_ms=elapsed_ms,
        error=analysis.error or generated.error,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/process/comment", response_model=CommentResult, tags=["N8N"])
def process_comment(req: CommentRequest) -> CommentResult:
    """
    Process a single customer comment (Facebook, LINE, or any channel).

    Called by N8N workflows 01 (Facebook) and 02 (LINE) after receiving
    a webhook event. Returns full AI analysis + generated reply.
    """
    return _process_one(req)


@router.post("/process/batch", response_model=List[CommentResult], tags=["N8N"])
def process_batch(requests: List[CommentRequest]) -> List[CommentResult]:
    """
    Process multiple comments in sequence (manual batch mode).

    Useful for replaying queued comments or running offline tests.
    Returns an array of results in the same order as the input.
    """
    logger.info("Batch processing %d comments", len(requests))
    return [_process_one(r) for r in requests]


@router.get("/health", tags=["N8N"])
def health() -> dict:
    """
    Liveness check — verifies Ollama is reachable and reports the active model.

    N8N can poll this endpoint to gate workflows on model availability.
    """
    client = OllamaClient()
    ollama_ok = client.is_healthy()
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": {
            "connected": ollama_ok,
            "base_url":  settings.ollama_base_url,
            "model":     settings.ollama_model,
        },
        "api_version": "2.0.0",
    }
