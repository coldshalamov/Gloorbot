"""Logging configuration helpers for the CheapSkater application."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Force UTF-8 for stdout/stderr on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class SafeStreamHandler(logging.StreamHandler):
    """A StreamHandler that doesn't crash on encoding errors."""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                # Fallback: try to print ascii-only version
                try:
                    safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                    stream.write(safe_msg + self.terminator)
                    self.flush()
                except Exception:
                    # If even that fails, just give up silently.
                    # DO NOT call handleError(record) as it prints to stderr and looks like a crash.
                    pass
        except Exception:
            pass


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with console and rotating file handlers."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(DEFAULT_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT)

        # File Handler (Always UTF-8)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(DEFAULT_LEVEL)

        # Console Handler (Safe)
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(DEFAULT_LEVEL)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
