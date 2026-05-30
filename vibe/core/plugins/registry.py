"""vibe/core/plugins/registry.py

─────────────────────────────────────────────────────────────────────────────
CapabilityRegistry — tracks and manages plugin capabilities for runtime checks.

The CapabilityRegistry provides a centralized way to register, discover, and
validate plugin capabilities. It enables dynamic capability-based filtering and
runtime capability checks.

Key Features:
  • Thread-safe capability registration and lookup
  • Integration with PluginManager for automatic capability discovery
  • Runtime capability validation and filtering
  • Support for capability requirements and conflicts
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vibe.core.plugins.base import VibePlugin
    from vibe.core.plugins.manager import PluginManager


class CapabilityRegistry:
    """Registry for tracking and managing plugin capabilities.
    
    This class provides thread-safe operations for registering, querying,
    and validating plugin capabilities. It integrates with PluginManager
    to automatically discover and register capabilities from active plugins.
    """
    
    def __init__(self, plugin_manager: PluginManager | None = None) -> None:
        """Initialize the capability registry.
        
        Parameters
        ----------
        plugin_manager:
            Optional PluginManager instance for automatic capability discovery.
            If provided, capabilities will be automatically registered from
            active plugins.
        """
        self._capabilities: set[str] = set()
        self._capability_providers: dict[str, set[str]] = defaultdict(set)
        self._plugin_capabilities: dict[str, set[str]] = defaultdict(set)
        self._required_capabilities: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._plugin_manager = plugin_manager
        
        # Automatically register capabilities from plugin manager if provided
        if plugin_manager is not None:
            self._register_from_plugin_manager()
    
    def _register_from_plugin_manager(self) -> None:
        """Register capabilities from all active plugins in the PluginManager."""
        if self._plugin_manager is None:
            return
            
        with self._lock:
            for plugin in self._plugin_manager.all_plugins:
                self._register_plugin_capabilities(plugin)
    
    def _register_plugin_capabilities(self, plugin: VibePlugin) -> None:
        """Register capabilities from a single plugin."""
        metadata = plugin.metadata()
        plugin_name = metadata.name
        
        # Register provided capabilities
        for capability in metadata.capabilities:
            self._capabilities.add(capability)
            self._capability_providers[capability].add(plugin_name)
            self._plugin_capabilities[plugin_name].add(capability)
        
        # Register required capabilities
        for capability in metadata.required_capabilities:
            self._required_capabilities[plugin_name].add(capability)
    
    def register_capability(self, capability: str, provider: str | None = None) -> None:
        """Register a capability with an optional provider.
        
        Parameters
        ----------
        capability:
            The capability to register (e.g., "file-system", "network-access").
        provider:
            Optional name of the provider (plugin) that offers this capability.
            If None, the capability is registered without a specific provider.
        """
        with self._lock:
            self._capabilities.add(capability)
            if provider is not None:
                self._capability_providers[capability].add(provider)
    
    def register_plugin_capabilities(self, plugin: VibePlugin) -> None:
        """Register all capabilities from a plugin.
        
        Parameters
        ----------
        plugin:
            The plugin instance whose capabilities should be registered.
        """
        with self._lock:
            self._register_plugin_capabilities(plugin)
    
    def has_capability(self, capability: str) -> bool:
        """Check if a capability is available in the registry.
        
        Parameters
        ----------
        capability:
            The capability to check.
            
        Returns
        -------
        bool:
            True if the capability is registered, False otherwise.
        """
        with self._lock:
            return capability in self._capabilities
    
    def get_capability_providers(self, capability: str) -> set[str]:
        """Get all providers that offer a specific capability.
        
        Parameters
        ----------
        capability:
            The capability to query.
            
        Returns
        -------
        set[str]:
            Set of plugin names that provide the specified capability.
            Returns an empty set if the capability is not available.
        """
        with self._lock:
            return set(self._capability_providers.get(capability, set()))
    
    def get_plugin_capabilities(self, plugin_name: str) -> set[str]:
        """Get all capabilities provided by a specific plugin.
        
        Parameters
        ----------
        plugin_name:
            The name of the plugin to query.
            
        Returns
        -------
        set[str]:
            Set of capabilities provided by the plugin.
            Returns an empty set if the plugin is not registered.
        """
        with self._lock:
            return set(self._plugin_capabilities.get(plugin_name, set()))
    
    def get_required_capabilities(self, plugin_name: str) -> set[str]:
        """Get all capabilities required by a specific plugin.
        
        Parameters
        ----------
        plugin_name:
            The name of the plugin to query.
            
        Returns
        -------
        set[str]:
            Set of capabilities required by the plugin.
            Returns an empty set if the plugin has no requirements.
        """
        with self._lock:
            return set(self._required_capabilities.get(plugin_name, set()))
    
    def get_all_capabilities(self) -> set[str]:
        """Get all registered capabilities.
        
        Returns
        -------
        set[str]:
            Set of all capabilities currently registered.
        """
        with self._lock:
            return set(self._capabilities)
    
    def get_all_providers(self) -> dict[str, set[str]]:
        """Get a mapping of all capabilities to their providers.
        
        Returns
        -------
        dict[str, set[str]]:
            Dictionary mapping capability names to sets of provider names.
        """
        with self._lock:
            return {cap: set(providers) for cap, providers in self._capability_providers.items()}
    
    def can_satisfy_requirements(self, plugin_name: str) -> bool:
        """Check if all required capabilities for a plugin are available.
        
        Parameters
        ----------
        plugin_name:
            The name of the plugin to check.
            
        Returns
        -------
        bool:
            True if all required capabilities are available, False otherwise.
        """
        with self._lock:
            required = self._required_capabilities.get(plugin_name, set())
            if not required:
                return True  # No requirements means satisfied
            
            available = self._capabilities
            return required.issubset(available)
    
    def find_plugins_with_capability(self, capability: str) -> set[str]:
        """Find all plugins that provide a specific capability.
        
        Parameters
        ----------
        capability:
            The capability to search for.
            
        Returns
        -------
        set[str]:
            Set of plugin names that provide the specified capability.
        """
        with self._lock:
            return self.get_capability_providers(capability)
    
    def find_plugins_missing_requirements(self) -> set[str]:
        """Find all plugins that have unsatisfied capability requirements.
        
        Returns
        -------
        set[str]:
            Set of plugin names that have unsatisfied requirements.
        """
        with self._lock:
            unsatisfied = set()
            for plugin_name, required in self._required_capabilities.items():
                if required and not required.issubset(self._capabilities):
                    unsatisfied.add(plugin_name)
            return unsatisfied
    
    def clear(self) -> None:
        """Clear all registered capabilities and providers."""
        with self._lock:
            self._capabilities.clear()
            self._capability_providers.clear()
            self._plugin_capabilities.clear()
            self._required_capabilities.clear()
    
    def update_from_plugin_manager(self) -> None:
        """Update the registry by re-scanning the PluginManager's active plugins.
        
        This method clears the current registry and re-registers capabilities
        from all currently active plugins.
        """
        with self._lock:
            self.clear()
            if self._plugin_manager is not None:
                self._register_from_plugin_manager()
    
    def get_capability_summary(self) -> dict[str, Any]:
        """Get a summary of the current capability registry state.
        
        Returns
        -------
        dict[str, Any]:
            Dictionary containing:
            - total_capabilities: int
            - total_providers: int
            - capabilities_by_provider: dict[str, list[str]]
            - providers_by_capability: dict[str, list[str]]
            - unsatisfied_requirements: dict[str, list[str]]
        """
        with self._lock:
            summary = {
                "total_capabilities": len(self._capabilities),
                "total_providers": len(self._plugin_capabilities),
                "capabilities_by_provider": {},
                "providers_by_capability": {},
                "unsatisfied_requirements": {}
            }
            
            # Capabilities by provider
            for plugin_name, capabilities in self._plugin_capabilities.items():
                summary["capabilities_by_provider"][plugin_name] = sorted(capabilities)
            
            # Providers by capability
            for capability, providers in self._capability_providers.items():
                summary["providers_by_capability"][capability] = sorted(providers)
            
            # Unsatisfied requirements
            for plugin_name, required in self._required_capabilities.items():
                missing = required - self._capabilities
                if missing:
                    summary["unsatisfied_requirements"][plugin_name] = sorted(missing)
            
            return summary
    
    def validate_capability_requirements(self, plugin_name: str) -> tuple[bool, set[str]]:
        """Validate that a plugin's capability requirements are satisfied.
        
        Parameters
        ----------
        plugin_name:
            The name of the plugin to validate.
            
        Returns
        -------
        tuple[bool, set[str]]:
            Tuple containing:
            - bool: True if all requirements are satisfied, False otherwise
            - set[str]: Set of missing capabilities (empty if all requirements are satisfied)
        """
        with self._lock:
            required = self._required_capabilities.get(plugin_name, set())
            if not required:
                return True, set()
            
            missing = required - self._capabilities
            return len(missing) == 0, missing
    
    def __contains__(self, capability: str) -> bool:
        """Check if a capability is registered (supports 'in' operator)."""
        return self.has_capability(capability)
    
    def __len__(self) -> int:
        """Get the number of registered capabilities."""
        with self._lock:
            return len(self._capabilities)