"""Logging setup for the backend application."""

import logging
import sys
from typing import Final

from app.core.config import Settings

LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def setup_logging(settings: Settings, level: int | str | None = None) -> logging.Logger:
    """Configure root logging and return the application logger."""

    log_level = level if level is not None else settings.log_level
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
    )

    logger = logging.getLogger(settings.app_service)
    logger.setLevel(log_level)
    return logger
