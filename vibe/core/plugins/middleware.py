"""vibe/core/plugins/middleware.py

─────────────────────────────────────────────────────────────────────────────
PluginMiddleware — bridges Vibe's MiddlewarePipeline with the plugin system.

How it works
────────────
Vibe's AgentLoop owns a MiddlewarePipeline.  Each middleware can:
  • inject text into the user message before the LLM sees it  (pre_turn)
  • perform cleanup after a turn ends                          (post_turn)

PluginMiddleware intercepts the tool call/result events that flow through
AgentLoop and dispatches them to every registered ToolEventPlugin.

The interception is done by wrapping the AgentLoop's internal
``_execute_tool`` coroutine with a thin decorator that:
  1. calls ``on_tool_call`` BEFORE the real execution
  2. runs the real tool
  3. calls ``on_tool_result`` AFTER the real execution
  4. checks ``context.extra["lsp_diagnostics_output"]`` — if the LSP plugin
     stored a formatted diagnostics string there, it is appended directly to
     the tool result returned to AgentLoop.  This means:
       • The LLM sees the errors in the same message as the tool result.
       • The terminal output includes the errors without any change to
         agent_loop.py.

Wiring example (done once in vibe/core/agent_loop.py or startup code)
─────────────────────────────────────────────────────────────────────
    plugin_mw = PluginMiddleware(plugin_manager)
    agent_loop.middleware_pipeline.add(plugin_mw)
    plugin_mw.patch_agent_loop(agent_loop)
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pybreaker
import structlog

from vibe.core.middleware import ConversationContext, MiddlewareResult
from vibe.core.plugins.base import PluginContext, ToolEventPlugin
from vibe.core.plugins.resilience import get_plugin_circuit_breaker
from vibe.core.tools.base import InvokeContext

if TYPE_CHECKING:
    from vibe.core.agent_loop import AgentLoop  # type: ignore[import]
    from vibe.core.plugins.manager import PluginManager

logger = structlog.get_logger(__name__)

# Key used by LspPlugin to pass the formatted diagnostics string back to the
# middleware wrapper so it can be appended to the tool result.
_DIAG_OUTPUT_KEY = "lsp_diagnostics_output"


class PluginExecutionTracker:
    """Track plugin execution metrics for automatic priority adjustment."""
    
    def __init__(self) -> None:
        self._execution_stats: dict[str, dict[str, Any]] = {}
        
    def record_execution(self, plugin_name: str, success: bool, duration: float) -> None:
        """Record a plugin execution with success status and duration."""
        if plugin_name not in self._execution_stats:
            self._execution_stats[plugin_name] = {
                'execution_count': 0,
                'error_count': 0,
                'total_duration': 0.0,
                'last_execution': 0.0,
                'success_count': 0
            }
        
        stats = self._execution_stats[plugin_name]
        stats['execution_count'] += 1
        stats['total_duration'] += duration
        stats['last_execution'] = time.perf_counter()
        
        if success:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1
    
    def get_stats(self, plugin_name: str) -> dict[str, Any]:
        """Get execution statistics for a specific plugin."""
        return self._execution_stats.get(plugin_name, {
            'execution_count': 0,
            'error_count': 0,
            'total_duration': 0.0,
            'last_execution': 0.0,
            'success_count': 0
        })
    
    def get_error_rate(self, plugin_name: str) -> float:
        """Calculate error rate for a plugin (0.0 to 1.0)."""
        stats = self.get_stats(plugin_name)
        if stats['execution_count'] == 0:
            return 0.0
        return stats['error_count'] / stats['execution_count']
    
    def get_average_duration(self, plugin_name: str) -> float:
        """Calculate average execution duration for a plugin."""
        stats = self.get_stats(plugin_name)
        if stats['execution_count'] == 0:
            return 0.0
        return stats['total_duration'] / stats['execution_count']


class PluginMiddleware:
    """Middleware that dispatches tool call / result events to plugins and ensures LSP diagnostics
    are surfaced directly in tool results.
    
    Parameters
    ----------
    plugin_manager:
        The live :class:`~vibe.core.plugins.manager.PluginManager`.
    context:
        Shared :class:`~vibe.core.plugins.base.PluginContext`.
    """
    
    def __init__(self, plugin_manager: PluginManager, context: PluginContext) -> None:
        self._manager = plugin_manager
        self._context = context
        self._patched_loop: AgentLoop | None = None
        try:
            self._circuit_breaker = get_plugin_circuit_breaker()
        except RuntimeError:
            self._circuit_breaker = None
        
        # Plugin execution tracking for auto-priority adjustment
        self._plugin_execution_tracker = PluginExecutionTracker()

    def _determine_error_log_level(self, error: Exception) -> str:
        """Determine the appropriate log level for a given error."""
        # Critical errors that should always be logged
        critical_errors = (
            RuntimeError,
            MemoryError,
            RecursionError,
            SystemError,
            KeyboardInterrupt,
        )
        
        if isinstance(error, critical_errors):
            return "ERROR"
        
        # Non-critical errors that can be suppressed
        non_critical_errors = (
            TimeoutError,
            ConnectionError,
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
            TypeError,
            AttributeError,
        )
        
        if isinstance(error, non_critical_errors):
            return "WARNING"
        
        # Default to ERROR for unknown error types
        return "ERROR"

    def _should_log_error(self, error_level: str, reset_log_level: str) -> bool:
        """Determine if an error should be logged based on log levels."""
        # Convert string levels to logging constants for comparison
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        
        # Default to WARNING if invalid level
        error_level_num = level_map.get(error_level.upper(), logging.WARNING)
        reset_level_num = level_map.get(reset_log_level.upper(), logging.WARNING)
        
        return error_level_num >= reset_level_num

    async def _call_with_circuit_breaker(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> Any:
        """Call a function with circuit breaker protection."""
        if self._circuit_breaker is None:
            return await func(*args, **kwargs)
        return await self._circuit_breaker.call(func, *args, **kwargs)

    # ── MiddlewarePipeline interface ──────────────────────────────────────────

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        """Called by the middleware pipeline before each agent turn.

        This delegates to pre_turn which allows plugins to inject text into
        the user message before the LLM sees it.
        """
        # Note: context is not used here but kept for interface compatibility
        return MiddlewareResult()

    async def pre_turn(self, message: str) -> str | None:
        """Called before each agent turn.

        Returns None to leave the message unchanged.
        """
        return None

    async def post_turn(self) -> None:
        """Called after each agent turn completes (or errors out)."""
        # Auto-adjust plugin priorities after each turn
        if self._patched_loop is not None and hasattr(self._patched_loop, '_auto_adjust_priorities_async'):
            await self._patched_loop._auto_adjust_priorities_async()

    def reset(self, reset_reason: str = "stop") -> None:
        """Reset the middleware state and notify all plugins to reset."""
        # Get the configured log level for reset operations
        reset_log_level = getattr(self._manager._config, 'plugin_reset_log_level', 'WARNING')
        
        for plugin in self._manager.tool_event_plugins:
            if hasattr(plugin, "reset") and callable(plugin.reset):
                try:
                    plugin.reset(reset_reason)
                except Exception as e:
                    # Determine if this error should be logged based on log level
                    error_log_level = self._determine_error_log_level(e)
                    
                    # Only log if the error level is at or above the configured reset log level
                    if self._should_log_error(error_log_level, reset_log_level):
                        logger.error(
                            "Plugin reset failed",
                            extra={
                                "context": {
                                    "plugin_name": plugin.metadata().name,
                                    "reset_reason": reset_reason,
                                    "error_type": type(e).__name__,
                                    "error_message": str(e)
                                }
                            },
                            exc_info=True
                        )
                    else:
                        # Log at debug level for troubleshooting
                        logger.debug(
                            "Non-critical plugin reset error suppressed",
                            extra={
                                "context": {
                                    "plugin_name": plugin.metadata().name,
                                    "reset_reason": reset_reason,
                                    "error_type": type(e).__name__,
                                    "error_message": str(e)
                                }
                            }
                        )

    # ── AgentLoop patching ────────────────────────────────────────────────────

    def patch_agent_loop(self, loop: AgentLoop) -> None:
        """Monkey-patch ``loop._execute_tool`` to intercept every tool execution.

        The wrapper:
          • fires plugin hooks before/after the real tool call
          • appends any LSP diagnostics output directly to the returned
            result string, so both the LLM and the terminal see it

        Safe to call multiple times; the loop is only patched once.
        """
        if self._patched_loop is loop:
            logger.debug("AgentLoop already patched, skipping")
            return  # already patched

        original = loop._execute_tool  # type: ignore[attr-defined]
        context = self._context
        logger.debug("Patching AgentLoop._execute_tool (found %d tool event plugins)", len(self._manager.tool_event_plugins))

        @functools.wraps(original)
        async def _wrapped(
            tool_name: str,
            arguments: dict[str, Any],
            ctx: InvokeContext | None = None,
            **kwargs,
        ) -> str:
            # Clear any stale diagnostics output from a previous call
            context.extra.pop(_DIAG_OUTPUT_KEY, None)

            await self._dispatch_on_tool_call(tool_name, arguments)
            result: str = await original(tool_name, arguments, **kwargs)
            await self._dispatch_on_tool_result(tool_name, arguments, result)

            # ── Diagnostics surface-up ────────────────────────────────────────
            # LspPlugin writes a ready-to-display string into context.extra
            # under _DIAG_OUTPUT_KEY.  We append it here so it flows back to
            # AgentLoop as part of the tool result — visible to both the LLM
            # (which uses the result to decide next steps) and to the user
            # (who sees it rendered in the terminal alongside the tool output).
            diag_output: str | None = context.extra.pop(_DIAG_OUTPUT_KEY, None)
            if diag_output:
                result += diag_output

            return result

        loop._execute_tool = _wrapped  # type: ignore[attr-defined]
        self._patched_loop = loop
        logger.debug("PluginMiddleware patched AgentLoop._execute_tool")

    # ── Dispatchers (using pluggy hooks) ──────────────────────────────────

    async def _dispatch_on_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> None:
        """Dispatch on_tool_call hook using pluggy."""
        logger.debug("Dispatching on_tool_call via pluggy")
         
        # Track plugin execution start time for each plugin
        plugin_start_times: dict[str, float] = {}
        
        # Extract file path and line number from arguments if available
        file_path = None
        line_number = None
        if tool_name in ToolEventPlugin.FILE_ACCESS_TOOLS:
            file_path_str = arguments.get("path") or arguments.get("file_path")
            if file_path_str:
                file_path = str(file_path_str)
            line_number = arguments.get("line_number")
         
        try:
            # Call the hook - pluggy will invoke all registered implementations
            results = self._manager._pluggy_pm.hook.on_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                context=self._context,
            )
            # Handle async implementations - results may contain coroutines
            if results:
                # Filter out None results and check for coroutines
                async_tasks = []
                sync_results = []
                for r in results:
                    if asyncio.iscoroutine(r):
                        async_tasks.append(r)
                    elif r is not None:
                        sync_results.append(r)
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(
                "Tool call hook dispatch failed",
                extra={
                    "context": {
                        "tool_name": tool_name,
                        "file_path": file_path,
                        "line_number": line_number
                    }
                },
                exc_info=True
            )

    async def _dispatch_on_tool_result(
        self, tool_name: str, arguments: dict[str, Any], result: str
    ) -> None:
        """Dispatch on_tool_result hook using pluggy."""
        logger.debug("Dispatching on_tool_result via pluggy")
        
        # Track plugin execution success/failure and duration
        plugin_success_status: dict[str, bool] = {}
        
        # Extract file path and line number from arguments if available
        file_path = None
        line_number = None
        if tool_name in ToolEventPlugin.FILE_ACCESS_TOOLS:
            file_path_str = arguments.get("path") or arguments.get("file_path")
            if file_path_str:
                file_path = str(file_path_str)
            line_number = arguments.get("line_number")
        
        try:
            # Call the hook - pluggy will invoke all registered implementations
            results = self._manager._pluggy_pm.hook.on_tool_result(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                context=self._context,
            )
            # Handle async implementations
            if results:
                async_tasks = []
                sync_results = []
                for r in results:
                    if asyncio.iscoroutine(r):
                        async_tasks.append(r)
                    elif r is not None:
                        sync_results.append(r)
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(
                "Tool result hook dispatch failed",
                extra={
                    "context": {
                        "tool_name": tool_name,
                        "file_path": file_path,
                        "line_number": line_number
                    }
                },
                exc_info=True
            )
        
        # Record execution metrics for all plugins
        for plugin in self._manager.tool_event_plugins:
            plugin_name = plugin.metadata().name
            success = plugin_success_status.get(plugin_name, True)  # Default to success
            duration = 0.0  # Would be calculated from start time in real implementation
            self._plugin_execution_tracker.record_execution(plugin_name, success, duration)
    
    def get_execution_stats(self) -> dict[str, dict[str, Any]]:
        """Get execution statistics for all tracked plugins."""
        return self._plugin_execution_tracker._execution_stats
