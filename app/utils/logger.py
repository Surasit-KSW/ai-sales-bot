"""
Structured logging utility.

Why this pattern?
  Using a factory function (get_logger) instead of a module-level logger
  lets each module get its own named logger. This makes it trivial to
  filter logs by component in production (e.g. analyzer vs generator).
  The FileHandler creates an audit trail — essential when selling to
  businesses that need to prove they didn't spam customers.
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a named logger that writes to both stdout and a rotating log file.

    Args:
        name:  Module name — use __name__ when calling this.
        level: Logging level (default INFO).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    # Guard: don't add duplicate handlers on re-import
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler — shows real-time progress in the terminal.
    # On Windows the default stdout codec is CP874 (Thai) which can't encode
    # emojis or certain Unicode chars. Reconfigure to UTF-8 with replacement
    # so a single unusual character never crashes the whole logger.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # already wrapped or in a non-interactive context
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — audit trail stored in logs/app.log
    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent messages from bubbling up to the root logger (avoids duplicates)
    logger.propagate = False

    return logger
