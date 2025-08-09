import logging
import os
import sys
from typing import Optional

try:
    from rich.logging import RichHandler  # type: ignore
except Exception:  # pragma: no cover
    RichHandler = None  # Fallback if rich is not available


def setup_logging(level: Optional[str] = None, use_json: bool = False) -> None:
    """Configure application-wide logging.
    - level: e.g. "DEBUG", "INFO", "WARNING", "ERROR"
    - use_json: emit JSON lines for structured logging
    """
    log_level = (level or os.getenv("VIDEO_ANALYTICS_LOG_LEVEL") or "INFO").upper()

    root_logger = logging.getLogger()
    # Clear existing handlers to avoid duplicate logs if re-initialized
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    if use_json:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '{"t":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
        )
    else:
        # Prefer RichHandler when available for nicer console output
        if RichHandler is not None:
            handler = RichHandler(rich_tracebacks=False, show_time=False, show_path=False)
            formatter = logging.Formatter("%(message)s")
        else:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a namespaced logger; defaults to package root name."""
    return logging.getLogger(name or "video_analytics")
