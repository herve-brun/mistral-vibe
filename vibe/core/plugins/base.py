"""vibe/core/plugins/base.py

─────────────────────────────────────────────────────────────────────────────
Base interfaces for the Vibe plugin system.

A plugin is a Python package (or single module) that hooks into Vibe's
execution pipeline.  Two hook families are provided:

  • VibePLugin        — lifecycle hooks (startup / shutdown / config)
  • ToolEventPlugin   — reacts to tool calls and their results

Plugins are discovered by PluginManager and activated through
PluginMiddleware, which is inserted into AgentLoop's MiddlewarePipeline.

Usage in a plugin module::

    from vibe.core.plugins.base import ToolEventPlugin, PluginMetadata

    class MyPlugin(ToolEventPlugin):
        @classmethod
        def metadata(cls) -> PluginMetadata:
            return PluginMetadata(name="my-plugin", version="0.1.0",
                                  description="Does something useful")

        async def on_tool_call(self, tool_name: str, arguments: dict,
                               context: "PluginContext") -> None:
            ...  # react before execution

        async def on_tool_result(self, tool_name: str, arguments: dict,
                                 result: str,
                                 context: "PluginContext") -> None:
            ...  # react after execution
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from vibe.core.config import VibeConfig

# Hook implementation marker for pluggy
hookimpl = pluggy.HookimplMarker("mistral-vibe")


# ──────────────────────────────────────────────────────────────────────────────
# Priority Groups
# ──────────────────────────────────────────────────────────────────────────────

class PriorityGroup(IntEnum):
    """Priority groups for dynamic plugin ordering.

    Lower values run first. These groups provide semantic meaning to priority ranges.
    """
    CRITICAL = 25      # 0-49: Critical system plugins
    HIGH = 75          # 50-99: High-priority middleware  
    DEFAULT = 100      # 90-110: Default range for most plugins
    LOW = 175          # 150-199: Lower priority
    DELAYED = 250      # 200+: Delayed execution


# ──────────────────────────────────────────────────────────────────────────────
# Metadata
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PluginMetadata:
    """Static description of a plugin, used for discovery and display.

    Attributes
    ----------
    priority:
        Execution order hint for plugins in the middleware pipeline.
        Lower values run first. Defaults to 100.

        - 0-49:   Critical system plugins (run first)
        - 50-99:  High-priority middleware
        - 90-110: Default range for most plugins
        - 150-199: Lower priority (run later)
        - 200+:   Delayed execution (run last)
    tags:
        Capability tags for filtering and discovery (e.g., ["code-lint",
        "telemetry"]). Empty by default.
    capabilities:
        List of capabilities provided by this plugin (e.g., ["file-system",
        "network-access"]). Empty by default.
    required_capabilities:
        List of capabilities required by this plugin to function properly.
        Empty by default.
    runtime_requirements:
        Dictionary of runtime requirements (e.g., {"python": ">=3.12"}).
        Empty by default.
    """

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    provides_tools: list[str] = field(default_factory=list)
    priority: int = field(default=100)
    priority_group: PriorityGroup | None = field(default=None)
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    runtime_requirements: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate priority ranges and capability names after initialization."""
        self._validate_priority()
        self._validate_capability_names()

    def _validate_priority(self) -> None:
        """Validate that priority is within allowed ranges."""
        # Get priority group ranges
        priority_group_ranges = {
            PriorityGroup.CRITICAL: (0, 49),
            PriorityGroup.HIGH: (50, 99),
            PriorityGroup.DEFAULT: (90, 110),
            PriorityGroup.LOW: (150, 199),
            PriorityGroup.DELAYED: (200, float('inf')),
        }

        # Check if priority_group is set and validate against its range
        if self.priority_group is not None:
            min_priority, max_priority = priority_group_ranges[self.priority_group]
            if max_priority == float('inf'):
                # Special case for DELAYED group - only check minimum
                if self.priority < min_priority:
                    raise ValueError(
                        f"Priority {self.priority} is below the minimum valid value "
                        f"{min_priority} for priority group {self.priority_group.name}"
                    )
            else:
                # Check both min and max for other groups
                if not (min_priority <= self.priority <= max_priority):
                    raise ValueError(
                        f"Priority {self.priority} is not within the valid range "
                        f"{min_priority}-{max_priority} for priority group {self.priority_group.name}"
                    )

        # Validate against global min/max from configuration
        # These are soft limits that can be overridden but provide guidance
        plugin_min_priority = 0  # Allow 0 for critical system plugins
        plugin_max_priority = 1000  # Allow higher values for special cases
         
        if self.priority < plugin_min_priority:
            raise ValueError(
                f"Priority {self.priority} is below the minimum allowed value of "
                f"{plugin_min_priority}. Consider using a higher priority value."
            )
         
        if self.priority > plugin_max_priority:
            raise ValueError(
                f"Priority {self.priority} is above the maximum allowed value of "
                f"{plugin_max_priority}. Consider using a lower priority value."
            )

    def _validate_capability_names(self) -> None:
        """Validate that capability names follow the kebab-case naming convention.
        
        Allowed characters: lowercase letters, numbers, hyphens, and underscores.
        """
        # Define the regex pattern for valid capability names
        # kebab-case: lowercase letters, numbers, hyphens, and underscores
        capability_pattern = re.compile(r'^[a-z0-9_-]+$')
        
        # Validate capabilities
        for capability in self.capabilities:
            if not capability_pattern.match(capability):
                raise ValueError(
                    f"Invalid capability name '{capability}'. "
                    f"Capability names must use kebab-case: lowercase letters, numbers, "
                    f"hyphens, and underscores only."
                )
        
        # Validate required_capabilities
        for capability in self.required_capabilities:
            if not capability_pattern.match(capability):
                raise ValueError(
                    f"Invalid required capability name '{capability}'. "
                    f"Capability names must use kebab-case: lowercase letters, numbers, "
                    f"hyphens, and underscores only."
                )


# ──────────────────────────────────────────────────────────────────────────────
# Context passed to hook methods
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PluginContext:
    """Snapshot of the current Vibe state made available to plugin hooks.

    Attributes
    ----------
    workdir:
        Absolute path to the current project root (same as
        ``config.effective_workdir``).
    config:
        The live ``VibeConfig`` instance.
    tool_manager:
        Optional reference to Vibe's ToolManager for dynamic tool registration.
    extra:
        Free-form dict that plugins may use to share state across hooks
        within a single agent turn.
    """

    workdir: Path
    config: VibeConfig
    tool_manager: Any | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Base plugin interface
# ──────────────────────────────────────────────────────────────────────────────


class VibePlugin(abc.ABC):
    """Minimal lifecycle interface that all plugins must implement.

    Plugins are instantiated once by :class:`PluginManager` and kept alive
    for the duration of the Vibe session.
    """

    def __init__(self) -> None:
        self._runtime_priority: int | None = None

    @classmethod
    @abc.abstractmethod
    def metadata(cls) -> PluginMetadata:
        """Return static metadata for this plugin."""

    @abc.abstractmethod
    async def setup(self, context: PluginContext) -> None:
        """Called once after the plugin is instantiated and the config is ready.

        Use this to start background processes, connect to servers, or
        pre-compute any state that should persist across turns.
        """

    @abc.abstractmethod
    async def teardown(self) -> None:
        """Called when Vibe is shutting down.

        Release all resources acquired in :meth:`setup`.
        """

    def is_applicable(self, context: PluginContext) -> bool:
        """Return True if this plugin should be active for the given context.

        The default implementation always returns True.  Override to enable
        context-aware activation (e.g., only when certain file types are
        present in the workdir).
        """
        return True

    def set_runtime_priority(self, priority: int, context: PluginContext | None = None) -> None:
        """Set a runtime priority override for this plugin.

        This allows dynamic adjustment of plugin execution order based on
        context, user preferences, or other runtime conditions.

        Parameters
        ----------
        priority:
            The new priority value. Lower values run first.
        context:
            Optional plugin context providing access to configuration.
            If not provided, bounds checking will be skipped.

        Raises
        ------
        ValueError
            If priority is outside the configured bounds and context is provided.
        """
        old_priority = self._runtime_priority if self._runtime_priority is not None else self.metadata().priority
        
        self._validate_runtime_priority(priority, context)
        self._runtime_priority = priority

    def _validate_runtime_priority(self, priority: int, context: PluginContext | None = None) -> None:
        """Validate runtime priority against allowed ranges."""
        # Get priority group ranges from static metadata
        metadata = self.metadata()
        priority_group_ranges = {
            PriorityGroup.CRITICAL: (0, 49),
            PriorityGroup.HIGH: (50, 99),
            PriorityGroup.DEFAULT: (90, 110),
            PriorityGroup.LOW: (150, 199),
            PriorityGroup.DELAYED: (200, float('inf')),
        }

        # Validate against global min/max from configuration first (if context is available)
        if context is not None:
            config = context.config
            min_priority = config.plugin_min_priority
            max_priority = config.plugin_max_priority

            if priority < min_priority or priority > max_priority:
                raise ValueError(
                    f"Runtime priority {priority} is out of bounds. "
                    f"Must be between {min_priority} and {max_priority} (inclusive)."
                )

        # If priority_group is set in metadata, validate against its range
        if metadata.priority_group is not None:
            min_priority, max_priority = priority_group_ranges[metadata.priority_group]
            if max_priority == float('inf'):
                # Special case for DELAYED group - only check minimum
                if priority < min_priority:
                    raise ValueError(
                        f"Runtime priority {priority} is below the minimum valid value "
                        f"{min_priority} for priority group {metadata.priority_group.name}"
                    )
            else:
                # Check both min and max for other groups
                if not (min_priority <= priority <= max_priority):
                    raise ValueError(
                        f"Runtime priority {priority} is not within the valid range "
                        f"{min_priority}-{max_priority} for priority group {metadata.priority_group.name}"
                    )

    def clear_runtime_priority(self) -> None:
        """Clear any runtime priority override, reverting to the static priority."""
        self._runtime_priority = None

    def effective_priority(self) -> int:
        """Return the effective priority (runtime override or static priority)."""
        if self._runtime_priority is not None:
            return self._runtime_priority
        return self.metadata().priority


# ──────────────────────────────────────────────────────────────────────────────
# Tool-event plugin
# ──────────────────────────────────────────────────────────────────────────────


class ToolEventPlugin(VibePlugin, abc.ABC):
    """Plugin that reacts to tool call / result events emitted by AgentLoop.

    The two hook methods are called **synchronously within the agent turn**
    by :class:`~vibe.core.plugins.middleware.PluginMiddleware`.  They must
    be non-blocking or use asyncio properly.

    Both methods receive the same ``context`` object so plugins can share
    transient per-turn state via ``context.extra``.
    """

    # File-access tools whose ``path`` / ``file_path`` argument tells us
    # which file the agent is looking at.  Subclasses may extend this set.
    FILE_ACCESS_TOOLS: frozenset[str] = frozenset({
        "read_file",
        "write_file",
        "search_replace",
        "grep",
        "ls",
    })

    @hookimpl
    async def on_tool_call(
        self, tool_name: str, arguments: dict[str, Any], context: PluginContext
    ) -> None:
        """Called just *before* a tool is executed.

        Parameters
        ----------
        tool_name:
            The canonical name of the tool (e.g. ``"read_file"``).
        arguments:
            Raw arguments dict as sent by the LLM.
        context:
            Current plugin context.
        """

    @hookimpl
    async def on_tool_result(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        context: PluginContext,
    ) -> None:
        """Called just *after* a tool has executed and produced a result.

        Parameters
        ----------
        tool_name:
            The canonical name of the tool.
        arguments:
            Raw arguments dict that was used for the call.
        result:
            The string result returned by the tool.
        context:
            Current plugin context.
        """

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def extract_file_path(tool_name: str, arguments: dict[str, Any]) -> Path | None:
        """Try to extract a file path from tool arguments.

        Returns None when the tool is not file-related or when the argument
        is missing / not a string.
        """
        for key in ("path", "file_path", "filename", "filepath"):
            value = arguments.get(key)
            if isinstance(value, str) and value:
                return Path(value)
        return None
