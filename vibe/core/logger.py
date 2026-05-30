from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
from typing import Any

from vibe.core.paths import LOG_DIR, LOG_FILE

LOG_DIR.path.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("vibe")


class ContextFilter(logging.Filter):
    """Filter to inject context into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Allow context to be passed via extra parameter
        if hasattr(record, "context"):
            # Context already set, no action needed
            return True
        
        # If no context is provided, set an empty dict
        record.context = {}
        return True


class JSONStructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        level = record.levelname
        message = record.getMessage()

        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "logger": record.name,
            "line": record.lineno,
            "function": record.funcName,
            "context": record.__dict__.get("context", {}),
        }

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_entry["stack_trace"] = exc_text

        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        ppid = os.getppid()
        pid = os.getpid()
        level = record.levelname
        message = encode_log_message(record.getMessage())

        line = f"{timestamp} {ppid} {pid} {level} {record.name}:{record.lineno}:{record.funcName} {message}"

        if record.exc_info:
            exc_text = encode_log_message(self.formatException(record.exc_info))
            line = f"{line} {exc_text}"

        return line


def encode_log_message(message: str) -> str:
    return message.replace("\\", "\\\\").replace("\n", "\\n")


def decode_log_message(encoded: str) -> str:
    return re.sub(
        r"\\(.)", lambda m: "\n" if m.group(1) == "n" else m.group(1), encoded
    )


def apply_logging_config(target_logger: logging.Logger) -> None:
    LOG_DIR.path.mkdir(parents=True, exist_ok=True)

    max_bytes = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))

    if os.environ.get("DEBUG_MODE") == "true":
        log_level_str = "DEBUG"
    else:
        log_level_str = os.environ.get("LOG_LEVEL", "WARNING").upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level_str not in valid_levels:
            log_level_str = "WARNING"

    handler = RotatingFileHandler(
        LOG_FILE.path, maxBytes=max_bytes, backupCount=0, encoding="utf-8"
    )
    
    # Use JSON formatter for structured logging with context support
    handler.setFormatter(JSONStructuredLogFormatter())
    
    # Add context filter to inject context into log records
    context_filter = ContextFilter()
    target_logger.addFilter(context_filter)
    
    log_level = getattr(logging, log_level_str, logging.WARNING)
    handler.setLevel(log_level)

    # Make sure the logger is not gating logs
    target_logger.setLevel(logging.DEBUG)

    target_logger.addHandler(handler)


# Backward compatibility functions for existing tests
def configure_structlog() -> None:
    """Configure structlog (backward compatibility)."""
    # Apply logging config to root logger
    root_logger = logging.getLogger()
    apply_logging_config(root_logger)
    
    # Also configure any existing loggers that might need it
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name and not logger_name.startswith('pytest'):
            logger = logging.getLogger(logger_name)
            if not logger.handlers:
                apply_logging_config(logger)


def get_structured_logger(name: str) -> logging.Logger:
    """Get a structured logger (backward compatibility)."""
    logger = logging.getLogger(name)
    # Ensure the logger has the proper configuration
    if not logger.handlers:
        apply_logging_config(logger)
    return logger


apply_logging_config(logger)
