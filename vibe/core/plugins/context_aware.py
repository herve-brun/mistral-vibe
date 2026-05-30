"""vibe/core/plugins/context_aware.py

─────────────────────────────────────────────────────────────────────────────
ContextAwarePlugin — mixin for plugins that support dynamic priority adjustment

This module provides the ContextAwarePlugin abstract base class that enables
plugins to adjust their execution priority based on runtime context.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe.core.plugins.base import PluginContext


class ContextAwarePlugin(abc.ABC):
    """Mixin interface for plugins that support context-aware priority adjustment.
    
    Plugins that implement this interface can dynamically adjust their priority
    based on the current execution context, enabling more intelligent ordering
    of plugin execution.
    """

    @abc.abstractmethod
    def context_aware_priority(self, context: PluginContext) -> int:
        """Calculate the effective priority for this plugin given the current context.
        
        This method is called by PluginManager when dynamic priorities are enabled
        and allows plugins to adjust their execution order based on runtime conditions
        such as the current working directory, configuration settings, or other context
        information.
        
        Parameters
        ----------
        context:
            The current PluginContext containing workdir, config, and other state.
            
        Returns
        -------
            int
            The adjusted priority value. Lower values run first.
            
        Notes
        -----
        - The returned priority should be in the same range as static priorities (0-200+)
        - If an exception occurs during calculation, the plugin's base priority will be used
        - Results are cached to avoid repeated computations for the same context
        """
        pass