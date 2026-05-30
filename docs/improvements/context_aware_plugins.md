# Context-Aware Plugins

The context-aware plugin system enables plugins to dynamically adjust their behavior and priority based on runtime context.

## Features

### 1. ContextAwarePlugin Mixin

The `ContextAwarePlugin` abstract base class provides a standard interface for context-aware behavior:

```python
from vibe.core.plugins import ContextAwarePlugin, PluginContext

class MyPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        # Adjust priority based on context
        if "important" in str(context.workdir):
            return 50  # HIGH priority
        return 150  # LOW priority
```

### 2. PluginContext

The `PluginContext` provides runtime information:
- Current working directory
- Configuration
- Tool manager
- Other context-specific data

### 3. Integration with PluginManager

The `PluginManager` automatically resolves context-aware priorities when enabled.

### 4. Caching

Context-aware priority calculations are cached for performance.

## Usage

### Basic Context-Aware Plugin

```python
from vibe.core.plugins import VibePlugin, ContextAwarePlugin, PluginContext
from vibe.core.plugins.base import PriorityGroup

class CodeAnalysisPlugin(VibePlugin, ContextAwarePlugin):
    @classmethod
    def metadata(cls):
        return PluginMetadata(
            name="code_analysis",
            description="Context-aware code analysis",
            priority=100,  # DEFAULT priority
            priority_group=PriorityGroup.DEFAULT,
            capabilities=["code_analysis", "linting"]
        )

    def context_aware_priority(self, context: PluginContext) -> int:
        # Higher priority for production code
        if "src/main" in str(context.workdir):
            return 50  # HIGH priority
        
        # Lower priority for test code
        if "tests" in str(context.workdir):
            return 150  # LOW priority
        
        # Default priority
        return 100
```

### Advanced Context Usage

```python
class SmartRefactoringPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        # Check configuration
        config = context.config
        
        # Higher priority if refactoring is enabled in config
        if config.get("enable_refactoring", False):
            return 75
        
        # Check working directory
        workdir = str(context.workdir)
        
        # Higher priority for specific project directories
        if any(dir in workdir for dir in ["src/core", "src/api"]):
            return 60
        
        # Default priority
        return 100

    def setup(self, context: PluginContext):
        # Context can also be used in setup
        if "important_project" in str(context.workdir):
            self._aggressive_mode = True
```

### Plugin Manager Integration

```python
from vibe.core.plugins.manager import PluginManager

# Create plugin manager with context
manager = PluginManager(config)

# Get plugins sorted by context-aware priority
context = PluginContext(
    workdir=Path("/path/to/project"),
    config=config,
    tool_manager=tool_manager
)

sorted_plugins = manager.get_sorted_plugins(context)
```

## Configuration

Enable dynamic priorities in `config.toml`:

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

## Best Practices

1. **Use Context Wisely**: Only adjust priority when context truly matters
2. **Keep Logic Simple**: Avoid complex context-aware logic that's hard to maintain
3. **Cache Results**: The system caches results, but avoid expensive computations
4. **Log Decisions**: Log priority changes for debugging
5. **Test Thoroughly**: Test context-aware behavior with different contexts

## Advanced Features

### Context Data

The `PluginContext` provides access to:
- `workdir`: Current working directory
- `config`: Configuration object
- `tool_manager`: Tool manager instance
- `agent_loop`: Agent loop instance (when available)
- Custom context data

### Dynamic Behavior

```python
class EnvironmentAwarePlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        # Adjust based on environment
        if context.config.get("environment") == "production":
            return 50  # HIGH priority in production
        return 150  # LOW priority otherwise

    def on_tool_call(self, tool_name: str, params: dict, context: ToolCallContext):
        # Context can also be used in tool calls
        if "debug" in str(context.workdir):
            params["verbose"] = True
```

### Context Caching

The system automatically caches context-aware priority calculations. The cache:
- Uses plugin name and context hash as key
- Has a configurable maximum size
- Is thread-safe
- Is invalidated when priorities change

## Examples

### Project-Specific Plugin

```python
class ProjectSpecificPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        workdir = str(context.workdir)
        
        # High priority for main project
        if "main_project" in workdir:
            return 50
        
        # Medium priority for related projects
        if any(proj in workdir for proj in ["utils", "libs", "shared"]):
            return 80
        
        # Low priority otherwise
        return 150
```

### Configuration-Driven Plugin

```python
class ConfigDrivenPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        config = context.config
        
        # Check if plugin is enabled in config
        if not config.get("enable_my_plugin", True):
            return 200  # DELAYED priority if disabled
        
        # Check priority setting in config
        config_priority = config.get("my_plugin_priority")
        if config_priority:
            return config_priority
        
        # Default priority
        return 100
```

### Environment-Aware Plugin

```python
class EnvironmentPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        # Get environment from config
        env = context.config.get("environment", "development")
        
        # Priority based on environment
        if env == "production":
            return 50  # HIGH in production
        elif env == "staging":
            return 75  # HIGH in staging
        else:
            return 120  # Below DEFAULT in development
```

## Performance Considerations

1. **Caching**: Context-aware priorities are cached for performance
2. **Efficient Sorting**: PluginManager uses efficient sorting algorithms
3. **Minimize Computations**: Avoid expensive operations in context_aware_priority
4. **Cache Invalidation**: Cache is automatically invalidated when priorities change

## Troubleshooting

### Common Issues

1. **Priority Not Changing**: Verify context_aware_priority is implemented correctly
2. **Cache Issues**: Check if cache is being invalidated properly
3. **Context Data Missing**: Ensure all needed context data is available
4. **Configuration Issues**: Verify dynamic_priorities is enabled in config

### Debugging

Enable debug logging for context-aware plugins:

```toml
[logging]
level = "DEBUG"

[plugins]
log_priority_changes = true
```

Log messages will show:
- When context-aware priorities are calculated
- Cache hits and misses
- Final priority values