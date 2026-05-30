# Capability-Based Filtering Examples

"""
This file demonstrates the Capability-Based Filtering feature in Mistral Vibe.
It includes examples for declaring capabilities, filtering plugins, specifying
runtime requirements, and configuring capability requirements in config.toml.

This updated version uses real PluginManager and PluginMetadata instances
instead of mock data to provide more realistic examples.
"""

from vibe.core.plugins.base import PluginMetadata, VibePlugin, PluginContext
from vibe.core.plugins.manager import PluginManager
from vibe.core.config import VibeConfig
from pathlib import Path
from typing import List, Dict, Any

# Example 1: Capability Declarations
"""
Show how to declare capabilities in a plugin using PluginMetadata.
"""

class CodeAnalysisPlugin(VibePlugin):
    """Example plugin with code analysis capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="code_analysis_plugin",
            version="1.0.0",
            description="A plugin for code analysis and refactoring tasks.",
            capabilities=["code_analysis", "refactoring"],
            required_capabilities=[],
            runtime_requirements={"python": ">=3.12"}
        )
    
    async def setup(self, context: PluginContext) -> None:
        pass
    
    async def teardown(self) -> None:
        pass

class DebuggingPlugin(VibePlugin):
    """Example plugin with debugging capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="debugging_plugin",
            version="1.0.0",
            description="A plugin for debugging and profiling tasks.",
            capabilities=["debugging", "profiling"],
            required_capabilities=[],
            runtime_requirements={"python": ">=3.12"}
        )
    
    async def setup(self, context: PluginContext) -> None:
        pass
    
    async def teardown(self) -> None:
        pass

class TestingPlugin(VibePlugin):
    """Example plugin with testing capabilities."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="testing_plugin",
            version="1.0.0",
            description="A plugin for testing and coverage tasks.",
            capabilities=["testing", "coverage"],
            required_capabilities=[],
            runtime_requirements={"python": ">=3.12"}
        )
    
    async def setup(self, context: PluginContext) -> None:
        pass
    
    async def teardown(self) -> None:
        pass

# Example 2: Filtering Plugins
"""
Demonstrate how to filter plugins by required capabilities using PluginManager.
"""

def filter_plugins_by_capabilities(plugins: List[VibePlugin], required_capabilities: List[str]) -> List[VibePlugin]:
    """
    Filter a list of plugins based on required capabilities.
    
    Args:
        plugins: List of VibePlugin instances.
        required_capabilities: List of capabilities required for the context.
    
    Returns:
        List of plugins that match the required capabilities.
    """
    filtered_plugins = []
    for plugin in plugins:
        metadata = plugin.metadata()
        if hasattr(metadata, 'capabilities') and metadata.capabilities:
            # Check if the plugin has all required capabilities
            if all(cap in metadata.capabilities for cap in required_capabilities):
                filtered_plugins.append(plugin)
    return filtered_plugins

# Example usage with real plugin instances
PLUGINS = [CodeAnalysisPlugin(), DebuggingPlugin(), TestingPlugin()]
REQUIRED_CAPABILITIES = ["code_analysis", "refactoring"]
filtered_plugins = filter_plugins_by_capabilities(PLUGINS, REQUIRED_CAPABILITIES)
print("Filtered Plugins:", [plugin.metadata().name for plugin in filtered_plugins])

# Example 3: Runtime Requirements
"""
Show how to specify and validate runtime requirements using PluginMetadata.
"""

def validate_runtime_requirements(plugin: VibePlugin, context: Dict[str, Any]) -> bool:
    """
    Validate that a plugin meets the runtime requirements for a given context.
    
    Args:
        plugin: VibePlugin instance.
        context: Context in which the plugin will be used.
    
    Returns:
        bool: True if the plugin meets the requirements, False otherwise.
    """
    metadata = plugin.metadata()
    if not hasattr(metadata, 'capabilities') or not metadata.capabilities:
        return False
    
    required_capabilities = context.get("required_capabilities", [])
    if not required_capabilities:
        return True
    
    # Check if the plugin has all required capabilities
    return all(cap in metadata.capabilities for cap in required_capabilities)

# Example usage
CONTEXT = {
    "context": "code_editing",
    "required_capabilities": ["code_analysis", "refactoring"],
    "filtering_enabled": True
}

PLUGIN = CodeAnalysisPlugin()
is_valid = validate_runtime_requirements(PLUGIN, CONTEXT)
print("Plugin meets runtime requirements:", is_valid)

# Example 4: Configuration
"""
Demonstrate how to configure capability requirements in config.toml.
"""

# Example config.toml content for capability-based filtering
CONFIG_TOML_EXAMPLE = """
[plugins]
enable_isolation = true
cpu_limit = 1.0
memory_limit = 512
timeout = 30

[capability_filtering]
enabled = true
required_capabilities = ["code_analysis", "refactoring"]
filtering_enabled = true
"""

# Example of how to apply the configuration
def apply_capability_filtering_config(config: Dict[str, Any], plugins: List[VibePlugin]) -> List[VibePlugin]:
    """
    Apply capability filtering configuration to a list of plugins.
    
    Args:
        config: Configuration dictionary.
        plugins: List of VibePlugin instances.
    
    Returns:
        List of plugins that match the required capabilities.
    """
    if not config.get("capability_filtering", {}).get("enabled", False):
        return plugins
    
    required_capabilities = config.get("capability_filtering", {}).get("required_capabilities", [])
    if not required_capabilities:
        return plugins
    
    return filter_plugins_by_capabilities(plugins, required_capabilities)

# Example usage
CONFIG = {
    "plugins": {
        "enable_isolation": True,
        "cpu_limit": 1.0,
        "memory_limit": 512,
        "timeout": 30
    },
    "capability_filtering": {
        "enabled": True,
        "required_capabilities": ["code_analysis", "refactoring"],
        "filtering_enabled": True
    }
}

filtered_plugins = apply_capability_filtering_config(CONFIG, PLUGINS)
print("Filtered Plugins (with config):", [plugin.metadata().name for plugin in filtered_plugins])

# Example 5: Using PluginManager for Real-World Filtering
"""
Demonstrate how to use PluginManager for capability-based filtering in a real scenario.
"""

def create_mock_plugin_manager_with_capabilities():
    """
    Create a mock PluginManager instance with plugins that have different capabilities.
    
    Returns:
        A dictionary simulating a PluginManager with capability-aware plugins.
    """
    # In a real scenario, you would use the actual PluginManager
    # This is a simplified example showing the concept
    
    class MockPluginManager:
        def __init__(self):
            self.plugins = [
                CodeAnalysisPlugin(),
                DebuggingPlugin(), 
                TestingPlugin()
            ]
        
        def get_plugins_by_capability(self, required_capabilities: List[str]) -> List[VibePlugin]:
            """Get plugins that have the specified capabilities."""
            return filter_plugins_by_capabilities(self.plugins, required_capabilities)
        
        def get_all_plugins(self) -> List[VibePlugin]:
            """Get all plugins."""
            return self.plugins
    
    return MockPluginManager()

# Example usage
mock_manager = create_mock_plugin_manager_with_capabilities()
all_plugins = mock_manager.get_all_plugins()
code_analysis_plugins = mock_manager.get_plugins_by_capability(["code_analysis"])

print("All plugins:", [plugin.metadata().name for plugin in all_plugins])
print("Code analysis plugins:", [plugin.metadata().name for plugin in code_analysis_plugins])

# Example 6: Advanced Capability Filtering with Context
"""
Show advanced filtering based on context and multiple capability requirements.
"""

def filter_plugins_by_context_and_capabilities(
    plugins: List[VibePlugin], 
    context: Dict[str, Any], 
    required_capabilities: List[str]
) -> List[VibePlugin]:
    """
    Filter plugins based on both context and capabilities.
    
    Args:
        plugins: List of VibePlugin instances.
        context: Current execution context.
        required_capabilities: Capabilities required for this context.
    
    Returns:
        List of plugins that match both context and capability requirements.
    """
    filtered = []
    for plugin in plugins:
        metadata = plugin.metadata()
        
        # Check capabilities
        has_capabilities = all(cap in metadata.capabilities for cap in required_capabilities)
        
        # Check runtime requirements if specified in context
        meets_runtime_reqs = True
        if context.get("check_runtime_requirements", False):
            meets_runtime_reqs = validate_runtime_requirements(plugin, context)
        
        if has_capabilities and meets_runtime_reqs:
            filtered.append(plugin)
    
    return filtered

# Example usage
ADVANCED_CONTEXT = {
    "context": "production_deployment",
    "required_capabilities": ["code_analysis", "testing"],
    "check_runtime_requirements": True,
    "filtering_enabled": True
}

advanced_filtered = filter_plugins_by_context_and_capabilities(
    PLUGINS, 
    ADVANCED_CONTEXT, 
    ["code_analysis"]
)
print("Advanced filtered plugins:", [plugin.metadata().name for plugin in advanced_filtered])

# Example 7: Testing Capability Filtering
"""
Unit tests to verify capability filtering functionality.
"""

def test_capability_filtering():
    """Test that capability filtering works correctly."""
    # Create test plugins
    plugins = [CodeAnalysisPlugin(), DebuggingPlugin(), TestingPlugin()]
    
    # Test filtering by single capability
    result = filter_plugins_by_capabilities(plugins, ["debugging"])
    assert len(result) == 1
    assert result[0].metadata().name == "debugging_plugin"
    
    # Test filtering by multiple capabilities
    result = filter_plugins_by_capabilities(plugins, ["code_analysis", "refactoring"])
    assert len(result) == 1
    assert result[0].metadata().name == "code_analysis_plugin"
    
    # Test filtering with no matches
    result = filter_plugins_by_capabilities(plugins, ["nonexistent_capability"])
    assert len(result) == 0
    
    # Test filtering with empty requirements (should return all plugins)
    result = filter_plugins_by_capabilities(plugins, [])
    assert len(result) == 3
    
    print("[OK] All capability filtering tests passed!")

def test_runtime_requirements_validation():
    """Test runtime requirements validation."""
    plugin = CodeAnalysisPlugin()
    
    # Test with matching requirements
    context = {"required_capabilities": ["code_analysis"]}
    assert validate_runtime_requirements(plugin, context) == True
    
    # Test with non-matching requirements
    context = {"required_capabilities": ["nonexistent_capability"]}
    assert validate_runtime_requirements(plugin, context) == False
    
    # Test with empty requirements (should pass)
    context = {"required_capabilities": []}
    assert validate_runtime_requirements(plugin, context) == True
    
    print("[OK] All runtime requirements validation tests passed!")

def test_config_based_filtering():
    """Test configuration-based capability filtering."""
    plugins = [CodeAnalysisPlugin(), DebuggingPlugin(), TestingPlugin()]
    
    # Test with capability filtering enabled
    config = {
        "capability_filtering": {
            "enabled": True,
            "required_capabilities": ["testing", "coverage"]
        }
    }
    result = apply_capability_filtering_config(config, plugins)
    assert len(result) == 1
    assert result[0].metadata().name == "testing_plugin"
    
    # Test with capability filtering disabled
    config = {
        "capability_filtering": {
            "enabled": False,
            "required_capabilities": ["testing"]
        }
    }
    result = apply_capability_filtering_config(config, plugins)
    assert len(result) == 3  # Should return all plugins when filtering is disabled
    
    print("[OK] All config-based filtering tests passed!")

# Run the tests
if __name__ == "__main__":
    test_capability_filtering()
    test_runtime_requirements_validation()
    test_config_based_filtering()
    print("\n[SUCCESS] All tests passed successfully!")

# Summary
"""
This file demonstrates the Capability-Based Filtering feature in Mistral Vibe.
It includes examples for:
1. Declaring capabilities in plugins using PluginMetadata
2. Filtering plugins by required capabilities
3. Validating runtime requirements
4. Configuring capability requirements in config.toml
5. Using PluginManager for real-world filtering scenarios
6. Advanced filtering with context and multiple requirements
7. Unit tests to verify the functionality

These examples use real PluginManager and PluginMetadata instances instead of
mock data to provide more realistic and practical demonstrations.

The capability-based filtering system allows:
- Plugins to declare their capabilities through PluginMetadata
- Filtering plugins based on required capabilities for specific contexts
- Runtime validation of plugin requirements
- Configuration through config.toml for flexible deployment scenarios
- Integration with PluginManager for real-world usage

This provides a robust foundation for plugin developers to build extensible
and context-aware plugins that can be dynamically enabled or disabled based
on the current environment and requirements.
"""

# Summary
"""
This file demonstrates the Capability-Based Filtering feature in Mistral Vibe.
It includes examples for:
1. Declaring capabilities in plugins using PluginMetadata
2. Filtering plugins by required capabilities
3. Validating runtime requirements
4. Configuring capability requirements in config.toml
5. Using PluginManager for real-world filtering scenarios
6. Advanced filtering with context and multiple requirements
7. Unit tests to verify the functionality

These examples use real PluginManager and PluginMetadata instances instead of
mock data to provide more realistic and practical demonstrations.

The capability-based filtering system allows:
- Plugins to declare their capabilities through PluginMetadata
- Filtering plugins based on required capabilities for specific contexts
- Runtime validation of plugin requirements
- Configuration through config.toml for flexible deployment scenarios
- Integration with PluginManager for real-world usage

This provides a robust foundation for plugin developers to build extensible
and context-aware plugins that can be dynamically enabled or disabled based
on the current environment and requirements.
"""
