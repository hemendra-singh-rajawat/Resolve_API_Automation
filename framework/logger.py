from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent logger setup. Called from conftest before any tests run."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()

    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> :: <level>{message}</level>"
        ),
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    logger.add(
        LOG_DIR / "run-{time:YYYYMMDD-HHmmss}.log",
        level="DEBUG",
        rotation="50 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    _CONFIGURED = True


def get_logger(name: str):
    configure_logging()
    return logger.bind(name=name)
