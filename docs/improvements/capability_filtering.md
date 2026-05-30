# Capability-Based Filtering

The capability-based filtering system provides fine-grained control over plugin loading and activation based on declared capabilities.

## Features

### 1. Capability Declarations

Plugins declare their capabilities in the `PluginMetadata`:

```python
from dataclasses import dataclass, field
from vibe.core.plugins.base import PluginMetadata

@dataclass
class MyPluginMetadata(PluginMetadata):
    name: str = "my_plugin"
    capabilities: list[str] = field(default_factory=lambda: ["code_analysis", "refactoring"])
    required_capabilities: list[str] = field(default_factory=lambda: ["file_system"])
```

### 2. Filtering Logic

The `PluginManager` filters plugins based on:
- Required capabilities (whitelist)
- Excluded capabilities (blacklist)
- Runtime requirements

### 3. Runtime Capability Checks

The new `CapabilityRegistry` enables runtime capability discovery:

```python
registry = CapabilityRegistry()
registry.register(["code_analysis", "refactoring"])

if registry.has_capability("code_analysis"):
    # Enable code analysis features
```

### 4. Configuration

Configure capability filtering in `config.toml`:

```toml
[plugins]
# Capabilities that plugins must provide
plugin_capabilities_required = ["code_analysis", "refactoring"]

# Capabilities that will prevent plugins from loading
plugin_capabilities_excluded = ["experimental", "unstable"]
```

## Usage

### Declaring Capabilities

```python
from vibe.core.plugins import VibePlugin, PluginMetadata

class CodeAnalysisPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="code_analysis",
            description="Advanced code analysis plugin",
            capabilities=["code_analysis", "linting", "static_analysis"],
            required_capabilities=["file_system", "python_3.8+"]
        )
```

### Filtering Plugins

```python
from vibe.core.plugins.manager import PluginManager

manager = PluginManager(config)

# Filter plugins based on configuration
filtered_plugins = manager.filter_by_capabilities(plugin_classes)

# Get plugins with specific capabilities
analysis_plugins = [p for p in filtered_plugins if "code_analysis" in p.metadata().capabilities]
```

### Runtime Capability Checks

```python
from vibe.core.plugins.registry import CapabilityRegistry

# Create and populate registry
registry = CapabilityRegistry()
for plugin in active_plugins:
    registry.register(plugin.metadata().capabilities)

# Check for capabilities
if registry.has_capability("code_analysis"):
    print("Code analysis is available!")

# Find plugins by capability
refactoring_plugins = registry.get_plugins_with_capability("refactoring")
```

### Configuration Examples

```toml
[plugins]
# Only load plugins that provide code analysis
plugin_capabilities_required = ["code_analysis"]

# Exclude plugins that are experimental or unstable
plugin_capabilities_excluded = ["experimental", "unstable"]

# Capability groups for easier configuration
capability_groups = {
    "code_editing": ["code_analysis", "refactoring", "formatting"],
    "testing": ["test_runner", "coverage", "mocking"]
}
```

## Capability Naming Convention

Capability names should:
- Use **kebab-case** (lowercase with hyphens)
- Be descriptive but concise
- Avoid special characters (except hyphens and underscores)
- Follow the pattern: `{action}_{subject}` or `{subject}_{action}`

Examples:
- `code_analysis`
- `file_system_access`
- `python_3.8+`
- `git_integration`
- `database_migration`

## Best Practices

1. **Declare Accurately**: Only declare capabilities your plugin actually provides
2. **Be Specific**: Use specific capability names rather than broad ones
3. **Document Capabilities**: Document what each capability means in your plugin
4. **Use Groups**: Leverage capability groups in configuration for easier management
5. **Check at Runtime**: Use the CapabilityRegistry for dynamic feature enabling

## Advanced Features

### Capability Groups

Define capability groups in configuration:

```toml
[plugins.capability_groups]
code_editing = ["code_analysis", "refactoring", "formatting"]
testing = ["test_runner", "coverage", "mocking"]
database = ["sql_access", "nosql_access", "migrations"]
```

### Runtime Requirements

Specify runtime requirements in plugin metadata:

```python
@dataclass
class MyPluginMetadata(PluginMetadata):
    name: str = "my_plugin"
    runtime_requirements: dict = field(default_factory=lambda: {
        "python": ">=3.8",
        "platform": "linux|windows|darwin",
        "memory": ">=512MB"
    })
```

### Dynamic Capability Discovery

```python
# Find all plugins that provide a specific capability
analysis_plugins = [
    plugin for plugin in active_plugins
    if "code_analysis" in plugin.metadata().capabilities
]

# Check if a capability is available
if any("code_analysis" in plugin.metadata().capabilities for plugin in active_plugins):
    print("Code analysis is available!")
```

## Examples

### Basic Capability Declaration

```python
from vibe.core.plugins import VibePlugin, PluginMetadata

class LintingPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="linting",
            description="Code linting plugin",
            capabilities=["code_analysis", "linting", "style_checking"],
            required_capabilities=["file_system"]
        )
```

### Advanced Configuration

```toml
[plugins]
# Only load plugins that provide testing capabilities
plugin_capabilities_required = ["test_runner"]

# Exclude experimental plugins
plugin_capabilities_excluded = ["experimental", "alpha", "beta"]

# Define capability groups for easier configuration
[plugins.capability_groups]
testing = ["test_runner", "coverage", "mocking", "assertions"]
code_quality = ["linting", "formatting", "static_analysis"]
```

### Runtime Capability Check

```python
from vibe.core.plugins.registry import CapabilityRegistry

# Initialize registry
registry = CapabilityRegistry()

# Register capabilities from active plugins
for plugin in plugin_manager.active_plugins():
    registry.register(plugin.metadata().capabilities)

# Enable features based on available capabilities
if registry.has_capability("code_analysis"):
    enable_code_analysis_features()

if registry.has_capability("test_runner"):
    enable_testing_features()
```

### Plugin Discovery by Capability

```python
# Find all plugins that provide refactoring capabilities
refactoring_plugins = [
    plugin for plugin in plugin_manager.active_plugins()
    if "refactoring" in plugin.metadata().capabilities
]

# Use the first available refactoring plugin
if refactoring_plugins:
    refactoring_plugin = refactoring_plugins[0]
    refactoring_plugin.refactor(code)
```

## Troubleshooting

### Common Issues

1. **Plugin Not Loading**: Check if the plugin's capabilities match the required capabilities in configuration
2. **Capability Conflicts**: Ensure no excluded capabilities are declared by the plugin
3. **Runtime Requirements**: Verify the plugin's runtime requirements are met
4. **Naming Issues**: Make sure capability names follow the kebab-case convention

### Debugging

Enable debug logging to troubleshoot capability filtering:

```toml
[logging]
level = "DEBUG"

[plugins]
log_filtering_decisions = true
```