"""
Structured logging for Astra.

Logs go to the console and to logs/astra.log (under ASTRA_DATA_DIR
when configured).  Sensitive data (credentials, API keys) is never
logged.
"""

import logging
import os

from config.settings import LOG_DIR, LOG_LEVEL

_configured = False

_FORMAT = "[%(levelname)s] %(message)s"

_LOG_FILE = os.path.join(LOG_DIR, "astra.log")


def setup_logger(level=None):
    """Configure the root logger once.  Safe to call repeatedly."""

    global _configured

    if _configured:
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()

    if root.handlers:
        _configured = True
        return

    root.setLevel(
        level or getattr(logging, LOG_LEVEL, logging.INFO)
    )

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    try:
        file_handler = logging.FileHandler(
            _LOG_FILE, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)
    except OSError:
        pass

    _configured = True


def get_logger(name):
    """Return a named logger, configuring the root on first use."""

    setup_logger()

    return logging.getLogger(name)
