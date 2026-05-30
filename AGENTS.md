# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-14
**Commit:** 9421fbc
**Branch:** main

## OVERVIEW

Mistral Vibe is Mistral AI's open-source CLI coding assistant. Python 3.12+ CLI tool providing conversational interface to codebases using Mistral's models.

## STRUCTURE

```
mistral-vibe/
├── vibe/                    # Main package (NOT src/)
│   ├── cli/                 # CLI interface, TUI, autocompletion
│   ├── core/                # Agent loop, tools, LLM backends, plugins
│   ├── acp/                 # Agent Client Protocol (editor integration)
│   └── setup/               # Onboarding, trust folder setup
├── tests/                   # Test suite (root-level)
├── distribution/            # Zed editor extension
├── docs/                    # Documentation
└── scripts/                 # Build/release scripts
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent loop | `vibe/core/agent_loop.py` | Main orchestration |
| Tools | `vibe/core/tools/` | Built-in + MCP tools |
| LLM backends | `vibe/core/llm/backend/` | Mistral, Anthropic, Vertex |
| CLI entry | `vibe/cli/entrypoint.py` | `vibe` command |
| ACP entry | `vibe/acp/entrypoint.py` | `vibe-acp` command |
| Plugin system | `vibe/core/plugins/` | Built-in + custom plugins |
| Skills system | `vibe/core/skills/` | Extensibility |

## CODE MAP

| Symbol | Type | Location |
|--------|------|----------|
| `AgentLoop` | class | `vibe/core/agent_loop.py` |
| `Tool` | class | `vibe/core/tools/base.py` |
| `ToolManager` | class | `vibe/core/tools/manager.py` |
| `LLMBackend` | base | `vibe/core/llm/backend/base.py` |
| `TextualApp` | class | `vibe/cli/textual_ui/app.py` |
| `PluginManager` | class | `vibe/core/plugins/manager.py` |
| `VibePlugin` | class | `vibe/core/plugins/base.py` |

## DEPENDENCIES

Key external libraries:
- **pybreaker** (>=1.4.0) - Circuit breaker for plugin resilience
- **pluggy** (>=1.0.0) - Extension point system (like pytest)
- **pygls** (>=2.1.1) - LSP client integration
- **mcp** (>=1.14.0) - Model Context Protocol

## Tools

- Subclass `BaseTool` from `vibe/core/tools/base.py` with a Pydantic args model and a `BaseToolConfig` generic parameter.
- Implement `async def run(args, ctx: InvokeContext)` and yield events progressively.
- Raise `ToolError` for user-facing failures; raise `ToolPermissionError` for authorization failures.
- Declare permission with `ToolPermission` (`ALWAYS` / `ASK` / `NEVER`); honor it consistently.

## Logging & errors

  - title: "No Docstrings in Tests"
    description: >
      Do not add docstrings to test functions, test methods, or test classes.
      Test names should be descriptive enough to convey intent (e.g.,
      `test_create_user_returns_403_when_unauthorized`). Docstrings in tests add
      noise, duplicate the function name, and can suppress pytest's default output
      (pytest displays the docstring instead of the node id when one is present).
      Use inline comments sparingly for non-obvious setup or assertions instead.
## NOTES

- Dual entry points: `vibe` (CLI), `vibe-acp` (editor protocol)
- Uses `textual` for TUI
- MCP for external tool integrations
- ACP for IDE editor integration (Zed, VS Code)
- Plugin resilience via pybreaker circuit breaker

### Enhanced Error Reporting

#### Overview
Enhanced Error Reporting provides structured and detailed error logging to improve debugging and error handling across the Mistral Vibe ecosystem. It standardizes error formats, captures context, and propagates errors to the agent loop for better visibility and recovery.

#### Structured Logging Format
Errors are logged in a structured JSON format for easy parsing and integration with monitoring tools. Example:

```json
{
  "timestamp": "2026-05-08T12:00:00Z",
  "level": "ERROR",
  "message": "Failed to load plugin",
  "context": {
    "plugin_name": "example_plugin",
    "file_path": "/path/to/plugin.py",
    "line_number": 42
  },
  "stack_trace": "Traceback (most recent call last):\n  ..."
}
```

#### Error Context Information
Errors include contextual information such as:
- **Plugin/Tool Name**: Name of the plugin or tool where the error occurred.
- **File Path**: Path to the file where the error originated.
- **Line Number**: Line number in the file.
- **Additional Metadata**: Any relevant metadata (e.g., configuration settings, input parameters).

#### Error Propagation to the Agent Loop
Errors are propagated to the agent loop, where they are logged and can trigger recovery mechanisms. The agent loop uses this information to:
- Retry failed operations.
- Notify the user of critical issues.
- Adjust behavior based on error severity.

#### Configuration Options
Enhanced Error Reporting can be configured via `config.toml`:

```toml
[error_reporting]
enabled = true
log_level = "DEBUG"
max_context_depth = 5
include_stack_trace = true
```

#### Best Practices for Plugin Developers
- **Use Structured Logging**: Always log errors in the structured JSON format.
- **Include Context**: Provide as much context as possible (e.g., plugin name, file path).
- **Handle Errors Gracefully**: Use try-catch blocks to capture and log errors before propagating them.
- **Avoid Sensitive Data**: Do not include sensitive information (e.g., API keys, passwords) in error logs.

#### Example Usage

```python
import json
import logging
from datetime import datetime

def log_error(message: str, context: dict, stack_trace: str):
    error_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": message,
        "context": context,
        "stack_trace": stack_trace
    }
    logging.error(json.dumps(error_log))

# Example error handling in a plugin
try:
    # Plugin logic here
    pass
except Exception as e:
    context = {
        "plugin_name": "example_plugin",
        "file_path": __file__,
        "line_number": 42
    }
    log_error("Failed to execute plugin", context, str(e))
    raise
```

### Plugin Isolation and Sandboxing

#### Overview
Mistral Vibe provides a robust plugin isolation and sandboxing system to ensure that third-party plugins run securely and do not interfere with the main application or other plugins. This feature enhances stability and security by isolating plugins in separate processes with controlled resource limits.

#### Process Isolation and Resource Limits
- **Process Isolation**: Each plugin runs in its own dedicated process, preventing crashes or misbehavior in one plugin from affecting the main application or other plugins.
- **Resource Limits**: Plugins are constrained by configurable CPU, memory, and execution time limits to prevent resource exhaustion attacks or accidental overconsumption.

#### IPC Mechanism for Safe Communication
- **Inter-Process Communication (IPC)**: Plugins communicate with the main application and other plugins using a secure IPC mechanism. This ensures that data exchanged between processes is serialized and validated, preventing injection attacks or unauthorized access.
- **Message Validation**: All messages passed via IPC are validated to ensure they conform to expected schemas, reducing the risk of malformed data causing issues.

#### Configuration Options
Plugin isolation and sandboxing can be configured via the `config.toml` file or environment variables. Key configuration options include:
- `plugin_isolation_enabled`: Enable or disable plugin isolation (default: `true`).
- `plugin_cpu_limit`: Maximum CPU usage per plugin (e.g., `1.0` for 100% of a single core).
- `plugin_memory_limit`: Maximum memory usage per plugin in MB (e.g., `512` for 512 MB).
- `plugin_timeout`: Maximum execution time per plugin operation in seconds (e.g., `30` for 30 seconds).

Example configuration:
```toml
[plugins]
enable_isolation = true
cpu_limit = 1.0
memory_limit = 512
timeout = 30
```

#### Security Considerations
- **Privilege Separation**: Plugins run with minimal privileges, reducing the potential impact of security vulnerabilities.
- **Network Restrictions**: Plugins are restricted from making arbitrary network requests unless explicitly allowed via configuration.
- **Filesystem Access**: Plugins have limited access to the filesystem, typically restricted to a designated sandbox directory.

#### Best Practices for Plugin Developers
- **Minimize Dependencies**: Reduce the number of dependencies to lower the attack surface and improve performance.
- **Handle Errors Gracefully**: Ensure your plugin handles errors and edge cases gracefully to avoid crashes.
- **Validate Inputs**: Always validate inputs received via IPC to ensure they meet expected criteria.
- **Respect Resource Limits**: Design your plugin to operate within the default resource limits to ensure compatibility across different environments.
- **Use Async I/O**: Prefer asynchronous I/O operations to avoid blocking the plugin process and improve responsiveness.

#### Example Usage
To enable plugin isolation and set resource limits, add the following to your `config.toml`:
```toml
[plugins]
enable_isolation = true
cpu_limit = 1.0
memory_limit = 512
timeout = 30
```

To disable plugin isolation (not recommended for production):
```toml
[plugins]
enable_isolation = false
```

For more details, refer to the [Plugin Development Guide](docs/plugins.md).

### Dynamic Priorities

#### Overview
The Dynamic Priorities feature allows plugins and tools to adjust their execution priority at runtime based on context, dependencies, or user-defined rules. This ensures optimal resource allocation and task scheduling.

#### Priority Groups
Priority groups categorize tasks into logical units (e.g., `high`, `medium`, `low`). Each group can be assigned a base priority, which can be dynamically adjusted.

#### Runtime Priority Adjustment
Priorities can be modified during execution using the `PriorityManager` API. This allows plugins to respond to changing conditions (e.g., resource availability, task urgency).

#### Context-Aware Resolution
The system evaluates context (e.g., current workload, dependencies) to resolve the most appropriate priority for a task. This ensures efficient scheduling and execution.

#### Configuration Options
- **Base Priority**: Default priority for a group.
- **Dynamic Adjustment Rules**: Conditions under which priorities are adjusted.
- **Context Weights**: Importance of different context factors (e.g., CPU load, task dependencies).

#### Best Practices for Plugin Developers
1. **Define Clear Priority Groups**: Use meaningful names for priority groups (e.g., `critical`, `background`).
2. **Use Context Wisely**: Adjust priorities based on relevant context (e.g., user input, system load).
3. **Avoid Over-Prioritization**: Reserve high priorities for truly critical tasks.
4. **Test Dynamic Adjustments**: Ensure priority changes behave as expected under various conditions.

#### Example Usage
```python
from vibe.core.priority import PriorityManager

# Define a priority group
manager = PriorityManager()
manager.add_group("high", base_priority=100)

# Adjust priority at runtime
manager.adjust_priority("high", delta=50)

# Resolve priority based on context
current_priority = manager.resolve_priority("high", context={"load": "low"})
```

### Capability-Based Filtering

#### Overview
Capability-Based Filtering is a feature that allows plugins to declare their capabilities and enables the system to filter and select plugins based on these declarations. This ensures that only plugins with the required capabilities are loaded or used in specific contexts.

#### Capability Declarations
Plugins can declare their capabilities using the `capabilities` attribute in their plugin configuration. Capabilities are defined as a list of strings, each representing a specific capability the plugin provides.

#### Filtering Logic and Usage
The filtering logic is applied during plugin discovery and loading. The system checks the declared capabilities of each plugin against the required capabilities for a given context. Only plugins that match the required capabilities are loaded or used.

#### Runtime Requirements
- Plugins must explicitly declare their capabilities in their configuration.
- The system must be configured to use capability-based filtering for the relevant contexts.

#### Configuration Options
- **Enable/Disable Filtering**: Capability-based filtering can be enabled or disabled globally or for specific contexts.
- **Required Capabilities**: Define the capabilities required for a specific context.
- **Default Capabilities**: Specify default capabilities that are always required.

#### Best Practices for Plugin Developers
- **Declare Capabilities Clearly**: Ensure that capabilities are declared in a clear and concise manner.
- **Use Standard Capability Names**: Adhere to standard capability names to ensure compatibility with the system.
- **Test Capability Declarations**: Verify that capability declarations work as expected in different contexts.

#### Example Usage
```python
# Example plugin configuration with capability declarations
{
    "name": "example_plugin",
    "capabilities": ["code_analysis", "refactoring"],
    "description": "An example plugin with code analysis and refactoring capabilities."
}

# Example of enabling capability-based filtering in a specific context
{
    "context": "code_editing",
    "required_capabilities": ["code_analysis", "refactoring"],
    "filtering_enabled": true
}
```
