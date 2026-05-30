"""vibe/core/plugins/manager.py

─────────────────────────────────────────────────────────────────────────────
PluginManager — discovers, instantiates, and manages Vibe plugins.

Discovery rules (in priority order, first match wins per plugin name)
──────────────────────────────────────────────────────────────────────
1. Paths listed in ``config.plugin_paths``          (user overrides)
2. ``{VIBE_HOME}/plugins/``                         (user global plugins)
3. ``{workdir}/.vibe/plugins/``                     (project-local plugins)
4. ``vibe.core.plugins.builtin``                    (built-in plugins)

Each search path is scanned for Python packages/modules that contain a
class that:
  • inherits from :class:`~vibe.core.plugins.base.VibePlugin`
  • is not abstract (i.e. can be instantiated)
  • is not the base class itself

Filtering (same semantics as tool/skill filtering in VibeConfig):
  • ``enabled_plugins``  → whitelist (supports exact names, globs, regex)
  • ``disabled_plugins`` → blacklist applied after whitelist
"""

from __future__ import annotations

import fnmatch
import importlib
import importlib.metadata
import importlib.util
import inspect
import logging
from functools import lru_cache
from pathlib import Path
import re
import sys
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pybreaker
import pluggy

from vibe.core.logger import get_structured_logger
from vibe.core.plugins.base import PluginContext, ToolEventPlugin, VibePlugin
from vibe.core.plugins.command_plugin import CommandPlugin
from vibe.core.plugins.context_aware import ContextAwarePlugin
from vibe.core.plugins.resilience import get_plugin_circuit_breaker
from vibe.core.plugins.extension_points import HookSpecs, HookImplMarker
from vibe.core.plugins.registry import CapabilityRegistry

if TYPE_CHECKING:
    from vibe.core.config import VibeConfig

logger = get_structured_logger(__name__)

# Built-in plugins package (shipped with Vibe)
_BUILTIN_PACKAGE = "vibe.core.plugins.builtin"


class PriorityManager:
    """Manages plugin priorities with caching and context-aware resolution.

    This class consolidates all priority-related logic including caching,
    context-aware resolution, and cache invalidation.
    """

    def __init__(self) -> None:
        self._priority_cache: dict[int, int] = {}  # Cache for plugin priorities by plugin id
        self._context_aware_priority_cache: dict[str, int] = {}  # Cache for context-aware priorities
        self._priority_cache_lock: threading.RLock = threading.RLock()  # Lock for thread-safe cache access
        self._priority_cache_max_size: int = 1000  # Maximum cache size to prevent memory growth
        
        # Initialize LRU cache for plugin priorities
        self._get_priority_cached = lru_cache(maxsize=self._priority_cache_max_size)(self._get_priority_impl)
    
    def _get_priority_impl(self, plugin_id: int) -> int | None:
        """Internal implementation for LRU-cached priority lookup."""
        with self._priority_cache_lock:
            return self._priority_cache.get(plugin_id)
    
    def get_priority(self, plugin_id: int) -> int | None:
        """Get cached priority for a plugin by its id."""
        with self._priority_cache_lock:
            result = self._priority_cache.get(plugin_id)
            logger.debug("Cache hit for plugin_id %d, priority: %s", plugin_id, result)
            return result
    
    def set_priority(self, plugin_id: int, priority: int) -> None:
        """Cache the priority for a plugin."""
        with self._priority_cache_lock:
            self._priority_cache[plugin_id] = priority
            # Enforce LRU cache size limit
            if len(self._priority_cache) > self._priority_cache_max_size:
                # Remove the oldest entry (simple approach - in production you'd want a proper LRU)
                oldest_key = next(iter(self._priority_cache))
                self._priority_cache.pop(oldest_key)
            logger.debug("Cached priority %d for plugin_id %d", priority, plugin_id)
    
    def invalidate_cache(self) -> None:
        """Invalidate the entire priority cache."""
        with self._priority_cache_lock:
            self._priority_cache.clear()
            # Clear the LRU cache as well
            if hasattr(self._get_priority_cached, 'cache_clear'):
                self._get_priority_cached.cache_clear()
            logger.debug("Priority cache invalidated")
    
    def invalidate_plugin_cache(self, plugin_id: int) -> None:
        """Invalidate the priority cache for a specific plugin.
        
        Parameters
        ----------
        plugin_id:
            The id() of the plugin instance whose cache should be invalidated.
        """
        with self._priority_cache_lock:
            self._priority_cache.pop(plugin_id, None)
    
    def resolve_context_aware_priorities(
        self, 
        plugins_with_priority: list[tuple[VibePlugin, int]], 
        context: PluginContext
    ) -> list[tuple[VibePlugin, int]]:
        """Apply context-aware conflict resolution to plugin priorities.
        
        This method allows plugins to adjust their priorities based on the
        current context (workdir, config, etc.).
        """
        resolved = []
        
        for plugin, base_priority in plugins_with_priority:
            # Generate a unique cache key based on plugin name and context hash
            cache_key = self._generate_cache_key(plugin, context)
            
            # Check cache first
            cached_priority = self._context_aware_priority_cache.get(cache_key)
            if cached_priority is not None:
                resolved.append((plugin, cached_priority))
                continue
            
            # Check if plugin implements ContextAwarePlugin interface
            if isinstance(plugin, ContextAwarePlugin):
                try:
                    adjusted_priority = plugin.context_aware_priority(context)
                    if isinstance(adjusted_priority, int):
                        # Cache the result
                        self._context_aware_priority_cache[cache_key] = adjusted_priority
                        # Enforce cache size limit
                        if len(self._context_aware_priority_cache) > self._priority_cache_max_size:
                            # Remove oldest entries (simple FIFO eviction)
                            oldest_key = next(iter(self._context_aware_priority_cache.keys()))
                            self._context_aware_priority_cache.pop(oldest_key, None)
                        resolved.append((plugin, adjusted_priority))
                        continue
                except Exception:
                    # If context-aware priority fails, fall back to base priority
                    logger.debug("Plugin %s context_aware_priority failed, using base priority", 
                                plugin.metadata().name, exc_info=True)
            
            # Use base priority if no context-aware adjustment
            resolved.append((plugin, base_priority))
        
        return resolved
    
    def _generate_cache_key(self, plugin: VibePlugin, context: PluginContext) -> str:
        """Generate a unique cache key for context-aware priority caching.
        
        The key combines the plugin name with a hash of relevant context
        information to ensure cache invalidation when context changes.
        """
        # Create a hash based on plugin name and key context attributes
        context_hash = hash((
            str(context.workdir),
            tuple(sorted(context.config.enabled_plugins or [])),
            tuple(sorted(context.config.disabled_plugins or [])),
        ))
        return f"{plugin.metadata().name}:{context_hash}"


class PluginManager:
    """Manages the full lifecycle of Vibe plugins.

    Parameters
    ----------
    config:
        Live :class:`~vibe.core.config.VibeConfig` instance.
    context:
        :class:`~vibe.core.plugins.base.PluginContext` shared with all plugins.
    command_registry:
        Optional CommandRegistry to register plugin commands into.
    """

    def __init__(
        self, config: VibeConfig, context: PluginContext, command_registry=None
    ) -> None:
        self._config = config
        self._context = context
        self._command_registry = command_registry
        self._plugins: list[VibePlugin] = []
        self._tool_event_plugins: list[ToolEventPlugin] = []
        self._pluggy_pm = pluggy.PluginManager("mistral-vibe")
        self._pluggy_pm.add_hookspecs(HookSpecs)
        self._priority_manager = PriorityManager()  # Dedicated priority manager
        self._capability_registry = CapabilityRegistry(self)  # Capability registry for runtime checks
        
        # Plugin usage statistics tracking
        self._plugin_stats: dict[str, dict] = {}  # plugin_name -> stats dict
        self._stats_lock: threading.RLock = threading.RLock()  # Lock for thread-safe stats access
        self._cached_usage_stats: list[dict] | None = None  # Cache for calculated usage statistics
        try:
            self._circuit_breaker = get_plugin_circuit_breaker()
        except RuntimeError:
            self._circuit_breaker = None
        
    def _get_cached_priority_impl(self, plugin_id: int) -> int | None:
        """Internal implementation for LRU-cached priority lookup."""
        return self._priority_manager.get_priority(plugin_id)

    async def _call_with_circuit_breaker(
        self, func: Callable, *args, **kwargs
    ) -> Any:
        """Call a function with circuit breaker protection."""
        if self._circuit_breaker is None:
            return await func(*args, **kwargs)
        return await self._circuit_breaker.call(func, *args, **kwargs)
    
    def _track_plugin_usage(
        self, plugin_name: str, success: bool, start_time: float
    ) -> None:
        """Track usage statistics for a plugin call.
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin being tracked
        success:
            Whether the call succeeded (True) or failed (False)
        start_time:
            Timestamp when the call started (from time.time())
        """
        with self._stats_lock:
            if plugin_name not in self._plugin_stats:
                self._plugin_stats[plugin_name] = {
                    'calls': 0,
                    'errors': 0,
                    'total_time': 0.0,
                    'last_call': 0.0
                }
            
            stats = self._plugin_stats[plugin_name]
            stats['calls'] += 1
            
            if not success:
                stats['errors'] += 1
            
            execution_time = time.time() - start_time
            stats['total_time'] += execution_time
            stats['last_call'] = time.time()
            
            # Invalidate the cache since we've added new data
            self._cached_usage_stats = None
            logger.debug("Invalidated usage statistics cache after tracking new plugin usage")

    # ── Public API ────────────────────────────────────────────────────────────

    async def discover_and_setup(self) -> None:
        """Discover all eligible plugins and call :meth:`VibePlugin.setup` on each active one.

        This method is idempotent; calling it twice rebuilds the plugin list
        from scratch.
        """
        self._plugins = []
        self._tool_event_plugins = []
        self._pluggy_pm = pluggy.PluginManager("mistral-vibe")
        self._pluggy_pm.add_hookspecs(HookSpecs)
        self._invalidate_priority_cache()

        classes = self._discover_plugin_classes()

        for cls in classes:
            meta = cls.metadata()
            if not self._is_enabled(meta.name):
                logger.debug("Plugin %s disabled by config", meta.name)
                continue
            try:
                instance: VibePlugin = cls()
            except Exception:
                logger.exception("Failed to instantiate plugin %s", meta.name)
                continue

            logger.debug("Checking is_applicable for plugin %s", meta.name)
            is_applicable = instance.is_applicable(self._context)
            logger.info("Plugin %s is_applicable=%s (workdir=%s)", meta.name, is_applicable, self._context.workdir)
            if not is_applicable:
                logger.debug("Plugin %s not applicable to current context", meta.name)
                continue

            try:
                await self._call_with_circuit_breaker(
                    instance.setup, self._context
                )
            except pybreaker.CircuitBreakerError:
                logger.warning(
                    "Plugin %s skipped due to open circuit breaker",
                    meta.name,
                )
                continue
            except Exception:
                logger.exception("Plugin %s raised during setup", meta.name)
                continue

            self._plugins.append(instance)
            # Wrap priority methods to automatically invalidate cache
            self._wrap_plugin_priority_methods(instance)
            # Register plugin capabilities
            self._capability_registry.register_plugin_capabilities(instance)
            if isinstance(instance, ToolEventPlugin):
                self._tool_event_plugins.append(instance)
                # Register with pluggy for hook dispatch
                self._pluggy_pm.register(instance)
                logger.debug("Registered tool event plugin: %s", instance.metadata().name)

            logger.info("Plugin %s (%s) ACTIVATED", meta.name, meta.version)

            # Register commands if this plugin implements CommandPlugin
            if isinstance(instance, CommandPlugin) and self._command_registry:
                try:
                    await instance.register_commands(self._command_registry)
                    logger.debug("Registered commands from plugin %s", meta.name)

                    # Auto-register handler methods for commands added by this plugin
                    # We need to track which commands were just added, but since we can't easily
                    # know that, we'll register handlers only if they exist on the plugin instance
                    for _cmd_name, command in self._command_registry.commands.items():
                        if hasattr(instance, command.handler):
                            handler_method = getattr(instance, command.handler)
                            # Only register if not already registered (to avoid overwriting built-in commands)
                            if command.handler not in self._command_registry._handler_map:
                                self._command_registry.register_handler(command.handler, handler_method)
                except Exception:
                    logger.exception("Plugin %s raised during command registration", meta.name)

            logger.info("Plugin %s (%s) activated", meta.name, meta.version)

    async     def teardown_all(self) -> None:
        """Call :meth:`VibePlugin.teardown` on every active plugin."""
        for plugin in reversed(self._plugins):
            try:
                await self._call_with_circuit_breaker(plugin.teardown)
            except pybreaker.CircuitBreakerError:
                logger.warning(
                    "Plugin %s teardown skipped due to open circuit breaker",
                    plugin.metadata().name,
                )
            except Exception:
                logger.exception(
                    "Plugin %s raised during teardown", plugin.metadata().name
                )
        self._plugins = []
        self._tool_event_plugins = []
        self._pluggy_pm = pluggy.PluginManager("mistral-vibe")
        self._pluggy_pm.add_hookspecs(HookSpecs)
        self._invalidate_priority_cache()
        self._capability_registry.clear()
        
        # Clear usage statistics when all plugins are torn down
        with self._stats_lock:
            self._plugin_stats.clear()
            self._cached_usage_stats = None

    @property
    def tool_event_plugins(self) -> list[ToolEventPlugin]:
        """Active plugins that implement :class:`ToolEventPlugin`."""
        return list(self._tool_event_plugins)

    @property
    def all_plugins(self) -> list[VibePlugin]:
        """All active plugins."""
        return list(self._plugins)

    @property
    def capability_registry(self) -> CapabilityRegistry:
        """Capability registry for runtime capability checks."""
        return self._capability_registry

    def get_sorted_plugins(self, context: PluginContext | None = None) -> list[VibePlugin]:
        """Return plugins sorted by effective priority.
        
        If dynamic priorities are enabled and context is provided, this method
        will use context-aware resolution to determine the final order.
        """
        if not self._plugins:
            return []
            
        # Create a list of (plugin, effective_priority) tuples
        plugins_with_priority = []
        for plugin in self._plugins:
            # Use plugin id() as cache key
            plugin_id = id(plugin)
            cached_priority = self._get_cached_priority(plugin_id)
            if cached_priority is not None:
                effective_priority = cached_priority
            else:
                effective_priority = plugin.effective_priority()
                self._set_cached_priority(plugin_id, effective_priority)
            
            plugins_with_priority.append((plugin, effective_priority))
        
        # Sort by priority (lower values first)
        plugins_with_priority.sort(key=lambda x: x[1])
        
        # Apply context-aware conflict resolution if dynamic priorities are enabled
        if (context is not None and 
            getattr(context.config, 'dynamic_priorities', False)):
            plugins_with_priority = self._resolve_context_aware_priorities(
                plugins_with_priority, context
            )
        
        # Extract just the plugins in the final order
        return [plugin for plugin, _ in plugins_with_priority]
    
    def _resolve_context_aware_priorities(
        self, 
        plugins_with_priority: list[tuple[VibePlugin, int]], 
        context: PluginContext
    ) -> list[tuple[VibePlugin, int]]:
        """Apply context-aware conflict resolution to plugin priorities.
        
        This method allows plugins to adjust their priorities based on the
        current context (workdir, config, etc.).
        """
        return self._priority_manager.resolve_context_aware_priorities(plugins_with_priority, context)

    def summary(self) -> str:
        """Return a human-readable summary of active plugins in markdown format."""
        if not self._plugins:
            return "No plugins active."
        lines = ["## Plugins"]
        for p in self._plugins:
            m = p.metadata()
            lines.append("")
            lines.append(f"### {m.name}")
            lines.append(m.description)
            
            # Add usage statistics if available (only shows actual usage, not setup/teardown)
            usage_stats = self.get_plugin_usage_stats(m.name)
            if usage_stats and usage_stats['calls'] > 0:
                lines.append(f"")
                lines.append(f"**Active Usage**: {usage_stats['calls']} hook calls, "
                           f"{usage_stats['errors']} errors, "
                           f"{usage_stats['avg_time']:.3f}s avg, "
                           f"{usage_stats['error_rate']:.1f}% error rate")
        return "\n".join(lines)

    def get_plugin_statistics(self) -> list[dict]:
        """Return a list of dictionaries containing statistics for all plugins.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary contains
                       plugin statistics such as name, version, priority, and active status.
        """
        logger.debug("Generating statistics for %d active plugins", len(self.all_plugins))
        
        stats = []
        for plugin in self.all_plugins:
            metadata = plugin.metadata()
            plugin_stats = {
                "name": metadata.name,
                "version": metadata.version,
                "priority": metadata.priority,
                "active": True,  # All plugins in _plugins are considered active
            }
            
            # Add usage statistics if available
            usage_stats = self.get_plugin_usage_stats(metadata.name)
            if usage_stats:
                plugin_stats["usage"] = {
                    "calls": usage_stats["calls"],
                    "errors": usage_stats["errors"],
                    "avg_time": usage_stats["avg_time"],
                    "error_rate": usage_stats["error_rate"]
                }
                logger.debug("Plugin '%s' usage stats: %d calls, %.1f%% error rate", 
                           metadata.name, usage_stats["calls"], usage_stats["error_rate"])
            
            stats.append(plugin_stats)
        
        logger.debug("Generated statistics for %d plugins", len(stats))
        return stats

    def _get_circuit_breaker_status(self, plugin_name: str) -> str:
        """Get the circuit breaker status for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            str: Circuit breaker status (e.g., 'Closed', 'Open', 'Half-Open', or 'N/A')
        """
        if self._circuit_breaker is None:
            return "N/A"
        return self._circuit_breaker.state.name
    
    def get_plugin_usage_statistics(self) -> list[dict]:
        """Return usage statistics for all plugins.
        
        Returns:
            list[dict]: A list of dictionaries containing usage statistics including:
                      - name: Plugin name
                      - calls: Total number of calls
                      - errors: Number of failed calls
                      - total_time: Total execution time in seconds
                      - avg_time: Average execution time per call
                      - error_rate: Error rate as percentage
                      - last_call: Timestamp of last call
        """
        with self._stats_lock:
            # Check if we have cached statistics
            if self._cached_usage_stats is not None:
                logger.debug("Returning cached usage statistics for %d plugins", len(self._cached_usage_stats))
                return self._cached_usage_stats
            
            logger.debug("Generating usage statistics for %d plugins with tracked usage", len(self._plugin_stats))
            
            usage_stats = []
            for plugin_name, stats in self._plugin_stats.items():
                calls = stats['calls']
                avg_time = stats['total_time'] / calls if calls > 0 else 0.0
                error_rate = (stats['errors'] / calls * 100) if calls > 0 else 0.0
                
                usage_stats.append({
                    "name": plugin_name,
                    "calls": calls,
                    "errors": stats['errors'],
                    "total_time": stats['total_time'],
                    "avg_time": avg_time,
                    "error_rate": error_rate,
                    "last_call": stats['last_call']
                })
                
                logger.debug("Plugin '%s' usage: %d calls, %d errors, %.3fs avg, %.1f%% error rate", 
                           plugin_name, calls, stats['errors'], avg_time, error_rate)
            
            # Cache the calculated statistics
            self._cached_usage_stats = usage_stats
            logger.debug("Generated and cached usage statistics for %d plugins", len(usage_stats))
            return usage_stats
    
    def reset_plugin_usage_statistics(self, plugin_name: str | None = None) -> None:
        """Reset usage statistics for a specific plugin or all plugins.
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin to reset statistics for. If None, reset all plugins.
        """
        with self._stats_lock:
            if plugin_name:
                if plugin_name in self._plugin_stats:
                    logger.debug("Resetting usage statistics for plugin '%s'", plugin_name)
                    del self._plugin_stats[plugin_name]
                    logger.info("Usage statistics reset for plugin '%s'", plugin_name)
                else:
                    logger.debug("No usage statistics found for plugin '%s' to reset", plugin_name)
            else:
                logger.debug("Resetting usage statistics for all %d plugins", len(self._plugin_stats))
                self._plugin_stats.clear()
                logger.info("Usage statistics reset for all plugins")
            
            # Invalidate the cache since we've reset statistics
            self._cached_usage_stats = None
            logger.debug("Invalidated usage statistics cache after reset")
    
    def get_plugin_usage_stats(self, plugin_name: str) -> dict | None:
        """Get usage statistics for a specific plugin.
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin to get statistics for.
            
        Returns
        -------
        dict or None:
            Dictionary containing usage statistics, or None if plugin has no statistics.
        """
        with self._stats_lock:
            if plugin_name not in self._plugin_stats:
                return None
            
            stats = self._plugin_stats[plugin_name].copy()
            calls = stats['calls']
            if calls > 0:
                stats['avg_time'] = stats['total_time'] / calls
                stats['error_rate'] = (stats['errors'] / calls * 100)
            else:
                stats['avg_time'] = 0.0
                stats['error_rate'] = 0.0
            
            return stats
    
    def track_plugin_call(self, plugin_name: str, success: bool, execution_time: float | None = None) -> None:
        """Manually track a plugin call (for external integration).
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin being tracked
        success:
            Whether the call succeeded (True) or failed (False)
        execution_time:
            Optional execution time in seconds. If None, current timestamp is used.
        """
        logger.debug("Tracking plugin call: plugin='%s', success=%s, time=%.3fs", 
                   plugin_name, success, execution_time or 0.0)
        
        start_time = time.time() - (execution_time or 0.0)
        self._track_plugin_usage(plugin_name, success, start_time)
    
    def track_plugin_tool_call(self, plugin_name: str, tool_name: str, success: bool, execution_time: float | None = None) -> None:
        """Track a tool call made by a specific plugin.
        
        This method allows tracking when plugins contribute tools that are then
        executed by the agent. This helps associate tool usage with the plugins
        that provided them.
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin that contributed the tool
        tool_name:
            Name of the tool that was called
        success:
            Whether the tool call succeeded (True) or failed (False)
        execution_time:
            Optional execution time in seconds. If None, current timestamp is used.
        """
        logger.debug("Tracking tool call: plugin='%s', tool='%s', success=%s, time=%.3fs", 
                   plugin_name, tool_name, success, execution_time or 0.0)
        
        # For now, we'll track this as a regular plugin call
        # In a more sophisticated implementation, we could track tool-specific stats
        self.track_plugin_call(plugin_name, success, execution_time)
    
    def get_plugin_tool_usage(self, plugin_name: str) -> list[dict]:
        """Get tool usage statistics for a specific plugin.
        
        Note: This is a placeholder for future implementation where we could
        track which specific tools are used by each plugin.
        
        Parameters
        ----------
        plugin_name:
            Name of the plugin to get tool usage for.
            
        Returns
        -------
        list[dict]
            List of tool usage statistics (currently empty, placeholder for future).
        """
        # Future enhancement: track tool-specific usage per plugin
        return []
    
    def get_usage_statistics_summary(self) -> str:
        """Return a human-readable summary of plugin usage statistics in markdown format."""
        usage_stats = self.get_plugin_usage_statistics()
        if not usage_stats:
            logger.debug("No plugin usage statistics available for summary")
            return "No plugin usage statistics available."
        
        logger.debug("Generating usage statistics summary for %d plugins", len(usage_stats))
        
        lines = ["## Plugin Usage Statistics"]
        lines.append("")
        lines.append("| Plugin | Calls | Errors | Avg Time | Error Rate | Last Call |")
        lines.append("|--------|-------|--------|----------|------------|-----------|")
        
        for stat in sorted(usage_stats, key=lambda x: x['calls'], reverse=True):
            last_call_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat['last_call']))
            lines.append(f"| {stat['name']} | {stat['calls']} | {stat['errors']} | "
                       f"{stat['avg_time']:.3f}s | {stat['error_rate']:.1f}% | {last_call_time} |")
            logger.debug("Summary line: %s | Calls: %d | Errors: %d | Error Rate: %.1f%%", 
                       stat['name'], stat['calls'], stat['errors'], stat['error_rate'])
        
        logger.debug("Generated usage statistics summary")
        return "\n".join(lines)

    def _register_with_pluggy(self, instance: VibePlugin) -> None:
        """Register a plugin instance with pluggy for hook dispatch."""
        self._pluggy_pm.register(instance)

    async def call_tool_event_hooks(
        self, hook_name: str, context: PluginContext, **kwargs: object
    ) -> None:
        """Call tool event hooks using pluggy's hook mechanism.

        This method provides backward compatibility by falling back to direct
        plugin iteration if pluggy hook dispatch fails.
        """
        logger.debug("Calling tool event hook '%s' with %d plugins", hook_name, len(self._tool_event_plugins))
        
        try:
            # Call each plugin's hook individually to track usage properly
            for plugin in self._tool_event_plugins:
                plugin_name = plugin.metadata().name
                start_time = time.time()
                logger.debug("Executing hook '%s' for plugin '%s'", hook_name, plugin_name)
                
                try:
                    hook_method = getattr(plugin, hook_name, None)
                    if hook_method:
                        await hook_method(context=context, **kwargs)
                        self._track_plugin_usage(plugin_name, True, start_time)
                        logger.debug("Hook '%s' for plugin '%s' completed successfully", hook_name, plugin_name)
                    else:
                        # Plugin doesn't implement this hook, that's fine
                        logger.debug("Plugin '%s' does not implement hook '%s'", plugin_name, hook_name)
                        pass
                except Exception:
                    self._track_plugin_usage(plugin_name, False, start_time)
                    logger.warning("Hook '%s' for plugin '%s' failed", hook_name, plugin_name, exc_info=True)
                    # Continue with other plugins even if one fails
                    continue
        except Exception:
            # Fallback to pluggy dispatch if individual calling fails
            logger.warning("Individual plugin hook execution failed, falling back to pluggy dispatch", exc_info=True)
            try:
                getattr(self._pluggy_pm.hook, hook_name)(context=context, **kwargs)
                logger.debug("Pluggy dispatch for hook '%s' completed", hook_name)
            except Exception:
                logger.error("Pluggy dispatch for hook '%s' failed", hook_name, exc_info=True)
                pass

    def _invalidate_priority_cache(self) -> None:
        """Invalidate the priority cache when priorities are changed."""
        self._priority_manager.invalidate_cache()
    
    def invalidate_priority_cache(self) -> None:
        """Public method to invalidate the priority cache.
        
        Call this method when plugin priorities are changed externally
        to ensure the cache is refreshed.
        """
        self._invalidate_priority_cache()
    
    def invalidate_plugin_priority_cache(self, plugin_id: int) -> None:
        """Invalidate the priority cache for a specific plugin.
        
        Parameters
        ----------
        plugin_id:
            The id() of the plugin instance whose cache should be invalidated.
        """
        self._priority_manager.invalidate_plugin_cache(plugin_id)

    def update_capability_registry(self) -> None:
        """Update the capability registry by re-scanning all active plugins.
        
        This method should be called when plugins are dynamically added or removed
        to ensure the capability registry stays in sync.
        """
        self._capability_registry.update_from_plugin_manager()

    def _wrap_plugin_priority_methods(self, plugin: VibePlugin) -> None:
        """Wrap plugin priority methods to automatically invalidate cache."""
        original_set_runtime_priority = plugin.set_runtime_priority
        original_clear_runtime_priority = plugin.clear_runtime_priority
        
        def wrapped_set_runtime_priority(priority: int, context: PluginContext | None = None) -> None:
            original_set_runtime_priority(priority, context)
            # Invalidate cache for this specific plugin
            self.invalidate_plugin_priority_cache(id(plugin))
        
        def wrapped_clear_runtime_priority() -> None:
            original_clear_runtime_priority()
            # Invalidate cache for this specific plugin
            self.invalidate_plugin_priority_cache(id(plugin))
        
        # Replace the methods
        plugin.set_runtime_priority = wrapped_set_runtime_priority  # type: ignore
        plugin.clear_runtime_priority = wrapped_clear_runtime_priority  # type: ignore

    def _get_cached_priority(self, plugin_id: int) -> int | None:
        """Get cached priority for a plugin by its id."""
        result = self._priority_manager.get_priority(plugin_id)
        logger.debug("Cache hit for plugin_id %d, priority: %s", plugin_id, result)
        return result
    
    def _set_cached_priority(self, plugin_id: int, priority: int) -> None:
        """Cache the priority for a plugin."""
        self._priority_manager.set_priority(plugin_id, priority)
        logger.debug("Cached priority %d for plugin_id %d", priority, plugin_id)

    def load_plugins_from_entrypoints(self) -> None:
        """Load plugins using pluggy's entry point discovery mechanism."""
        try:
            self._pluggy_pm.load_setuptools_entrypoints("mistral-vibe-plugins")
        except Exception:
            logger.debug("No pluggy entry points found or validation failed")

    # ── Discovery ─────────────────────────────────────────────────────────────

    def _search_paths(self) -> list[Path]:
        """Return ordered list of directories to scan for plugin classes."""
        paths: list[Path] = []

        # 1. User-configured extra paths
        for p in getattr(self._config, "plugin_paths", []):
            paths.append(Path(p).expanduser().resolve())

        # 2. VIBE_HOME/plugins
        from vibe.core.paths._vibe_home import VIBE_HOME  # type: ignore[import]

        paths.append(VIBE_HOME.path / "plugins")

        # 3. Project-local .vibe/plugins
        paths.append(self._context.workdir / ".vibe" / "plugins")

        return [p for p in paths if p.is_dir()]

    def _discover_plugin_classes(self) -> list[type[VibePlugin]]:
        """Return all unique, non-abstract VibePlugin subclasses found."""
        found: dict[str, type[VibePlugin]] = {}  # name → class

        # Built-ins first (lowest priority — overridable by user paths)
        for cls in self._scan_package(_BUILTIN_PACKAGE):
            found[cls.metadata().name] = cls

        # Entry points (same priority as built-ins)
        for cls in self._discover_via_entry_points():
            if cls.metadata().name not in found:
                found[cls.metadata().name] = cls

        # File-system paths (higher priority — later paths win per name)
        for path in self._search_paths():
            for cls in self._scan_directory(path):
                found[cls.metadata().name] = cls

        return list(found.values())

    @staticmethod
    def _scan_package(package_name: str) -> list[type[VibePlugin]]:
        """Import all submodules of a package and collect plugin classes."""
        try:
            pkg = importlib.import_module(package_name)
        except ImportError:
            logger.debug("Built-in plugin package %s not found", package_name)
            return []

        pkg_path = Path(pkg.__file__).parent  # type: ignore[arg-type]
        classes: list[type[VibePlugin]] = []

        for py_file in sorted(pkg_path.rglob("plugin.py")):
            # Calculate module name from package structure
            # e.g. vibe/core/plugins/builtin/lsp/plugin.py → vibe.core.plugins.builtin.lsp.plugin
            rel = py_file.relative_to(pkg_path)
            mod_name = f"{package_name}.{'.'.join(rel.with_suffix('').parts)}"
            classes.extend(PluginManager._load_classes_from_module_name(mod_name))

        return classes

    @staticmethod
    def _scan_directory(directory: Path) -> list[type[VibePlugin]]:
        """Scan a filesystem directory for plugin.py files."""
        classes: list[type[VibePlugin]] = []
        for py_file in sorted(directory.rglob("plugin.py")):
            if py_file.name.startswith("_"):
                continue
            classes.extend(PluginManager._load_classes_from_path(py_file))
        return classes

    @staticmethod
    def _load_classes_from_module_name(
        module_name: str,
    ) -> list[type[VibePlugin]]:
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            logger.exception("Could not import module %s", module_name)
            return []
        return PluginManager._extract_plugin_classes(mod)

    @staticmethod
    def _load_classes_from_path(path: Path) -> list[type[VibePlugin]]:
        module_name = f"_vibe_plugin_{path.stem}_{abs(hash(str(path)))}"
        if module_name in sys.modules:
            mod = sys.modules[module_name]
        else:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return []
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            try:
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            except Exception:
                logger.exception("Could not load plugin from %s", path)
                del sys.modules[module_name]
                return []
        return PluginManager._extract_plugin_classes(mod)

    @staticmethod
    def _extract_plugin_classes(module: object) -> list[type[VibePlugin]]:
        classes = []
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, VibePlugin)
                and obj is not VibePlugin
                and obj is not ToolEventPlugin
                and not inspect.isabstract(obj)
                and obj.__module__ == getattr(module, "__name__", "")
            ):
                classes.append(obj)
        return classes

    def _discover_via_entry_points(self) -> list[type[VibePlugin]]:
        """Discover plugins via setuptools entry points from the 'vibe.plugins' group."""
        classes: list[type[VibePlugin]] = []
        loaded: set[str] = set()

        try:
            eps = importlib.metadata.entry_points()
        except Exception:
            logger.debug("No entry points available")
            return classes
        group_eps = getattr(eps, "get", lambda k, d: [])("vibe.plugins", [])
        for ep in group_eps:
            if ep.name in loaded:
                continue
            try:
                plugin_cls = ep.load()
            except Exception:
                logger.exception("Failed to load plugin from entry point %s", ep.name)
                continue
            if not issubclass(plugin_cls, VibePlugin) or inspect.isabstract(plugin_cls):
                logger.debug("Entry point %s does not define a concrete VibePlugin", ep.name)
                continue
            loaded.add(ep.name)
            classes.append(plugin_cls)
            logger.debug("Discovered plugin %s via entry point", ep.name)

        logger.info("Entry point discovery: loaded %d plugins", len(classes))
        return classes

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _is_enabled(self, name: str) -> bool:
        enabled: list[str] | None = getattr(self._config, "enabled_plugins", None)
        disabled: list[str] = getattr(self._config, "disabled_plugins", [])

        # If whitelist is set (not None), name must match at least one pattern
        if enabled is not None and not any(_matches(name, pat) for pat in enabled):
            return False
        # If blacklist matches, disable
        if any(_matches(name, pat) for pat in disabled):
            return False
        return True


# ── Pattern matching (same semantics as Vibe's tool filtering) ─────────────


def _matches(name: str, pattern: str) -> bool:
    """Return True if *name* matches *pattern* (exact / glob / regex)."""
    if pattern.startswith("re:"):
        return bool(re.fullmatch(pattern[3:], name, re.IGNORECASE))
    # Heuristic: treat as regex if it contains regex metacharacters beyond */?
    if any(c in pattern for c in r"()[]{}+^$|\\"):
        try:
            return bool(re.fullmatch(pattern, name, re.IGNORECASE))
        except re.error:
            pass
    # Glob
    return fnmatch.fnmatch(name.lower(), pattern.lower())
