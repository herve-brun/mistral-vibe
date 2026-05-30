"""Tests for the CapabilityRegistry class."""

from vibe.core.plugins.registry import CapabilityRegistry
from vibe.core.plugins.base import VibePlugin, PluginMetadata


class TestPlugin(VibePlugin):
    """Test plugin for capability registry testing."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin for capability registry",
            capabilities=["file-system", "network-access"],
            required_capabilities=["basic-auth"]
        )
    
    async def setup(self, context):
        pass
    
    async def teardown(self):
        pass


class AnotherTestPlugin(VibePlugin):
    """Another test plugin for capability registry testing."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="another-plugin",
            version="1.0.0",
            description="Another test plugin",
            capabilities=["database-access", "file-system"],
            required_capabilities=[]
        )
    
    async def setup(self, context):
        pass
    
    async def teardown(self):
        pass


def test_capability_registry_basic():
    """Test basic capability registry functionality."""
    registry = CapabilityRegistry()
    
    # Test initial state
    assert len(registry) == 0
    assert not registry.has_capability("file-system")
    assert registry.get_all_capabilities() == set()
    
    # Test registering capabilities
    registry.register_capability("file-system", "test-provider")
    assert registry.has_capability("file-system")
    assert "file-system" in registry
    assert len(registry) == 1
    
    # Test getting providers
    providers = registry.get_capability_providers("file-system")
    assert providers == {"test-provider"}
    
    # Test registering plugin capabilities
    plugin = TestPlugin()
    registry.register_plugin_capabilities(plugin)
    
    assert registry.has_capability("file-system")
    assert registry.has_capability("network-access")
    assert len(registry) == 2
    
    # Test plugin capabilities
    plugin_caps = registry.get_plugin_capabilities("test-plugin")
    assert plugin_caps == {"file-system", "network-access"}
    
    # Test required capabilities
    required_caps = registry.get_required_capabilities("test-plugin")
    assert required_caps == {"basic-auth"}
    
    # Test capability validation
    has_requirements, missing = registry.validate_capability_requirements("test-plugin")
    assert not has_requirements  # basic-auth is missing
    assert missing == {"basic-auth"}
    
    # Register the missing capability
    registry.register_capability("basic-auth", "auth-provider")
    has_requirements, missing = registry.validate_capability_requirements("test-plugin")
    assert has_requirements  # Now all requirements are satisfied
    assert missing == set()


def test_capability_registry_with_multiple_plugins():
    """Test capability registry with multiple plugins."""
    registry = CapabilityRegistry()
    
    plugin1 = TestPlugin()
    plugin2 = AnotherTestPlugin()
    
    registry.register_plugin_capabilities(plugin1)
    registry.register_plugin_capabilities(plugin2)
    
    # Test that both plugins' capabilities are registered
    assert registry.has_capability("file-system")
    assert registry.has_capability("network-access")
    assert registry.has_capability("database-access")
    
    # Test that file-system has multiple providers
    providers = registry.get_capability_providers("file-system")
    assert providers == {"test-plugin", "another-plugin"}
    
    # Test finding plugins with specific capabilities
    file_system_plugins = registry.find_plugins_with_capability("file-system")
    assert file_system_plugins == {"test-plugin", "another-plugin"}
    
    network_plugins = registry.find_plugins_with_capability("network-access")
    assert network_plugins == {"test-plugin"}


def test_capability_registry_thread_safety():
    """Test that capability registry operations are thread-safe."""
    import threading
    
    registry = CapabilityRegistry()
    
    def register_capabilities(thread_id):
        for i in range(100):
            capability = f"capability-{thread_id}-{i}"
            provider = f"provider-{thread_id}-{i}"
            registry.register_capability(capability, provider)
    
    # Create multiple threads to register capabilities concurrently
    threads = []
    for thread_id in range(10):
        thread = threading.Thread(target=register_capabilities, args=(thread_id,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify that all capabilities were registered (10 threads * 100 capabilities each)
    assert len(registry) == 1000
    
    # Verify that we can still access capabilities
    assert registry.has_capability("capability-5-50")
    assert registry.has_capability("capability-9-99")


def test_capability_registry_summary():
    """Test the capability registry summary method."""
    registry = CapabilityRegistry()
    
    plugin1 = TestPlugin()
    plugin2 = AnotherTestPlugin()
    
    registry.register_plugin_capabilities(plugin1)
    registry.register_plugin_capabilities(plugin2)
    
    summary = registry.get_capability_summary()
    
    assert summary["total_capabilities"] == 3  # file-system, network-access, database-access
    assert summary["total_providers"] == 2  # test-plugin, another-plugin
    
    # Check capabilities by provider
    assert "test-plugin" in summary["capabilities_by_provider"]
    assert "another-plugin" in summary["capabilities_by_provider"]
    
    # Check providers by capability
    assert "file-system" in summary["providers_by_capability"]
    assert "network-access" in summary["providers_by_capability"]
    assert "database-access" in summary["providers_by_capability"]
    
    # Check unsatisfied requirements
    assert "test-plugin" in summary["unsatisfied_requirements"]
    assert summary["unsatisfied_requirements"]["test-plugin"] == ["basic-auth"]


def test_capability_registry_clear():
    """Test clearing the capability registry."""
    registry = CapabilityRegistry()
    
    # Add some capabilities
    registry.register_capability("cap1", "provider1")
    registry.register_capability("cap2", "provider2")
    
    assert len(registry) == 2
    
    # Clear the registry
    registry.clear()
    
    assert len(registry) == 0
    assert not registry.has_capability("cap1")
    assert not registry.has_capability("cap2")


def test_capability_registry_contains_operator():
    """Test the 'in' operator support."""
    registry = CapabilityRegistry()
    
    registry.register_capability("test-capability", "test-provider")
    
    assert "test-capability" in registry
    assert "non-existent-capability" not in registry