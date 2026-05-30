#!/usr/bin/env python3
'''
Practical examples demonstrating the Dynamic Priorities feature in Mistral Vibe.

This file provides examples for:
1. Static Priorities: Basic usage of static priorities.
2. Runtime Adjustment: Adjusting priorities at runtime.
3. Context-Aware Resolution: Adjusting priorities based on context.
4. Configuration: Configuring dynamic priorities in `config.toml`.
'''

from vibe.core.plugins.base import PriorityGroup, VibePlugin, PluginMetadata
from vibe.core.plugins.manager import PluginManager
from vibe.core.config import VibeConfig
from vibe.core.config.harness_files import init_harness_files_manager
from pathlib import Path
import asyncio


def example_static_priorities():
    '''
    Example 1: Static Priorities
    
    Demonstrates how to define and use static priority groups using PriorityGroup enum.
    Static priorities are fixed and do not change during execution.
    '''
    print("=" * 60)
    print("Example 1: Static Priorities")
    print("=" * 60)
    
    # Show the available priority groups
    print("Available Priority Groups:")
    print(f"CRITICAL: {PriorityGroup.CRITICAL}")
    print(f"HIGH: {PriorityGroup.HIGH}")
    print(f"DEFAULT: {PriorityGroup.DEFAULT}")
    print(f"LOW: {PriorityGroup.LOW}")
    print(f"DELAYED: {PriorityGroup.DELAYED}")
    print()
    
    # Example plugin with static priority
    class StaticPriorityPlugin(VibePlugin):
        @classmethod
        def metadata(cls) -> PluginMetadata:
            return PluginMetadata(
                name="static-plugin",
                version="1.0.0",
                description="Plugin with static priority",
                priority=PriorityGroup.HIGH  # Static priority
            )
        
        async def setup(self, context):
            pass
            
        async def teardown(self):
            pass
    
    plugin = StaticPriorityPlugin()
    print(f"Static Priority Plugin Priority: {plugin.metadata().priority}")
    print()


async def example_runtime_adjustment():
    '''
    Example 2: Runtime Adjustment
    
    Demonstrates how to adjust priorities dynamically during execution.
    This is useful for responding to changing conditions or requirements.
    '''
    print("=" * 60)
    print("Example 2: Runtime Adjustment")
    print("=" * 60)
    
    # Initialize harness files manager
    init_harness_files_manager()
    
    # Example plugin with runtime priority adjustment
    class RuntimeAdjustmentPlugin(VibePlugin):
        @classmethod
        def metadata(cls) -> PluginMetadata:
            return PluginMetadata(
                name="runtime-adjust-plugin",
                version="1.0.0",
                description="Plugin with runtime priority adjustment",
                priority=PriorityGroup.DEFAULT
            )
        
        async def setup(self, context):
            # Initial priority
            print(f"Initial Priority: {self.metadata().priority}")
            
            # Adjust priority at runtime
            self.set_runtime_priority(PriorityGroup.HIGH)
            print(f"Adjusted Priority: {self.effective_priority()}")
            
            # Further adjustment
            self.set_runtime_priority(PriorityGroup.CRITICAL)
            print(f"Final Priority: {self.effective_priority()}")
            
        async def teardown(self):
            pass
    
    # Create and setup the plugin
    plugin = RuntimeAdjustmentPlugin()
    
    # Create minimal context for setup
    from vibe.core.plugins.base import PluginContext
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None
    )
    
    await plugin.setup(context)
    print()


async def example_context_aware_resolution():
    '''
    Example 3: Context-Aware Resolution
    
    Demonstrates how priorities can be adjusted based on context.
    Context can include system load, task dependencies, or other runtime factors.
    '''
    print("=" * 60)
    print("Example 3: Context-Aware Resolution")
    print("=" * 60)
    
    # Initialize harness files manager
    init_harness_files_manager()
    
    # Example plugin with context-aware priority
    class ContextAwarePlugin(VibePlugin):
        @classmethod
        def metadata(cls) -> PluginMetadata:
            return PluginMetadata(
                name="context-aware-plugin",
                version="1.0.0",
                description="Plugin with context-aware priority",
                priority=PriorityGroup.LOW
            )
        
        async def setup(self, context):
            print(f"Initial Priority: {self.metadata().priority}")
            
        async def teardown(self):
            pass
        
        def context_aware_priority(self, context: 'PluginContext') -> int:
            """Adjust priority based on context."""
            # Higher priority if workdir contains 'critical' in path
            workdir_str = str(context.workdir).lower()
            if 'critical' in workdir_str:
                return PriorityGroup.CRITICAL
            # Higher priority if workdir has many files
            if context.workdir.exists() and len(list(context.workdir.glob('*'))) > 10:
                return PriorityGroup.HIGH
            # Default priority otherwise
            return self.metadata().priority
    
    # Create plugin and context
    plugin = ContextAwarePlugin()
    
    from vibe.core.plugins.base import PluginContext
    config = VibeConfig()
    
    # Context with critical workdir
    critical_context = PluginContext(
        workdir=Path("/critical/project"),
        config=config,
        tool_manager=None
    )
    
    # Context with normal workdir
    normal_context = PluginContext(
        workdir=Path("/normal/project"),
        config=config,
        tool_manager=None
    )
    
    # Setup plugin
    await plugin.setup(normal_context)
    
    # Get priorities based on context
    critical_priority = plugin.context_aware_priority(critical_context)
    normal_priority = plugin.context_aware_priority(normal_context)
    
    print(f"Priority (Critical Context): {critical_priority}")
    print(f"Priority (Normal Context): {normal_priority}")
    print()


def example_configuration():
    '''
    Example 4: Configuration
    
    Demonstrates how to configure dynamic priorities in `config.toml`.
    This example shows the structure of the configuration file.
    '''
    print("=" * 60)
    print("Example 4: Configuration")
    print("=" * 60)
    
    config_example = """
# Example configuration for dynamic priorities in config.toml

[priorities]
# Define priority groups and their base priorities
[[priorities.groups]]
name = "critical"
base_priority = 100

[[priorities.groups]]
name = "high"
base_priority = 75

[[priorities.groups]]
name = "medium"
base_priority = 50

[[priorities.groups]]
name = "low"
base_priority = 25

# Define context weights for context-aware resolution
[priorities.context_weights]
system_load = 0.7
available_resources = 0.5
user_urgency = 0.9
"""
    
    print("Add the following to your `config.toml` file:")
    print(config_example)
    print()


async def main():
    '''
    Run all examples.
    '''
    example_static_priorities()
    await example_runtime_adjustment()
    await example_context_aware_resolution()
    example_configuration()


if __name__ == "__main__":
    asyncio.run(main())