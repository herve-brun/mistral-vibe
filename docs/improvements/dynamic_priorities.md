# Dynamic Priorities

The dynamic priorities system provides flexible plugin prioritization that can adapt to runtime conditions and context.

## Features

### 1. Priority Groups

The `PriorityGroup` enum defines semantic priority ranges:

```python
from enum import IntEnum

class PriorityGroup(IntEnum):
    CRITICAL = 25      # 0-49: Critical system plugins
    HIGH = 75        # 50-99: High-priority middleware
    DEFAULT = 100    # 90-110: Default range for most plugins
    LOW = 175       # 150-199: Lower priority plugins
    DELAYED = 250   # 200+: Delayed execution plugins
```

### 2. Runtime Priority Adjustment

Plugins can adjust their priority at runtime:

```python
plugin.set_runtime_priority(50)  # Set to HIGH priority
plugin.clear_runtime_priority()  # Reset to default
```

### 3. Context-Aware Resolution

Plugins can implement context-aware priority resolution:

```python
class MyPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        if context.workdir.name == "important_project":
            return 50  # HIGH priority
        return 150  # LOW priority
```

### 4. Configuration

Configure dynamic priorities in `config.toml`:

```toml
[plugins]
# Enable dynamic priority adjustment
dynamic_priorities = true

# Priority adjustment multipliers
plugin_error_penalty = 10
plugin_usage_boost = 5

# Global priority bounds
plugin_min_priority = 10
plugin_max_priority = 200
```

## Usage

### Setting Priorities

```python
# In plugin metadata (static priority)
@dataclass
class MyPluginMetadata(PluginMetadata):
    name = "my_plugin"
    priority = 100  # DEFAULT priority
    priority_group = PriorityGroup.DEFAULT

# At runtime
plugin = MyPlugin()
plugin.set_runtime_priority(75)  # Set to HIGH priority
```

### Context-Aware Priorities

```python
from vibe.core.plugins import ContextAwarePlugin, PluginContext

class SmartAnalysisPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        # Higher priority for important directories
        if "src/important" in str(context.workdir):
            return 50  # HIGH priority
        
        # Lower priority for test directories
        if "tests" in str(context.workdir):
            return 150  # LOW priority
        
        # Default priority otherwise
        return 100
```

### Getting Effective Priority

```python
effective_priority = plugin.effective_priority()
```

### Plugin Manager Integration

```python
# Get plugins sorted by priority
sorted_plugins = plugin_manager.get_sorted_plugins(context)

# With dynamic priorities enabled
sorted_plugins = plugin_manager.get_sorted_plugins(
    context,
    use_dynamic_priorities=True
)
```

## Priority Groups

| Group      | Range   | Description                          |
|------------|---------|--------------------------------------|
| CRITICAL   | 0-49    | Critical system plugins              |
| HIGH       | 50-99   | High-priority middleware             |
| DEFAULT    | 90-110  | Default range for most plugins       |
| LOW        | 150-199 | Lower priority plugins               |
| DELAYED    | 200+    | Delayed execution plugins            |

## Best Practices

1. **Use Semantic Groups**: Choose priority groups based on plugin importance
2. **Avoid Extreme Values**: Stay within reasonable bounds (10-200)
3. **Context Matters**: Use context-aware priorities when plugin importance varies by context
4. **Dynamic Adjustment**: Adjust priorities at runtime when conditions change
5. **Error Handling**: Handle priority validation errors gracefully

## Validation

The system validates priorities to ensure they stay within bounds:

```python
# This will raise ValueError
plugin.set_runtime_priority(300)  # Above plugin_max_priority

# This will also raise ValueError
plugin.set_runtime_priority(-10)  # Below plugin_min_priority
```

## Performance Considerations

- **Caching**: Plugin priorities are cached for performance
- **Efficient Sorting**: PluginManager uses efficient sorting algorithms
- **Context Resolution**: Context-aware priorities are computed once and cached

## Examples

### Basic Priority Usage

```python
from vibe.core.plugins import VibePlugin, PluginMetadata
from vibe.core.plugins.base import PriorityGroup

class MyPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            description="My custom plugin",
            priority=100,  # DEFAULT priority
            priority_group=PriorityGroup.DEFAULT
        )

    def setup(self, context: PluginContext):
        # Increase priority for important operations
        self.set_runtime_priority(75)  # HIGH priority
```

### Advanced Context-Aware Plugin

```python
from vibe.core.plugins import VibePlugin, ContextAwarePlugin, PluginContext
from vibe.core.plugins.base import PriorityGroup

class CodeQualityPlugin(VibePlugin, ContextAwarePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="code_quality",
            description="Code quality analysis plugin",
            priority=100,
            priority_group=PriorityGroup.DEFAULT,
            capabilities=["code_analysis", "linting", "formatting"]
        )

    def context_aware_priority(self, context: PluginContext) -> int:
        # Higher priority for production code
        if "src/main" in str(context.workdir):
            return 50  # HIGH priority
        
        # Lower priority for test code
        if "src/test" in str(context.workdir):
            return 150  # LOW priority
        
        # Default priority
        return 100

    def setup(self, context: PluginContext):
        # Log priority changes for debugging
        logger.info(f"Plugin priority set to {self.effective_priority()}")