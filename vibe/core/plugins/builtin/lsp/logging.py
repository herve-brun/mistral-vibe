"""vibe/core/plugins/builtin/lsp/logging.py
─────────────────────────────────────────────────────────────────────────────
Logging setup for LSP server stdio output.

Routes lsp_client and lsp_server loggers to files in ~/.vibe/logs/lsp/
"""

from __future__ import annotations

import logging
from pathlib import Path


def get_lsp_log_dir() -> Path:
    """Return the LSP log directory path, creating it if needed."""
    from vibe.core.paths import LSP_LOG_DIR
    log_dir = LSP_LOG_DIR.path
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_lsp_logging() -> None:
    """Configure loguru to write LSP server logs to files."""
    from loguru import logger

    log_dir = get_lsp_log_dir()
    lsp_log_file = log_dir / "lsp_client.log"

    logger.add(
        lsp_log_file,
        rotation="10 MB",
        retention="7 days",
        level=logging.DEBUG,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        compression="zip",
    )

    import lsp_client
    lsp_client.enable_logging()

    logger.info("LSP logging initialized, writing to %s", lsp_log_file)