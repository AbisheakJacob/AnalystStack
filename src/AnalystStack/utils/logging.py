import logging
import sys

_QUIET = False
_SILENT_LEVEL = logging.CRITICAL + 1


def get_logger(name: str) -> logging.Logger:
    """Creates and returns a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(_SILENT_LEVEL if _QUIET else logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def set_quiet(quiet: bool = True) -> None:
    """Silences (or restores) every AnalystStack logger, including ones created later.

    The command-line interface calls this at startup because connector log lines can name the
    host, port or database a connection was built from, and those values come from ``.env``
    files that must never be echoed.

    Args:
        quiet: True to silence all AnalystStack logging, False to restore INFO level.
    """
    global _QUIET
    _QUIET = quiet
    level = _SILENT_LEVEL if quiet else logging.INFO
    for name, candidate in list(logging.root.manager.loggerDict.items()):
        if name.startswith("AnalystStack") and isinstance(candidate, logging.Logger):
            candidate.setLevel(level)
