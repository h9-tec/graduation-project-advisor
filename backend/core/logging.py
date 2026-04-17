from __future__ import annotations

import sys
from typing import Any

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru with JSON sink to stdout.

    Idempotent: removes existing handlers before adding.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        serialize=True,
        backtrace=False,
        diagnose=False,
    )


def bind_context(**kwargs: Any) -> Any:
    """Return a logger bound with the given context keys.

    Typical use: ``log = bind_context(session_id=sid, stage="retrieve")``.
    """
    return logger.bind(**kwargs)
