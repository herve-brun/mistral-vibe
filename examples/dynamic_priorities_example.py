"""Example demonstrating the Dynamic Priorities feature.

This example shows how to:
1. Use PriorityGroup enum for semantic priority levels
2. Set runtime priority overrides
3. Create context-aware plugins that adjust priority dynamically
4. Use AgentLoop to adjust plugin priorities at runtime
"""

from vibe.core.plugins.base import (
    PriorityGroup, 
    PluginMetadata, 
    VibePlugin, 
    PluginContext
)
from vibe.core.plugins.manager import PluginManager
from vibe.core.config import VibeConfig
from pathlib import Path
import asyncio


# Example 1: Using PriorityGroup enum
class CriticalSecurityPlugin(VibePlugin):
    """A plugin that should always run first for security checks."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="security-audit",
            version="1.0.0", 
            description="Security auditing plugin",
            priority=PriorityGroup.CRITICAL  # Use enum for semantic meaning
        )

    async def setup(self, context: PluginContext) -> None:
        print("Security plugin initialized with priority:", self.effective_priority())

    async def teardown(self) -> None:
        pass


# Example 2: Plugin with runtime priority adjustment
class AdaptiveLoggingPlugin(VibePlugin):
    """A plugin that can adjust its priority based on runtime conditions."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="adaptive-logger",
            version="1.0.0",
            description="Adaptive logging plugin",
            priority=PriorityGroup.DEFAULT
        )

    async def setup(self, context: PluginContext) -> None:
        # In a real scenario, this might check environment variables,
        # config settings, or other runtime conditions
        if context.config.enable_telemetry:
            # If telemetry is enabled, make this plugin higher priority
            self.set_runtime_priority(PriorityGroup.HIGH)
            print("Telemetry enabled - increased logging priority to", self.effective_priority())
        else:
            print("Telemetry disabled - using default priority", self.effective_priority())

    async def teardown(self) -> None:
        pass


# Example 3: Context-aware plugin with dynamic priority method
class SmartCachingPlugin(VibePlugin):
    """A plugin that adjusts priority based on workdir context."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="smart-cache",
            version="1.0.0",
            description="Context-aware caching plugin",
            priority=PriorityGroup.LOW  # Default to low priority
        )

    async def setup(self, context: PluginContext) -> None:
        print("Smart cache plugin initialized with priority:", self.effective_priority())

    async def teardown(self) -> None:
        pass
    
    def context_aware_priority(self, context: PluginContext) -> int:
        """Adjust priority based on current workdir."""
        workdir_str = str(context.workdir).lower()
        
        # Higher priority in project directories containing 'cache' or 'temp'
        if 'cache' in workdir_str or 'temp' in workdir_str:
            return PriorityGroup.HIGH
        
        # Higher priority if there are many files (simulated)
        if context.workdir.exists() and len(list(context.workdir.glob('*'))) > 100:
            return PriorityGroup.HIGH
        
        # Default priority otherwise
        return self.metadata().priority


# Example 4: Using AgentLoop to adjust priorities dynamically
async def demonstrate_agent_loop_priority_adjustment():
    """Show how AgentLoop can adjust plugin priorities at runtime."""
    
    # Create a minimal config and context for demonstration
    from vibe.core.config.harness_files import init_harness_files_manager
    init_harness_files_manager()
    
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    manager = PluginManager(config, context)
    
    # Add our example plugins
    security_plugin = CriticalSecurityPlugin()
    logging_plugin = AdaptiveLoggingPlugin() 
    cache_plugin = SmartCachingPlugin()
    
    manager._plugins = [security_plugin, logging_plugin, cache_plugin]
    
    # Setup plugins
    for plugin in manager.all_plugins:
        await plugin.setup(context)
    
    print("\n=== Initial Plugin Order ===")
    sorted_plugins = manager.get_sorted_plugins(context)
    for i, plugin in enumerate(sorted_plugins):
        print(f"{i+1}. {plugin.metadata().name} (priority: {plugin.effective_priority()})")
    
    # Simulate AgentLoop adjusting priority at runtime
    print("\n=== Adjusting priorities dynamically ===")
    
    # Increase cache plugin priority due to detected high I/O
    cache_plugin.set_runtime_priority(PriorityGroup.CRITICAL)
    print(f"Increased {cache_plugin.metadata().name} priority to {cache_plugin.effective_priority()}")
    
    # Decrease logging priority temporarily
    logging_plugin.set_runtime_priority(PriorityGroup.LOW)
    print(f"Decreased {logging_plugin.metadata().name} priority to {logging_plugin.effective_priority()}")
    
    print("\n=== New Plugin Order ===")
    sorted_plugins = manager.get_sorted_plugins(context)
    for i, plugin in enumerate(sorted_plugins):
        print(f"{i+1}. {plugin.metadata().name} (priority: {plugin.effective_priority()})")
    
    # Clean up
    for plugin in manager.all_plugins:
        await plugin.teardown()


# Example 5: PriorityGroup usage examples
def demonstrate_priority_groups():
    """Show how to use PriorityGroup enum."""
    print("\n=== PriorityGroup Enum Values ===")
    print(f"CRITICAL (0-49): {PriorityGroup.CRITICAL}")
    print(f"HIGH (50-99): {PriorityGroup.HIGH}")
    print(f"DEFAULT (100): {PriorityGroup.DEFAULT}")
    print(f"LOW (150-199): {PriorityGroup.LOW}")
    print(f"DELAYED (200+): {PriorityGroup.DELAYED}")
    
    print("\n=== Usage in PluginMetadata ===")
    print("PluginMetadata(priority=PriorityGroup.CRITICAL)")
    print("PluginMetadata(priority=PriorityGroup.HIGH)")
    print("PluginMetadata(priority=PriorityGroup.DEFAULT)")


if __name__ == "__main__":
    print("=== Dynamic Priorities Feature Examples ===")
    
    # Show priority groups
    demonstrate_priority_groups()
    
    # Run the async demonstration
    asyncio.run(demonstrate_agent_loop_priority_adjustment())
    
    print("\n=== Key Features Demonstrated ===")
    print("+ PriorityGroup enum for semantic priority levels")
    print("+ Runtime priority overrides with set_runtime_priority()")
    print("+ Context-aware priority adjustment")
    print("+ Dynamic priority management through PluginManager")
    print("+ Backward compatibility with existing plugins")