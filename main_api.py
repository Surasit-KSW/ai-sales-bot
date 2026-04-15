"""
FastAPI entry point for the AI Sales Bot webhook server.

Registered routes:
    GET  /webhook             — Facebook webhook verification
    POST /webhook             — Facebook comment events
    POST /webhook/line        — LINE bot events

    POST /process/comment     — N8N unified comment processing
    POST /process/batch       — N8N batch comment processing
    GET  /health              — Ollama + model liveness check

Run locally:
    uvicorn main_api:app --reload --port 8000

With Docker:
    docker-compose up

Environment variables required (.env):
    FB_VERIFY_TOKEN
    FB_PAGE_ACCESS_TOKEN
    LINE_CHANNEL_SECRET
    LINE_CHANNEL_ACCESS_TOKEN
    OLLAMA_BASE_URL         (default: http://localhost:11434)
    N8N_WEBHOOK_URL         (default: http://localhost:5678)
"""

from dotenv import load_dotenv

load_dotenv()  # must run before any os.getenv() calls

from fastapi import FastAPI

from app.integrations.facebook_webhook import router as fb_router
from app.integrations.line_webhook import router as line_router
from app.integrations.process_router import router as process_router
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AI Sales Bot",
    description=(
        "Multi-channel AI sales assistant for Thai e-commerce.\n\n"
        "**Webhook routes** (Facebook + LINE → direct)\n\n"
        "**N8N routes** (`/process/*`) — called by N8N orchestration workflows"
    ),
    version="2.0.0",
)

app.include_router(fb_router)
app.include_router(line_router)
app.include_router(process_router)

logger.info(
    "AI Sales Bot API v2 started | "
    "routes: /webhook (FB), /webhook/line (LINE), /process/comment (N8N), /health"
)
