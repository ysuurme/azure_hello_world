"""
Centralized logging module.

Provides:
- setup_logging()   : One-time configuration (call from main.py)
- f_log()           : Single logging function used across all modules
- f_log_calls()     : Decorator for function entry/exit timing
- f_log_execution() : Program-level execution timer

Logging profiles (set LOG_PROFILE in .env):
- PRD   : Stage markers + warnings/errors only
- TEST  : All INFO-level messages
- DEBUG : Full execution detail with module names
"""

###############################################################################
# IMPORTS
###############################################################################

import logging
import textwrap
import time
from enum import StrEnum
from functools import wraps

from src.config import settings

###############################################################################
# CONSTANTS
###############################################################################

# Custom log level for stage markers (sits between INFO=20 and WARNING=30)
STAGE = 25
logging.addLevelName(STAGE, "STAGE")


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    START = "start"
    PROCESS = "process"
    SUCCESS = "success"
    STORE = "store"
    REGISTER = "register"
    COMPLETE = "complete"
    GATE_FAIL = "gate_fail"


# Emoji auto-prepended for stage-level entries
STAGE_EMOJI: dict[LogLevel, str] = {
    LogLevel.START: "🚀",
    LogLevel.PROCESS: "⚙️",
    LogLevel.SUCCESS: "✅",
    LogLevel.STORE: "💾",
    LogLevel.REGISTER: "📦",
    LogLevel.COMPLETE: "🎉",
    LogLevel.GATE_FAIL: "🚫",
}

_STAGE_LEVELS: set[LogLevel] = set(STAGE_EMOJI)

_PROFILE_LEVELS: dict[str, int] = {
    "PRD": STAGE,
    "TEST": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_PROFILE_FORMATS: dict[str, str] = {
    "PRD": "%(message)s",
    "TEST": "%(asctime)s - %(levelname)s - %(message)s",
    "DEBUG": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
}

# Guard against double configuration
_is_configured: bool = False

# Single named logger — replace "app" with your project name
_logger = logging.getLogger("app")

###############################################################################
# FORMATTER
###############################################################################


class IndentedFormatter(logging.Formatter):
    """Wraps long lines and indents continuation lines for log file readability."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        parts = formatted.split(" - ", 2)
        if len(parts) < 3 or len(formatted) <= settings.log_line_width:
            return formatted

        prefix = f"{parts[0]} - {parts[1]} - "
        wrapped = textwrap.fill(
            parts[2],
            width=settings.log_line_width - len(prefix),
            initial_indent="",
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines = wrapped.split("\n")
        lines[0] = prefix + lines[0]
        return "\n".join(lines)


###############################################################################
# SETUP
###############################################################################


def setup_logging(profile: str | None = None) -> None:
    """
    One-time logging configuration. Call once from main.py before any f_log() calls.

    Sets up two handlers:
    - Console : level and format driven by LOG_PROFILE
    - File    : always captures DEBUG-level to logs/application.log

    Parameters
    ----------
    profile : str, optional
        Override LOG_PROFILE from .env. One of "PRD", "TEST", "DEBUG".
    """
    global _is_configured
    if _is_configured:
        return

    active_profile = profile or settings.log_profile
    if active_profile not in _PROFILE_LEVELS:
        active_profile = "PRD"

    for handler in _logger.handlers[:]:
        _logger.removeHandler(handler)
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = True

    console_handler = logging.StreamHandler()
    console_handler.setLevel(_PROFILE_LEVELS[active_profile])
    console_handler.setFormatter(
        logging.Formatter(fmt=_PROFILE_FORMATS[active_profile], datefmt="%H:%M:%S")
    )
    _logger.addHandler(console_handler)

    settings.log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(
        filename=settings.log_dir / "application.log",
        mode="a",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        IndentedFormatter(
            fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(file_handler)

    for noisy in ("httpx", "urllib3", "git"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _is_configured = True


def _ensure_setup() -> None:
    """Lazy initialisation guard — allows f_log() without an explicit setup_logging() call."""
    if not _is_configured:
        setup_logging()


###############################################################################
# PUBLIC API
###############################################################################


def f_log(
    message: str,
    level: str | LogLevel = LogLevel.INFO,
    raise_exc: bool = False,
    sep_before: str | None = None,
    sep_after: str | None = None,
) -> None:
    """
    Central logging function for all project modules.

    Parameters
    ----------
    message : str
        The message to log.
    level : str | LogLevel
        Standard: "debug", "info", "warning", "error", "critical".
        Stage (emoji auto-prepended): "start", "process", "success",
        "store", "register", "complete", "gate_fail".
    raise_exc : bool
        Raise Exception after logging when level is "error" or "critical".
    sep_before : str, optional
        Separator character repeated across full width before the message.
    sep_after : str, optional
        Separator character repeated across full width after the message.
    """
    _ensure_setup()

    try:
        level = LogLevel(level)
    except ValueError:
        level = LogLevel.INFO

    if level in _STAGE_LEVELS:
        log_level = STAGE
        formatted = f"{STAGE_EMOJI[level]} {message}"
    else:
        log_level = logging.getLevelName(level.upper())
        formatted = message

    if sep_before is not None:
        _logger.log(log_level, sep_before * settings.log_separator_width)
    _logger.log(log_level, formatted)
    if sep_after is not None:
        _logger.log(log_level, sep_after * settings.log_separator_width)

    if level in (LogLevel.ERROR, LogLevel.CRITICAL) and raise_exc:
        raise Exception(message)


###############################################################################
# DECORATORS
###############################################################################


def f_log_calls(separator: str = "-"):
    """
    Decorator that logs entry and exit of a function call.

    Parameters
    ----------
    separator : str
        Character used for separator lines around the log messages.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            f_log(f"Start {func.__name__}()", sep_before=separator)
            result = func(*args, **kwargs)
            f_log(f"End   {func.__name__}()", sep_after=separator)
            return result

        return wrapper

    return decorator


###############################################################################
# EXECUTION TIMER
###############################################################################

_start_times: dict[str, float] = {}


def f_log_execution(project: str, start: bool = True) -> None:
    """
    Log the start or end of a program run with elapsed time.

    Parameters
    ----------
    project : str
        Project identifier (displayed in uppercase in log output).
    start : bool
        True to record start time; False to log elapsed time since start.
    """
    action = "Start" if start else "End"

    if start:
        _start_times[project] = time.time()
        f_log(f"{action} of {project.upper()}.", sep_before="=", sep_after="=")
        return

    f_log(f"{action} of {project.upper()}.", sep_before="=", sep_after="-")

    if project not in _start_times:
        f_log(
            "No start time recorded. Call f_log_execution(start=True) first.",
            level=LogLevel.WARNING,
            sep_after="=",
        )
        return

    elapsed = time.time() - _start_times.pop(project)
    f_log(
        f"Total execution time: {elapsed:.2f}s ({elapsed / 60:.2f} min)",
        sep_after="=",
    )
