"""Integration tests for CapabilityRegistry with PluginManager."""

import pytest
from pathlib import Path

from vibe.core.plugins.manager import PluginManager
from vibe.core.plugins.base import PluginContext, VibePlugin, PluginMetadata
from vibe.core.plugins.registry import CapabilityRegistry
from vibe.core.config import VibeConfig


class TestCapabilityPlugin(VibePlugin):
    """Test plugin with capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="test-capability-plugin",
            version="1.0.0",
            description="Test plugin with capabilities",
            capabilities=["file-system", "network-access"],
            required_capabilities=["basic-auth"]
        )
    
    async def setup(self, context):
        pass
    
    async def teardown(self):
        pass


class AnotherTestCapabilityPlugin(VibePlugin):
    """Another test plugin with capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="another-capability-plugin",
            version="1.0.0",
            description="Another test plugin with capabilities",
            capabilities=["database-access", "file-system"],
            required_capabilities=[]
        )
    
    async def setup(self, context):
        pass
    
    async def teardown(self):
        pass


class BasicAuthPlugin(VibePlugin):
    """Plugin that provides basic-auth capability."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="basic-auth-plugin",
            version="1.0.0",
            description="Provides basic authentication capability",
            capabilities=["basic-auth"],
            required_capabilities=[]
        )
    
    async def setup(self, context):
        pass
    
    async def teardown(self):
        pass


def test_plugin_manager_capability_registry_integration():
    """Test that PluginManager integrates properly with CapabilityRegistry."""
    # Create real config and context
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    # Create plugin manager
    plugin_manager = PluginManager(config, context)
    
    # Verify capability registry is accessible
    assert hasattr(plugin_manager, 'capability_registry')
    assert isinstance(plugin_manager.capability_registry, CapabilityRegistry)
    
    # Initially, no capabilities should be registered
    assert len(plugin_manager.capability_registry) == 0


def test_capability_registry_auto_registration():
    """Test that capabilities are automatically registered when plugins are loaded."""
    # Create real config and context
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    # Create plugin manager
    plugin_manager = PluginManager(config, context)
    
    # Manually add some plugins (simulating discovery)
    plugin1 = TestCapabilityPlugin()
    plugin2 = AnotherTestCapabilityPlugin()
    
    # Register plugins with the manager
    plugin_manager._plugins = [plugin1, plugin2]
    plugin_manager.capability_registry.update_from_plugin_manager()
    
    # Verify capabilities are registered
    assert plugin_manager.capability_registry.has_capability("file-system")
    assert plugin_manager.capability_registry.has_capability("network-access")
    assert plugin_manager.capability_registry.has_capability("database-access")
    
    # Verify plugin capabilities
    caps1 = plugin_manager.capability_registry.get_plugin_capabilities("test-capability-plugin")
    assert caps1 == {"file-system", "network-access"}
    
    caps2 = plugin_manager.capability_registry.get_plugin_capabilities("another-capability-plugin")
    assert caps2 == {"database-access", "file-system"}
    
    # Verify capability providers
    providers = plugin_manager.capability_registry.get_capability_providers("file-system")
    assert providers == {"test-capability-plugin", "another-capability-plugin"}


def test_capability_requirements_validation():
    """Test capability requirements validation."""
    # Create real config and context
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    # Create plugin manager
    plugin_manager = PluginManager(config, context)
    
    # Add plugin with requirements
    plugin = TestCapabilityPlugin()
    plugin_manager._plugins = [plugin]
    plugin_manager.capability_registry.update_from_plugin_manager()
    
    # Initially, requirements should not be satisfied (basic-auth is missing)
    has_reqs, missing = plugin_manager.capability_registry.validate_capability_requirements("test-capability-plugin")
    assert not has_reqs
    assert missing == {"basic-auth"}
    
    # Add the missing capability
    auth_plugin = BasicAuthPlugin()
    plugin_manager._plugins.append(auth_plugin)
    plugin_manager.capability_registry.update_from_plugin_manager()
    
    # Now requirements should be satisfied
    has_reqs, missing = plugin_manager.capability_registry.validate_capability_requirements("test-capability-plugin")
    assert has_reqs
    assert missing == set()


def test_capability_registry_clear_on_teardown():
    """Test that capability registry is cleared when plugins are torn down."""
    # Create real config and context
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    # Create plugin manager
    plugin_manager = PluginManager(config, context)
    
    # Add some plugins
    plugin1 = TestCapabilityPlugin()
    plugin2 = AnotherTestCapabilityPlugin()
    plugin_manager._plugins = [plugin1, plugin2]
    plugin_manager.capability_registry.update_from_plugin_manager()
    
    # Verify capabilities are registered
    assert len(plugin_manager.capability_registry) > 0
    
    # Simulate teardown
    plugin_manager._plugins = []
    plugin_manager.capability_registry.clear()
    
    # Verify registry is cleared
    assert len(plugin_manager.capability_registry) == 0