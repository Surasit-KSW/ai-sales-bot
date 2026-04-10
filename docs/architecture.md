# Architecture

## Pipeline Overview

```
input_comments.txt  →  CommentAnalyzer  →  ReplyGenerator  →  processed_results.json
```

## Module Map

| Module | Path | Role |
|--------|------|------|
| Config | `app/core/config.py` | Single source of truth for model names, URLs, prompt templates |
| LLM Client | `app/core/llm_client.py` | Ollama HTTP wrapper — retries, backoff, error isolation |
| Analyzer | `app/services/analyzer.py` | Classifies intent: POTENTIAL_BUYER / GENERAL_INQUIRY / COMPLAINT / SPAM |
| Generator | `app/services/generator.py` | Produces contextual Thai replies per intent |
| Logger | `app/utils/logger.py` | Structured logging to stdout + logs/app.log |
| Main | `main.py` | Pipeline orchestration + summary output |

## Design Principles

- **Single Responsibility** — each module does one job
- **Dependency Injection** — `OllamaClient` is injected into services (testable)
- **Graceful Failure** — Ollama errors are caught per comment; pipeline never crashes
- **Configuration over Code** — prompts and settings in `config.py`, not scattered inline

## LLM Interaction

Two separate LLM calls per comment:
1. **Analyzer call** — temperature 0.1 (deterministic), expects structured JSON output
2. **Generator call** — temperature 0.7 (creative), produces free-form Thai text

## Model

Gemma 3 4B via Ollama (local inference)
