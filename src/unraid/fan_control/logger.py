import logging
from logging.handlers import RotatingFileHandler

from .config import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_MAX_BYTES,
    LOG_DIR,
)


class CategoryFormatter(logging.Formatter):
    """
    Formato común del log:

    2026-09-14 17:45:12.345 [INFO] [SERIAL] mensaje
    """

    def format(self, record):
        category = getattr(record, "category", "GENERAL")

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        milliseconds = int(record.created * 1000) % 1000

        return (
            f"{timestamp}.{milliseconds:03d} "
            f"[{record.levelname}] "
            f"[{category}] "
            f"{record.getMessage()}"
        )


def setup_logger(name="rp2040_fan_control"):
    """
    Crea y devuelve el logger principal de V3.0.
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    handler.setFormatter(CategoryFormatter())
    logger.addHandler(handler)

    return logger


def log_info(logger, category, message):
    logger.info(message, extra={"category": category})


def log_warning(logger, category, message):
    logger.warning(message, extra={"category": category})


def log_error(logger, category, message):
    logger.error(message, extra={"category": category})


def log_debug(logger, category, message):
    logger.debug(message, extra={"category": category})
