import sys

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Простой консольный логгер через loguru (как в tg_agg/flatinfo)."""
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level, backtrace=False, diagnose=False)
