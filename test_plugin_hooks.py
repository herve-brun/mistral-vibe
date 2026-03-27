#!/usr/bin/env python3
"""Test script to verify plugin hooks are being called."""

import asyncio
from pathlib import Path
from vibe.core.config import VibeConfig
from vibe.core.config.harness_files._harness_manager import init_harness_files_manager
from vibe.core.plugins import PluginContext, PluginManager, ToolEventPlugin, PluginMetadata
from vibe.core.plugins.base import VibePlugin


class TestPlugin(ToolEventPlugin):
    """Simple test plugin that logs when hooks are called."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="0.1.0",
            description="Test plugin for hook verification"
        )
    
    async def on_tool_call(self, tool_name: str, arguments: dict, context: PluginContext) -> None:
        print(f"TEST PLUGIN: on_tool_call called with tool={tool_name}")
        print(f"TEST PLUGIN: arguments={arguments}")
    
    async def on_tool_result(self, tool_name: str, arguments: dict, result: str, context: PluginContext) -> None:
        print(f"TEST PLUGIN: on_tool_result called with tool={tool_name}, result={result[:50]}...")


async def main():
    # Initialize harness manager first
    init_harness_files_manager(Path.cwd())
    
    # Create a minimal config
    config = VibeConfig()
    
    # Create plugin context
    plugin_context = PluginContext(
        workdir=Path.cwd(),
        config=config
    )
    
    # Create plugin manager and manually register our test plugin
    plugin_manager = PluginManager(config, plugin_context)
    
    # Manually add the test plugin class to simulate discovery
    from vibe.core.plugins.manager import PluginManager as PM
    classes = [TestPlugin]
    
    for cls in classes:
        meta = cls.metadata()
        if not plugin_manager._is_enabled(meta.name):
            print(f"Plugin {meta.name} disabled by config")
            continue
        try:
            instance: VibePlugin = cls()
        except Exception as e:
            print(f"Failed to instantiate plugin {meta.name}: {e}")
            continue
        
        if not instance.is_applicable(plugin_context):
            print(f"Plugin {meta.name} not applicable to current context")
            continue
        
        try:
            await instance.setup(plugin_context)
        except Exception as e:
            print(f"Plugin {meta.name} raised during setup: {e}")
            continue
        
        plugin_manager._plugins.append(instance)
        if isinstance(instance, ToolEventPlugin):
            plugin_manager._tool_event_plugins.append(instance)
            print(f"Registered tool event plugin: {meta.name}")
    
    # Check what plugins we have
    print(f"\nActive plugins: {[p.metadata().name for p in plugin_manager.all_plugins]}")
    print(f"Tool event plugins: {[p.metadata().name for p in plugin_manager.tool_event_plugins]}")
    
    # Now simulate what happens in the agent loop
    from vibe.core.plugins.middleware import PluginMiddleware
    
    middleware = PluginMiddleware(plugin_manager, plugin_context)
    
    print("\n=== Testing middleware patching ===")
    
    # Create a mock agent loop with _execute_tool
    class MockAgentLoop:
        def __init__(self):
            self._execute_tool_called = False
            
        async def _execute_tool(self, tool_name: str, arguments: dict):
            self._execute_tool_called = True
            print(f"MockAgentLoop._execute_tool called with {tool_name}")
            return "result"
    
    loop = MockAgentLoop()
    middleware.patch_agent_loop(loop)
    
    # Now call the patched version
    print("\n=== Calling patched _execute_tool ===")
    result = asyncio.run_coroutine_threadsafe(
        loop._execute_tool("read_file", {"path": "test.py"}),
        asyncio.get_event_loop()
    ).result()
    
    print(f"\nResult: {result}")
    print(f"Original _execute_tool was called: {loop._execute_tool_called}")


if __name__ == "__main__":
    asyncio.run(main())
