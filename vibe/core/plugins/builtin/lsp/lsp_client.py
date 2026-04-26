"""vibe/core/plugins/builtin/lsp/lsp_client.py
────────────────────────────────────────────────────────────────────────────
Async wrapper around a single Language Server Protocol process.

Uses lsp-client library (supports lsprotocol 2025+).
Each LspClient instance owns one LSP subprocess for one language.

Lifecycle
────────
    client = LspClient(cfg, root)
    await client.start()          # spawn process
    ...
    diags  = await client.diagnostics("src/foo.py")
    ...
    await client.stop()        # shutdown

Document synchronisation
───────────────────────
Files are opened on-demand via request methods.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from vibe.core.plugins.builtin.lsp.registry import LspConfig

logger = logging.getLogger(__name__)

# Seconds to wait for server to respond to requests.
_REQUEST_TIMEOUT = 10.0

# Map language to lsp-client client class
_LSP_CLIENTS: dict[str, str] = {
    "python": "BasedpyrightClient",
    "typescript": "TypescriptClient",
    "rust": "RustAnalyzerClient",
    "go": "GoplsClient",
    "deno": "DenoClient",
}


class LspClientError(RuntimeError):
    """Raised when an LSP operation fails."""


class LspClient:
    """Manages one LSP server subprocess for a single language.

    Parameters
    ----------
    config:
        :class:`~vibe.core.plugins.builtin.lsp.registry.LspConfig` that
        describes the server to start.
    root:
        Absolute path to the project root (workdir).
    """

    def __init__(self, config: LspConfig, root: Path) -> None:
        self._cfg = config
        self._root = root
        self._client: Any = None
        self._started = False
        self._client_class: type | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Spawn the LSP process and perform the LSP handshake."""
        if self._started:
            return
        if not self._cfg.is_available():
            raise LspClientError(
                f"LSP executable not found: {self._cfg.command[0]!r}. "
                f"Please install the {self._cfg.language} language server."
            )

        try:
            from lsp_client import clients
        except ImportError as exc:
            raise LspClientError(f"lsp-client not installed: {exc}") from exc

        client_class_name = _LSP_CLIENTS.get(self._cfg.language)
        if not client_class_name:
            raise LspClientError(
                f"No lsp-client for language: {self._cfg.language}. "
                f"Supported: {list(_LSP_CLIENTS.keys())}"
            )

        try:
            self._client_class = getattr(clients, client_class_name)
        except AttributeError as exc:
            raise LspClientError(
                f"Client class not found: {client_class_name}"
            ) from exc

        try:
            # Use async context manager - creates and starts the client
            self._client = self._client_class(
                server="local",
                workspace=self._root,
                sync_file=True,
                request_timeout=_REQUEST_TIMEOUT,
            )
            # Start server (async context manager enters and starts)
            await self._client.__aenter__()
        except Exception as exc:
            logger.error("Failed to start LSP for %s: %s", self._cfg.language, exc)
            self._client = None
            raise LspClientError(
                f"Failed to start LSP for {self._cfg.language!r}: {exc}"
            ) from exc

        self._started = True
        logger.info("LSP started: %s (%s)", self._cfg.language, self._cfg.command[0])

    async def stop(self) -> None:
        """Send shutdown/exit to the server and clean up."""
        if not self._started or self._client is None:
            return
        try:
            await self._client.__aexit__(None, None, None)
        except Exception as exc:
            logger.debug("LSP stop error (%s): %s", self._cfg.language, exc)
        finally:
            self._started = False
            self._client = None

    # ── LSP capabilities ────────────────────────────────────────────────────────

    async def diagnostics(self, file_path: str) -> list[dict[str, Any]]:
        """Return diagnostics for *file_path*."""
        self._assert_started()

        try:
            result = await self._client.request_text_document_diagnostics(
                file_path=file_path,
            )
        except Exception as e:
            logger.warning("diagnostics error: %s", e)
            return []

        if not result:
            return []

        return [
            self._format_diagnostic(d) for d in result
        ]

    async def completion(
        self, file_path: str, line: int, col: int
    ) -> list[dict[str, Any]]:
        """Return completion items at the given 1-indexed position."""
        self._assert_started()
        from lsp_client import Position

        try:
            result = await self._client.request_completion(
                file_path=file_path,
                position=Position(line - 1, col - 1),
            )
        except Exception as e:
            logger.warning("completion error: %s", e)
            return []

        items = result if isinstance(result, list) else []
        return [self._format_completion_item(i) for i in items[:50]]

    async def hover(self, file_path: str, line: int, col: int) -> dict[str, Any]:
        """Return hover information at the given 1-indexed position."""
        self._assert_started()
        from lsp_client import Position

        try:
            result = await self._client.request_hover(
                file_path=file_path,
                position=Position(line - 1, col - 1),
            )
        except Exception as e:
            logger.warning("hover error: %s", e)
            return {"content": "", "kind": "plaintext"}

        if not result:
            return {"content": "", "kind": "plaintext"}

        # Result can be string or MarkupContent
        if hasattr(result, "contents"):
            contents = result.contents
            if hasattr(contents, "value"):
                return {"content": contents.value, "kind": getattr(contents, "kind", "markdown")}
            return {"content": str(contents), "kind": "plaintext"}
        return {"content": str(result), "kind": "plaintext"}

    async def definition(
        self, file_path: str, line: int, col: int
    ) -> list[dict[str, Any]]:
        """Return the definition location(s) of the symbol at position."""
        self._assert_started()
        from lsp_client import Position

        try:
            result = await self._client.request_definition_locations(
                file_path=file_path,
                position=Position(line - 1, col - 1),
            )
        except Exception as e:
            logger.warning("definition error: %s", e)
            return []

        locations = result if isinstance(result, list) else ([result] if result else [])
        return [self._format_location(loc) for loc in locations if loc is not None]

    async def references(
        self, file_path: str, line: int, col: int, include_declaration: bool = True
    ) -> list[dict[str, Any]]:
        """Return all references to the symbol at position."""
        self._assert_started()
        from lsp_client import Position

        try:
            result = await self._client.request_references(
                file_path=file_path,
                position=Position(line - 1, col - 1),
                include_declaration=include_declaration,
            )
        except Exception as e:
            logger.warning("references error: %s", e)
            return []

        return [self._format_location(loc) for loc in (result or [])]

    # ── Formatters ────────────────────────────────────────────────────────────

    @staticmethod
    def _format_diagnostic(d: Any) -> dict[str, Any]:
        severity_map = {1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}
        
        # Handle different response formats
        if hasattr(d, "severity"):
            sev = d.severity.value if hasattr(d.severity, "value") else d.severity
        elif isinstance(d, dict):
            sev = d.get("severity")
        else:
            sev = None
        
        if hasattr(d, "range"):
            rng = d.range
            line = rng.start.line + 1 if hasattr(rng.start, "line") else 1
            col = rng.start.character + 1 if hasattr(rng.start, "character") else 1
            end_line = rng.end.line + 1 if hasattr(rng.end, "line") else line
            end_col = rng.end.character + 1 if hasattr(rng.end, "character") else col
        elif isinstance(d, dict):
            rng = d.get("range", {})
            line = rng.get("start", {}).get("line", 0) + 1
            col = rng.get("start", {}).get("character", 0) + 1
            end_line = rng.get("end", {}).get("line", 0) + 1
            end_col = rng.get("end", {}).get("character", 0) + 1
        else:
            line = col = end_line = end_col = 1

        return {
            "severity": severity_map.get(int(sev) if sev else 0, "Unknown"),
            "line": line,
            "col": col,
            "end_line": end_line,
            "end_col": end_col,
            "message": getattr(d, "message", d.get("message", "") if isinstance(d, dict) else ""),
            "source": getattr(d, "source", d.get("source", "") if isinstance(d, dict) else ""),
            "code": str(getattr(d, "code", d.get("code", "") if isinstance(d, dict) else "")),
        }

    @staticmethod
    def _format_completion_item(i: Any) -> dict[str, Any]:
        kind_map = {
            1: "Text", 2: "Method", 3: "Function", 4: "Constructor",
            5: "Field", 6: "Variable", 7: "Class", 8: "Interface",
            9: "Module", 10: "Property", 14: "Keyword", 17: "File",
        }
        
        kind = getattr(i, "kind", None) if hasattr(i, "kind") else i.get("kind") if isinstance(i, dict) else None
        if hasattr(kind, "value"):
            kind = kind.value
        
        return {
            "label": getattr(i, "label", i.get("label", "") if isinstance(i, dict) else ""),
            "kind": kind_map.get(int(kind) if kind else 0, "Unknown"),
            "detail": getattr(i, "detail", i.get("detail", "") if isinstance(i, dict) else ""),
            "documentation": getattr(i, "documentation", "") or (i.get("documentation", {}).get("value", "") if isinstance(i, dict) else ""),
        }

    @staticmethod
    def _format_location(loc: Any) -> dict[str, Any]:
        uri = getattr(loc, "uri", "") or (loc.get("uri") if isinstance(loc, dict) else "")
        file_path = uri.replace("file://", "") if uri.startswith("file://") else uri
        
        if hasattr(loc, "range"):
            rng = loc.range
            line = rng.start.line + 1 if hasattr(rng.start, "line") else 1
            col = rng.start.character + 1 if hasattr(rng.start, "character") else 1
        elif isinstance(loc, dict):
            rng = loc.get("range", {})
            line = rng.get("start", {}).get("line", 0) + 1
            col = rng.get("start", {}).get("character", 0) + 1
        else:
            line = col = 1

        return {"file": file_path, "line": line, "col": col}

    # ── Internal ───────────────────────────────────────────────────────────

    def _assert_started(self) -> None:
        if not self._started or self._client is None:
            raise LspClientError(
                f"LSP client for {self._cfg.language!r} is not started."
            )

    @property
    def language(self) -> str:
        return self._cfg.language

    @property
    def is_running(self) -> bool:
        return self._started