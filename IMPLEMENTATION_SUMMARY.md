# Context-Aware Plugin Implementation Summary

## Overview

This implementation adds context-aware priority resolution to the Mistral Vibe plugin system, allowing plugins to dynamically adjust their execution priority based on runtime context such as working directory, configuration, and other environmental factors.

## Changes Made

### 1. New `ContextAwarePlugin` Mixin (`vibe/core/plugins/context_aware.py`)

- **Abstract Base Class**: `ContextAwarePlugin` defines a single abstract method `context_aware_priority()`
- **Interface**: Plugins implement this method to return a priority adjustment based on the current `PluginContext`
- **Backward Compatible**: Existing plugins continue to work without implementing this interface

### 2. Enhanced `PluginManager` (`vibe/core/plugins/manager.py`)

- **New Method**: `get_sorted_plugins(context: PluginContext | None = None)` 
  - Returns plugins sorted by effective priority
  - Applies context-aware resolution when dynamic priorities are enabled
  - Maintains backward compatibility with existing sorting behavior

- **Context-Aware Resolution**: `_resolve_context_aware_priorities()`
  - Checks if plugins implement `ContextAwarePlugin` interface
  - Calls `context_aware_priority()` method for context-aware plugins
  - Falls back to base priority if context-aware calculation fails
  - Only active when `dynamic_priorities` config is enabled

- **Caching System**: 
  - `_context_aware_priority_cache`: Caches context-aware priority calculations
  - `_generate_cache_key()`: Creates unique cache keys based on plugin name and context hash
  - Cache invalidation: Automatic size management with LRU-like eviction

### 3. Enhanced `PluginMetadata` (`vibe/core/plugins/base.py`)

- **Priority Groups**: New `PriorityGroup` enum for semantic priority ranges
- **Validation**: Added priority range validation with helpful error messages
- **New Fields**: 
  - `priority_group`: Optional priority group classification
  - `capabilities`: List of plugin capabilities
  - `required_capabilities`: Capabilities required by the plugin
  - `runtime_requirements`: Runtime environment requirements

### 4. Enhanced `VibePlugin` Base Class

- **Runtime Priority Management**:
  - `set_runtime_priority()`: Set dynamic priority override
  - `clear_runtime_priority()`: Revert to static priority
  - `effective_priority()`: Get current effective priority
  - Automatic cache invalidation when runtime priority changes

### 5. Updated Exports (`vibe/core/plugins/__init__.py`)

- Added `ContextAwarePlugin` to public exports for easy import

## Key Features

### 1. Dynamic Priority Adjustment

Plugins can adjust their priority based on:
- Current working directory
- Configuration settings
- Presence of specific files or directories
- Project type or structure
- Any other context information

### 2. Caching and Performance

- Context-aware priority calculations are cached
- Cache keys include plugin name and context hash
- Automatic cache size management
- Cache invalidation on context changes

### 3. Backward Compatibility

- Existing plugins work without modification
- Context-aware features are opt-in via mixin interface
- Falls back gracefully if context-aware calculation fails
- No breaking changes to existing APIs

### 4. Configuration

- **Dynamic Priorities**: Enabled via `dynamic_priorities = true` in config
- **Priority Groups**: Semantic classification of priority ranges
- **Validation**: Ensures priorities stay within reasonable bounds

## Usage Examples

### Basic Context-Aware Plugin

```python
from vibe.core.plugins.base import PluginContext, PluginMetadata, VibePlugin
from vibe.core.plugins.context_aware import ContextAwarePlugin

class MyContextAwarePlugin(VibePlugin, ContextAwarePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(name="my-plugin", version="1.0.0", priority=100)

    async def setup(self, context: PluginContext) -> None:
        pass

    async def teardown(self) -> None:
        pass

    def context_aware_priority(self, context: PluginContext) -> int:
        # Adjust priority based on working directory
        if "/important" in str(context.workdir):
            return 50  # Higher priority for important directories
        return 150  # Lower priority otherwise
```

### Using Context-Aware Sorting

```python
from vibe.core.plugins.manager import PluginManager

# Create plugin manager
manager = PluginManager(config, context)

# Get plugins sorted with context-aware priorities
sorted_plugins = manager.get_sorted_plugins(context)

# Get plugins with default sorting (no context-aware adjustment)
default_sorted = manager.get_sorted_plugins(None)
```

## Testing

Comprehensive test suite included in `tests/test_context_aware_plugins.py`:

- **Interface Tests**: Verify `ContextAwarePlugin` abstract base class
- **Integration Tests**: Test plugin manager context-aware sorting
- **Priority Adjustment**: Test dynamic priority calculation
- **Backward Compatibility**: Ensure existing plugins still work
- **Cache Tests**: Verify caching behavior and key generation

## Benefits

1. **Intelligent Plugin Ordering**: Plugins can adapt their execution order based on context
2. **Improved Performance**: Context-aware calculations are cached
3. **Flexible Architecture**: Easy to extend with new context factors
4. **Backward Compatible**: No breaking changes to existing code
5. **Configurable**: Dynamic priorities can be enabled/disabled via config

## Migration Guide

### For Plugin Developers

To make an existing plugin context-aware:

1. **Add Mixin**: Inherit from `ContextAwarePlugin`
2. **Implement Method**: Add `context_aware_priority()` method
3. **Adjust Logic**: Return appropriate priority based on context

```python
# Before
class MyPlugin(VibePlugin):
    # ... existing code ...

# After  
class MyPlugin(VibePlugin, ContextAwarePlugin):
    # ... existing code ...
    
    def context_aware_priority(self, context: PluginContext) -> int:
        # Your context-aware logic here
        return self.metadata().priority  # or adjusted value
```

### For Application Developers

To enable context-aware priorities:

1. **Enable in Config**: Set `dynamic_priorities = true`
2. **Use Context-Aware Sorting**: Call `get_sorted_plugins(context)` instead of `all_plugins`

```python
# Enable dynamic priorities in config.toml
[plugins]
dynamic_priorities = true

# Use context-aware sorting in code
sorted_plugins = plugin_manager.get_sorted_plugins(context)
```

## Performance Considerations

- **Caching**: Context-aware priority calculations are cached to avoid repeated computations
- **Cache Size**: Default cache size is 100 entries, configurable via `_priority_cache_max_size`
- **Cache Invalidation**: Cache is automatically invalidated when plugin priorities change
- **Fallback**: If context-aware calculation fails, plugins fall back to their base priority

## Future Enhancements

Potential areas for future improvement:

1. **Priority Groups**: Automatic priority group assignment
2. **Context Change Detection**: More sophisticated context change detection
3. **Priority Conflict Resolution**: Advanced algorithms for resolving priority conflicts
4. **Performance Monitoring**: Metrics and monitoring for priority adjustments
5. **Visualization**: Tools to visualize plugin execution order and priority changes