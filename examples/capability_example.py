"""Example demonstrating the CapabilityRegistry usage."""

from vibe.core.plugins.registry import CapabilityRegistry
from vibe.core.plugins.base import VibePlugin, PluginMetadata


class FileSystemPlugin(VibePlugin):
    """Example plugin that provides file system capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="file-system-plugin",
            version="1.0.0",
            description="Provides file system access capabilities",
            capabilities=["file-read", "file-write", "file-list"],
            required_capabilities=[]
        )
    
    async def setup(self, context):
        print("FileSystemPlugin setup complete")
    
    async def teardown(self):
        print("FileSystemPlugin teardown complete")


class NetworkPlugin(VibePlugin):
    """Example plugin that provides network capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="network-plugin",
            version="1.0.0",
            description="Provides network access capabilities",
            capabilities=["http-request", "websocket"],
            required_capabilities=["basic-auth"]  # Requires authentication
        )
    
    async def setup(self, context):
        print("NetworkPlugin setup complete")
    
    async def teardown(self):
        print("NetworkPlugin teardown complete")


class AuthPlugin(VibePlugin):
    """Example plugin that provides authentication capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="auth-plugin",
            version="1.0.0",
            description="Provides authentication capabilities",
            capabilities=["basic-auth", "oauth2"],
            required_capabilities=[]
        )
    
    async def setup(self, context):
        print("AuthPlugin setup complete")
    
    async def teardown(self):
        print("AuthPlugin teardown complete")


def main():
    """Demonstrate CapabilityRegistry usage."""
    print("=== CapabilityRegistry Example ===\n")
    
    # Create a capability registry
    registry = CapabilityRegistry()
    
    # Create plugin instances
    fs_plugin = FileSystemPlugin()
    network_plugin = NetworkPlugin()
    auth_plugin = AuthPlugin()
    
    # Register plugin capabilities
    registry.register_plugin_capabilities(fs_plugin)
    registry.register_plugin_capabilities(network_plugin)
    registry.register_plugin_capabilities(auth_plugin)
    
    print("1. All registered capabilities:")
    for capability in sorted(registry.get_all_capabilities()):
        providers = registry.get_capability_providers(capability)
        print(f"   - {capability}: provided by {', '.join(providers)}")
    
    print("\n2. Capabilities provided by each plugin:")
    for plugin_name in ["file-system-plugin", "network-plugin", "auth-plugin"]:
        capabilities = registry.get_plugin_capabilities(plugin_name)
        print(f"   - {plugin_name}: {', '.join(sorted(capabilities))}")
    
    print("\n3. Capability requirements validation:")
    for plugin_name in ["file-system-plugin", "network-plugin", "auth-plugin"]:
        has_reqs, missing = registry.validate_capability_requirements(plugin_name)
        status = "Satisfied" if has_reqs else f"Missing: {', '.join(missing)}"
        print(f"   - {plugin_name}: {status}")
    
    print("\n4. Find plugins with specific capabilities:")
    file_plugins = registry.find_plugins_with_capability("file-read")
    print(f"   - Plugins with 'file-read': {', '.join(file_plugins)}")
    
    auth_plugins = registry.find_plugins_with_capability("basic-auth")
    print(f"   - Plugins with 'basic-auth': {', '.join(auth_plugins)}")
    
    print("\n5. Capability registry summary:")
    summary = registry.get_capability_summary()
    print(f"   - Total capabilities: {summary['total_capabilities']}")
    print(f"   - Total providers: {summary['total_providers']}")
    print(f"   - Unsatisfied requirements: {len(summary['unsatisfied_requirements'])}")
    
    print("\n6. Using 'in' operator:")
    print(f"   - 'file-read' in registry: {'file-read' in registry}")
    print(f"   - 'non-existent-cap' in registry: {'non-existent-cap' in registry}")
    
    print(f"\n7. Total capabilities registered: {len(registry)}")


if __name__ == "__main__":
    main()