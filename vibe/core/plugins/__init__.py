"""vibe/core/plugins/__init__.py

─────────────────────────────────────────────────────────────────────────────
Public re-exports for the Vibe plugin system.
"""
from __future__ import annotations

from vibe.core.plugins.base import (
    PluginContext,
    PluginMetadata,
    ToolEventPlugin,
    VibePlugin,
)
from vibe.core.plugins.context_aware import ContextAwarePlugin
from vibe.core.plugins.manager import PluginManager
from vibe.core.plugins.middleware import PluginMiddleware
from vibe.core.plugins.registry import CapabilityRegistry

__all__ = [
    "CapabilityRegistry",
    "ContextAwarePlugin",
    "PluginContext",
    "PluginManager",
    "PluginMetadata",
    "PluginMiddleware",
    "ToolEventPlugin",
    "VibePlugin",
]
