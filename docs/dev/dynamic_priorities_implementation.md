# Dynamic Priorities Implementation

## Overview

This document describes the implementation of the **Dynamic Priorities** feature for the Mistral Vibe plugin system. This feature enables runtime adjustment of plugin execution order based on context, user preferences, or other dynamic conditions.

## Changes Made

### 1. Core Changes

#### `vibe/core/plugins/base.py`

**Added PriorityGroup Enum:**
```python
class PriorityGroup(IntEnum):
    CRITICAL = 25      # 0-49: Critical system plugins
    HIGH = 75          # 50-99: High-priority middleware  
    DEFAULT = 100      # Default for most plugins
    LOW = 175          # 150-199: Lower priority
    DELAYED = 250      # 200+: Delayed execution
```

**Enhanced VibePlugin Class:**
- Added `_runtime_priority` instance variable
- Added `set_runtime_priority(priority: int)` method
- Added `clear_runtime_priority()` method  
- Added `effective_priority()` method
- Added `priority_group` field to `PluginMetadata`

**Enhanced PluginMetadata Class:**
- Added `priority_group: PriorityGroup | None` field

#### `vibe/core/plugins/manager.py`

**Added Dynamic Priority Management:**
- `get_sorted_plugins(context: PluginContext | None = None)` - Returns plugins sorted by effective priority with context-aware resolution
- `_resolve_context_aware_priorities()` - Applies context-aware conflict resolution

#### `vibe/core/config/_settings.py`

**Added Configuration Option:**
- `dynamic_priorities: bool = False` - Enable/disable dynamic priority adjustment

#### `vibe/core/agent_loop.py`

**Added AgentLoop Integration:**
- `adjust_plugin_priority(plugin_name: str, priority: int)` - Adjust plugin priority at runtime

### 2. Testing

**Created Comprehensive Test Suite:**
- `tests/test_dynamic_priorities.py` - 11 test cases covering:
  - PriorityGroup enum values
  - Runtime priority overrides
  - Context-aware priority adjustment
  - PluginManager sorting behavior
  - Backward compatibility
  - Error handling and fallbacks

### 3. Examples

**Created Usage Examples:**
- `examples/dynamic_priorities_example.py` - Demonstrates:
  - Using PriorityGroup enum
  - Runtime priority adjustment
  - Context-aware plugins
  - AgentLoop integration

## Key Features

### 1. PriorityGroup Enum

Semantic priority levels that provide meaningful categories:
- `CRITICAL` (25) - Security, essential system plugins
- `HIGH` (75) - Performance-critical middleware
- `DEFAULT` (100) - Standard plugins
- `LOW` (175) - Background, non-critical plugins
- `DELAYED` (250) - Post-processing, cleanup plugins

### 2. Runtime Priority Overrides

Plugins can adjust their priority at runtime:
```python
plugin.set_runtime_priority(50)  # Increase priority
plugin.clear_runtime_priority()  # Revert to default
```

### 3. Context-Aware Resolution

Plugins can implement `context_aware_priority(context)` method to dynamically adjust priority based on:
- Current workdir contents
- Configuration settings
- System state
- User preferences

### 4. AgentLoop Integration

The agent loop can adjust plugin priorities dynamically:
```python
agent_loop.adjust_plugin_priority("plugin-name", 50)
```

### 5. Backward Compatibility

- Existing plugins continue to work unchanged
- Static priorities are preserved when dynamic priorities are disabled
- No breaking changes to existing APIs

## Usage Examples

### Basic Usage

```python
from vibe.core.plugins.base import PriorityGroup, VibePlugin, PluginMetadata

class MyPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            priority=PriorityGroup.HIGH  # Use semantic priority
        )

    async def setup(self, context):
        # Adjust priority based on context
        if context.config.enable_telemetry:
            self.set_runtime_priority(PriorityGroup.CRITICAL)
```

### Context-Aware Plugin

```python
class SmartPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(name="smart-plugin", priority=100)
    
    def context_aware_priority(self, context):
        if "cache" in str(context.workdir):
            return PriorityGroup.HIGH
        return self.metadata().priority
```

### AgentLoop Integration

```python
# In agent loop or command handler
agent_loop.adjust_plugin_priority("performance-monitor", PriorityGroup.CRITICAL)
```

## Testing

Run the test suite:
```bash
python -m pytest tests/test_dynamic_priorities.py -v
```

All 11 tests should pass, covering:
- Static and dynamic priority behavior
- Runtime adjustments
- Context-aware resolution
- Error handling
- Backward compatibility

## Configuration

Enable dynamic priorities in `config.toml`:
```toml
[plugin_system]
dynamic_priorities = true
```

Or via environment variable:
```bash
export VIBE_DYNAMIC_PRIORITIES=true
```

## Benefits

1. **Flexibility**: Adjust plugin execution order based on runtime conditions
2. **Performance**: Prioritize critical plugins when needed
3. **Context Awareness**: Adapt behavior to current project/workdir
4. **User Control**: Allow users to adjust priorities via AgentLoop
5. **Backward Compatible**: No breaking changes to existing plugins

## Migration Guide

### For Plugin Developers

1. **Use PriorityGroup enum** (recommended):
   ```python
   PluginMetadata(priority=PriorityGroup.HIGH)
   ```

2. **Add context-aware priority** (optional):
   ```python
   def context_aware_priority(self, context):
       return PriorityGroup.HIGH if condition else self.metadata().priority
   ```

3. **Support runtime adjustments** (optional):
   ```python
   # Your plugin can call set_runtime_priority() based on internal logic
   ```

### For Application Developers

1. **Enable dynamic priorities**:
   ```python
   config = VibeConfig(dynamic_priorities=True)
   ```

2. **Adjust priorities at runtime**:
   ```python
   agent_loop.adjust_plugin_priority("plugin-name", new_priority)
   ```

## Technical Details

### Priority Resolution Algorithm

1. Check for runtime priority override (`_runtime_priority`)
2. If none, use static priority from metadata
3. If dynamic priorities enabled and plugin has `context_aware_priority()` method, apply context-aware adjustment
4. Sort plugins by final effective priority (lower values first)

### Error Handling

- Context-aware priority methods that fail fall back to base priority
- Invalid priority values are logged but don't crash the system
- Missing plugins in `adjust_plugin_priority()` return False gracefully

### Performance

- Priority resolution is O(n log n) due to sorting
- Context-aware methods are called only when dynamic priorities are enabled
- No performance impact when feature is disabled

## Future Enhancements

Potential future improvements:
- Priority change events/notifications
- Persistent priority overrides across sessions
- Priority conflict detection and resolution
- Visual priority management in UI

## Conclusion

The Dynamic Priorities feature provides a powerful yet backward-compatible way to control plugin execution order in Mistral Vibe. It enables context-aware, runtime-adjustable plugin prioritization while maintaining full compatibility with existing plugins.