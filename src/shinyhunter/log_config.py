"""Centralised logging configuration for Shiny Hunter.

Call ``setup_logging()`` once at application start-up (in ``main.py``) so
every module that does ``logging.getLogger(__name__)`` shares the same
format and handler.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format.

    Parameters
    ----------
    level:
        The minimum severity that should be emitted.  Defaults to INFO;
        pass ``logging.DEBUG`` for verbose output during development.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    root = logging.getLogger()
    # Avoid adding duplicate handlers when called more than once
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(level)
