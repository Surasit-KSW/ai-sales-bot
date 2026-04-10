"""
AI Sales Assistant — Entry Point

Pipeline:
  1. Health-check Ollama (fail fast, clear error message)
  2. Read raw comments from data/input_comments.txt
  3. For each comment:
      a. Analyze intent (CommentAnalyzer)
      b. Generate reply (ReplyGenerator)
      c. Append structured result
  4. Write all results to data/processed_results.json
  5. Print a summary table to the terminal

Run:
    python main.py

Why structure it as a pipeline function rather than a script?
  The `run_pipeline()` function can be imported and called from a FastAPI
  endpoint, a Celery task, or a test — without re-running the whole module.
"""

import json
import sys

# Windows terminals default to CP874/CP1252 which can't encode Thai + emojis.
# Reconfigure stdout to UTF-8 before any output so print() never crashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from app.core.config import settings, INPUT_FILE, OUTPUT_FILE
from app.core.llm_client import OllamaClient
from app.core.profile_loader import load_profile
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ANSI colours for terminal output (disabled on Windows if not supported)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _load_comments(filepath: Path) -> List[str]:
    """Read comments from a text file, one comment per line."""
    if not filepath.exists():
        logger.error("Input file not found: %s", filepath)
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    logger.info("Loaded %d comments from %s", len(lines), filepath)
    return lines


def _save_results(results: List[Dict[str, Any]], filepath: Path) -> None:
    """Persist results to JSON with UTF-8 encoding (required for Thai text)."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results saved → %s", filepath)


def _print_summary(results: List[Dict[str, Any]]) -> None:
    """Print a clean summary table to the terminal."""
    total = len(results)
    skipped = sum(1 for r in results if r.get("was_skipped"))
    errors = sum(1 for r in results if r.get("error"))
    processed = total - skipped - errors

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  AI SALES ASSISTANT — PROCESSING COMPLETE{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  Total comments : {total}")
    print(f"  {GREEN}Replied        : {processed}{RESET}")
    print(f"  {YELLOW}Skipped (spam) : {skipped}{RESET}")
    print(f"  {RED}Errors         : {errors}{RESET}")
    print(f"  Output file    : {OUTPUT_FILE}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    for i, r in enumerate(results, 1):
        comment_preview = r["comment"][:55] + "…" if len(r["comment"]) > 55 else r["comment"]
        intent_color = GREEN if r["intent"] == "POTENTIAL_BUYER" else YELLOW
        status = f"{intent_color}[{r['intent']}]{RESET}"

        if r.get("was_skipped"):
            status = f"{RED}[SKIPPED]{RESET}"
        elif r.get("error"):
            status = f"{RED}[ERROR]{RESET}"

        print(f"  {i:02d}. {status} {comment_preview}")
        if r.get("reply"):
            reply_preview = r["reply"][:80] + "…" if len(r["reply"]) > 80 else r["reply"]
            print(f"      └→ {reply_preview}")
        print()


def run_pipeline() -> List[Dict[str, Any]]:
    """
    Execute the full comment processing pipeline.

    Returns:
        List of result dictionaries (also written to OUTPUT_FILE).
    """
    logger.info("=" * 50)
    logger.info("AI Sales Assistant starting | model=%s", settings.ollama_model)
    logger.info("=" * 50)

    # --- Step 1: Health check ---
    client = OllamaClient()
    if not client.is_healthy():
        logger.error(
            "Cannot connect to Ollama at %s. "
            "Please run: ollama serve",
            settings.ollama_base_url,
        )
        sys.exit(1)
    logger.info("Ollama health check passed.")

    # --- Step 2: Load data ---
    comments = _load_comments(INPUT_FILE)

    # --- Step 3: Process each comment ---
    # Load shop profile once and share it — avoids re-reading YAML on every comment
    profile = load_profile()
    logger.info("Shop: %s | Products: %s", profile.shop_name, profile.product_category)

    analyzer = CommentAnalyzer(client=client, profile=profile)
    generator = ReplyGenerator(client=client, profile=profile)
    results: List[Dict[str, Any]] = []

    for idx, comment in enumerate(comments, 1):
        logger.info("Processing comment %d/%d…", idx, len(comments))

        # 3a. Classify intent
        analysis = analyzer.analyze(comment)

        # 3b. Generate reply (skips spam automatically)
        generated = generator.generate(analysis)

        # 3c. Build result record
        record: Dict[str, Any] = {
            "id": idx,
            "comment": comment,
            "intent": analysis.intent,
            "confidence": round(analysis.confidence, 2),
            "sentiment": analysis.sentiment,
            "key_signals": analysis.key_signals,
            "reply": generated.reply,
            "was_skipped": generated.was_skipped,
            "error": generated.error or analysis.error,
            "processed_at": datetime.now().isoformat(),
        }
        results.append(record)

        # Log a brief one-liner per comment for easy monitoring
        status = "SKIPPED" if generated.was_skipped else ("ERROR" if record["error"] else "OK")
        logger.info(
            "  [%s] intent=%-18s | confidence=%.2f | status=%s",
            idx,
            analysis.intent,
            analysis.confidence,
            status,
        )

    # --- Step 4: Persist ---
    _save_results(results, OUTPUT_FILE)

    # --- Step 5: Summary ---
    _print_summary(results)

    return results


if __name__ == "__main__":
    run_pipeline()
