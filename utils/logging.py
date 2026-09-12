"""Structured logging configuration with rotation and credential scrubbing."""

import logging
from logging.handlers import RotatingFileHandler
import os
import re
from pathlib import Path
from typing import Optional


class SensitiveFilter(logging.Filter):
    """Filters out tokens, secrets, and sensitive passwords from log lines."""

    PATTERNS = [
        re.compile(r"(token=)[\w\.\-]+", re.IGNORECASE),
        re.compile(r"(password=)[\w\.\-]+", re.IGNORECASE),
        re.compile(r"(client_secret=)[\w\.\-]+", re.IGNORECASE),
        re.compile(r"(Authorization: Bearer\s+)[\w\.\-]+", re.IGNORECASE),
        re.compile(r"([A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,})"),  # Discord token regex
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in self.PATTERNS:
                msg = pattern.sub(r"\1***REDACTED***", msg)
            record.msg = msg
        return True


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = "logs/bot.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Initialize structured console and rotating file logging."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    # Formatter
    console_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(console_format, date_format)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveFilter())
    root_logger.addHandler(console_handler)

    # File Handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveFilter())
        root_logger.addHandler(file_handler)

    # Quiet overly chatty libraries
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.INFO)
    logging.getLogger("wavelink").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Utility to get namespaced loggers."""
    return logging.getLogger(name)
