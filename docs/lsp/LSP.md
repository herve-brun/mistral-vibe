# Language Server Protocol (LSP) in Mistral Vibe

This document provides a comprehensive guide to using **Language Server Protocol (LSP)** tools in Mistral Vibe. LSP enables advanced code navigation, analysis, and refactoring across multiple programming languages.

---

## Table of Contents

1. [Recent Improvements](#recent-improvements)
2. [Future Improvements](#future-improvements)
3. [LSP Tools Overview](#lsp-tools-overview)
4. [Decision Tree](#decision-tree)
5. [When to Use LSP vs Command-Line Tools](#when-to-use-lsp-vs-command-line-tools)
6. [Fallback Rules](#fallback-rules)
7. [Quick Reference](#quick-reference)
8. [lsp_document_symbols](#lsp_document_symbols)
9. [lsp_workspace_symbols](#lsp_workspace_symbols)
10. [lsp_formatting](#lsp_formatting)
11. [lsp_status](#lsp_status)
12. [lsp_document_highlight](#lsp_document_highlight)
13. [lsp_symbol_references](#lsp_symbol_references)
14. [lsp_signature_help](#lsp_signature_help)
15. [lsp_code_action](#lsp_code_action)
16. [LSP Debug Tool](#lsp-debug-tool)
17. [Enhanced Error Reporting](#enhanced-error-reporting)
18. [Plugin Sandbox Feature](#plugin-sandbox-feature)
19. [Dynamic Priorities System](#dynamic-priorities-system)
20. [Capability-Based Filtering](#capability-based-filtering)
21. [Context-Aware Plugins](#context-aware-plugins)
22. [Performance Optimizations](#performance-optimizations)
23. [Pluggy Integration](#pluggy-integration)
24. [Recommendations](#recommendations)
25. [Todo/Next Steps](#todo-next-steps)

---

## Recent Improvements

Mistral Vibe has undergone significant improvements to enhance stability, security, and performance. The following sections detail these improvements:

### 1. Enhanced Error Reporting
- **Structured JSON Logging**: Errors are now logged in a structured JSON format for easy parsing and integration with monitoring tools.
- **Error Context Capture**: Errors include comprehensive context information such as plugin name, file path, line number, and additional metadata.
- **Error Propagation**: Errors are properly propagated to the agent loop with full context, enabling better recovery mechanisms.
- **Configuration**: New configuration options in `config.toml` allow customization of error reporting behavior.

### 2. Plugin Sandbox Improvements
- **Process Isolation**: Plugins now run in separate processes, providing true memory isolation and crash protection.
- **Resource Limits**: Configurable CPU, memory, and execution time limits prevent plugins from consuming excessive system resources.
- **Secure IPC**: Enhanced inter-process communication with message validation, checksum verification, and error handling.
- **Security Measures**: Filesystem access restrictions, network access control, and system call limitations improve security.

### 3. Dynamic Priorities System
- **Priority Groups**: Tasks are categorized into logical units (e.g., `high`, `medium`, `low`) with configurable base priorities.
- **Runtime Priority Adjustment**: Priorities can be modified during execution using the `PriorityManager` API.
- **Context-Aware Resolution**: The system evaluates context to resolve the most appropriate priority for a task.
- **Configuration**: Dynamic priorities can be configured via `config.toml`.

### 4. Capability-Based Filtering
- **Capability Declarations**: Plugins declare their capabilities, enabling fine-grained control over plugin loading and activation.
- **Filtering Logic**: The `PluginManager` filters plugins based on required and excluded capabilities.
- **Runtime Capability Checks**: The `CapabilityRegistry` enables runtime capability discovery and validation.
- **Configuration**: Capability filtering can be configured via `config.toml`.

### 5. Context-Aware Plugins
- **ContextAwarePlugin Mixin**: Provides a standard interface for context-aware behavior.
- **PluginContext**: Provides runtime information such as current working directory, configuration, and tool manager.
- **Integration with PluginManager**: The `PluginManager` automatically resolves context-aware priorities when enabled.
- **Caching**: Context-aware priority calculations are cached for performance.

### 6. Performance Optimizations
- **Plugin Priority Caching**: The `PluginManager` caches plugin priorities to avoid repeated calculations.
- **Efficient Plugin Sorting**: Plugins are sorted using optimized algorithms with cached priorities.
- **Context-Aware Caching**: Context-aware priority calculations are cached based on context hash.
- **Reduced Overhead**: Various optimizations reduce overhead in plugin discovery and execution.

---

## Future Improvements

- **Multi-LSP Fallback**: Automatically fall back to alternative LSP servers if the primary fails (e.g., try `pylsp` then `pyright` for Python).
- **Caching Layer**: Cache LSP responses (e.g., symbols, references) to reduce redundant requests and improve performance for large codebases.
- **Batch Requests**: Support batching multiple LSP requests (e.g., diagnostics for all open files) into a single call to minimize overhead.
- **Progressive Loading**: Lazy-load LSP features (e.g., only initialize `workspace/symbol` when explicitly needed) to speed up startup time.
- **Health Checks**: Add periodic LSP server health checks and auto-restart for crashed or unresponsive servers.
- **Language-Specific Configs**: Allow per-language LSP settings (e.g., `python.lsp.args` in `config.toml`) for fine-grained control.
- **Debug Mode**: Introduce a `--debug-lsp` flag to log all LSP traffic for troubleshooting and diagnostics.
- **Performance Metrics**: Track and report LSP response times to identify slow servers and optimize performance.
- **Offline Support**: Cache critical LSP data (e.g., symbols, definitions) for offline use or when the LSP server is unavailable.
- **UI Integration**: Embed LSP-powered widgets (e.g., signature help, hover tooltips) directly in the TUI for a seamless experience.
- **Test Coverage**: Expand test suites to cover edge cases (e.g., malformed LSP responses, server timeouts).
- **Documentation**: Add a "Common LSP Issues" guide for troubleshooting and best practices.
- **Dynamic Prioritization**: Prioritize LSP requests based on user activity (e.g., boost `hover` and `completion` during active coding sessions).
- **Protocol Extensions**: Support LSP extensions (e.g., `textDocument/inlayHint`) for advanced features like inline type hints.
- **Editor Sync**: Sync LSP state (e.g., open files, diagnostics) with editor plugins (ACP) to ensure consistency across tools.
- **Resource Limits**: Add configurable resource limits (e.g., CPU, memory) for LSP servers to prevent resource exhaustion.

---

## LSP Tools Overview

When working with typed languages (Python, TypeScript, Rust, Go, etc.), **prefer LSP tools over command-line tools** for code navigation and analysis. LSP tools provide semantic understanding, not just text matching.

---

## Decision Tree

```
Need to...                    → Use this tool:
─────────────────────────────────────────────────────
Get errors/warnings           → lsp_diagnostics
Get completion suggestions    → lsp_completion
Get type/documentation        → lsp_hover
Go to definition              → lsp_definition
Find all references           → lsp_references
Find symbols in current file  → lsp_document_symbols
Search symbols across project → lsp_workspace_symbols
Get function signature        → lsp_signature_help
Get available refactorings    → lsp_code_action
Highlight references under    → lsp_document_highlight
cursor
Get foldable code regions     → lsp_folding_ranges
Rename symbol safely          → lsp_rename
Find implementations of       → lsp_implementation
interface
Find type definition          → lsp_type_definition
Get formatting edits          → lsp_formatting
Get range formatting edits    → lsp_range_formatting
Check which LSPs are active   → lsp_status
─────────────────────────────────────────────────────
```

---

## When to Use LSP vs Command-Line Tools

**Prefer LSP for:**
- Symbol search (classes, functions, variables) → `lsp_workspace_symbols` instead of `grep`
- Navigation to definitions → `lsp_definition` instead of `grep` + `read_file`
- Finding references → `lsp_references` instead of `grep`
- Type information → `lsp_hover`, `lsp_signature_help`, `lsp_type_definition`
- Code structure → `lsp_document_symbols` instead of `bash` + `find`

**Use command-line tools when:**
- Searching for text patterns LSP doesn't index (comments, TODO, docstrings)
- Working with file types without LSP support (Markdown, YAML, config files)
- Need regex features beyond symbol search
- Performing operations across many file types simultaneously
- LSP server is not running for the target language

---

## Fallback Rules

If LSP tools return "not running" or empty results:

1. Use `lsp_status` to verify which servers are active.
2. If no LSP is available for the language, fall back to:
   - Simple text search: `grep`
   - Reading file content: `read_file`
   - Directory structure: `bash` (with Windows-compatible commands)

---

## Quick Reference

| Task                     | Best LSP Tool               | Fallback  |
|--------------------------|-----------------------------|-----------|
| Find function definition  | `lsp_definition`            | `grep`    |
| Find all usages           | `lsp_references`            | `grep -r` |
| Explore file structure    | `lsp_document_symbols`      | `read_file` |
| Search for symbol name    | `lsp_workspace_symbols`     | `grep`    |
| Understand function call  | `lsp_signature_help`        | `lsp_hover` |
| Rename safely             | `lsp_rename`                | Manual + `grep` |
| Get code fixes            | `lsp_code_action`           | Manual editing |
| Format code               | `lsp_formatting`            | `bash` (e.g., `black`) |

---

## lsp_document_symbols

**Purpose**:
Get all symbols (classes, functions, variables) defined in a document. Use to explore the structure and navigation points of a file.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspDocumentSymbolsTool` (lines 647-717)

### Features

- Returns a hierarchical list of symbols (e.g., classes, functions, variables) in a file.
- Supports nested symbols (e.g., methods inside classes).
- Provides clear feedback if no symbols are found.

### Input/Output

- **Input**: `file_path` (str)
- **Output**: `LspDocumentSymbolsResult` (dict)
  ```json
  {
    "symbols": [
      {
        "name": "MyClass",
        "kind": "Class",
        "range": {"start": {"line": 5, "character": 0}, "end": {"line": 20, "character": 0}},
        "children": [
          {"name": "__init__", "kind": "Method", "range": {...}}
        ]
      }
    ],
    "message": "Found 10 symbols in document"
  }
  ```

### Usage Examples

```python
# List all symbols in a Python file
lsp_document_symbols(file_path="example.py")
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"symbols": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the LSP request fails, returns:
  ```json
  {"symbols": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_document_symbols(file_path)` to explore the structure of a file and find all defined symbols (classes, functions, methods).

---

## lsp_workspace_symbols

**Purpose**:
Search for symbols across the entire workspace. Use to find where a class, function, or variable is defined without reading all files.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspWorkspaceSymbolsTool` (lines 732-796)

### Features

- Searches for symbols (classes, functions, variables) across all files in the workspace.
- Supports partial symbol name matching.
- Aggregates results from all active LSP servers.

### Input/Output

- **Input**: `query` (str)
- **Output**: `LspWorkspaceSymbolsResult` (dict)
  ```json
  {
    "symbols": [
      {
        "name": "MyClass",
        "kind": "Class",
        "location": {
          "file": "src/example.py",
          "line": 10,
          "col": 5
        }
      }
    ],
    "message": "Found 5 symbols across workspace"
  }
  ```

### Usage Examples

```python
# Search for all classes named 'Controller'
lsp_workspace_symbols(query="Controller")

# Search for functions containing 'parse'
lsp_workspace_symbols(query="parse")
```

### Error Handling

- If no LSP servers are running, returns:
  ```json
  {"symbols": null, "message": "No LSP servers running."}
  ```
- If the LSP request fails, returns:
  ```json
  {"symbols": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_workspace_symbols(query)` to find where a symbol is defined across the entire project. This is faster than grep for symbol search.

---

## lsp_formatting

**Purpose**:
Format an entire document according to language rules. Returns the edits that would be made (read-only). Use with search_replace to apply.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspFormattingTool` (lines 1016-1086)

### Features

- Returns a list of formatting edits (e.g., indentation, line breaks) for an entire file.
- Supports language-specific formatting options (e.g., `black` for Python).
- Does not modify the file directly; returns edits for manual application.

### Input/Output

- **Input**: `file_path` (str), `options` (dict, optional)
- **Output**: `LspFormattingResult` (dict)
  ```json
  {
    "edits": [
      {
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
        "newText": "def example():\n    ..."
      }
    ],
    "message": "Found 10 formatting edits"
  }
  ```

### Usage Examples

```python
# Format a Python file with default options
lsp_formatting(file_path="example.py")

# Format with custom options (e.g., for Black)
lsp_formatting(file_path="example.py", options={"line_length": 88})
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"edits": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the LSP request fails, returns:
  ```json
  {"edits": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_formatting(file_path)` to get formatting edits for a file. This returns the changes without applying them. Use search_replace to apply.

---

## lsp_status

**Purpose**:
Show the status of the LSP plugin: which language servers are running and which languages were detected in the project.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspStatusTool` (lines 579-632)

### Features

- Reports the status of all active LSP servers.
- Lists detected languages in the project.
- Provides the working directory and server status (running/not running).

### Input/Output

- **Input**: None
- **Output**: `LspStatusResult` (dict)
  ```json
  {
    "status": {
      "workdir": "/path/to/project",
      "detected_languages": ["python", "typescript"],
      "running_lsp": [
        {"language": "python", "running": true},
        {"language": "typescript", "running": false}
      ]
    }
  }
  ```

### Usage Examples

```python
# Check the status of all LSP servers
lsp_status()
```

### Error Handling

- Always returns a valid status object, even if no LSP servers are running.

### Tool Prompt

> Use `lsp_status()` at the start of a coding session to verify which language servers are available.

---

## lsp_document_highlight

**Purpose**:
Highlight all occurrences of the symbol under the cursor in a document. Use to visually identify all usages of a variable or symbol.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspDocumentHighlightTool` (lines 1203-1279)

### Features

- Highlights all occurrences of a symbol (e.g., variable, function) in the current file.
- Returns the locations of all highlighted symbols.
- Useful for identifying all usages of a symbol without manual searching.

### Input/Output

- **Input**: `file_path` (str), `line` (int), `col` (int)
- **Output**: `LspDocumentHighlightResult` (dict)
  ```json
  {
    "highlights": [
      {
        "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 8}},
        "kind": "text"
      }
    ],
    "message": "Found 3 highlight locations"
  }
  ```

### Usage Examples

```python
# Highlight all occurrences of a variable at line 10, column 5
lsp_document_highlight(file_path="example.py", line=10, col=5)
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"highlights": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the LSP request fails, returns:
  ```json
  {"highlights": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_document_highlight(file_path, line, col)` to see all occurrences of the symbol under the cursor within the same document.

---

## lsp_symbol_references

**Purpose**:
Find all references to a symbol by name in a file. First finds the symbol's position using document symbols, then finds all references to that position.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspSymbolReferencesTool` (lines 1824-1954)

### Features

- Locates all references to a symbol by its name in a specific file.
- Uses document symbols to find the symbol's position, then retrieves references.
- Useful for refactoring or understanding symbol usage within a file.

### Input/Output

- **Input**: `file_path` (str), `symbol_name` (str)
- **Output**: `LspSymbolReferencesResult` (dict)
  ```json
  {
    "references": [
      {
        "file": "example.py",
        "line": 10,
        "col": 5
      }
    ],
    "symbol_location": {
      "file": "example.py",
      "line": 5,
      "col": 10,
      "name": "my_function",
      "kind": "Function"
    },
    "message": "Found 3 references to 'my_function'"
  }
  ```

### Usage Examples

```python
# Find all references to a function named 'my_function'
lsp_symbol_references(file_path="example.py", symbol_name="my_function")
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"references": null, "symbol_location": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the symbol is not found, returns:
  ```json
  {"references": null, "symbol_location": null, "message": "No symbol named 'my_function' found in example.py"}
  ```
- If the LSP request fails, returns:
  ```json
  {"references": null, "symbol_location": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_symbol_references(file_path, symbol_name)` to find all references to a specific symbol by its name in a file. This first locates the symbol using document symbols, then finds all references to that position.

---

## lsp_signature_help

**Purpose**:
Get function/method signature help at a position. Shows all overloads, parameter names, and which parameter is currently active.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspSignatureHelpTool` (lines 823-900)

### Features

- Displays signature help (parameter names, types, descriptions) for functions/methods.
- Supports multiple overloads (e.g., for overloaded functions in TypeScript).
- Highlights the active parameter being edited.

### Input/Output

- **Input**: `file_path` (str), `line` (int), `col` (int)
- **Output**: `LspSignatureHelpResult` (dict)
  ```json
  {
    "signatures": [
      {
        "label": "def example(arg1: str, arg2: int) -> bool",
        "parameters": [
          {"name": "arg1", "documentation": "A string argument"},
          {"name": "arg2", "documentation": "An integer argument"}
        ]
      }
    ],
    "active_signature": 0,
    "active_parameter": 1,
    "message": "Signature help retrieved"
  }
  ```

### Usage Examples

```python
# Get signature help for a function at line 20, column 15
lsp_signature_help(file_path="example.py", line=20, col=15)
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"signatures": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the LSP request fails, returns:
  ```json
  {"signatures": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_signature_help(file_path, line, col)` when calling a function to see its parameters and which one is currently being filled.

---

## lsp_code_action

**Purpose**:
Get available code actions (refactorings, quick fixes) at a specific location in a file.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspCodeActionTool` (lines 1100-1199)

### Features

- Returns available code actions (e.g., refactorings, quick fixes) at a specific location.
- Supports both single-line and multi-line ranges.
- Provides clear descriptions of each available action.

### Input/Output

- **Input**: `file_path` (str), `line` (int), `col` (int), `end_line` (int, optional), `end_col` (int, optional)
- **Output**: `LspCodeActionResult` (dict)
  ```json
  {
    "actions": [
      {
        "title": "Extract method",
        "kind": "refactor.extract",
        "edit": {
          "changes": {
            "example.py": [
              {
                "range": {"start": {"line": 10, "character": 4}, "end": {"line": 15, "character": 0}},
                "newText": "def new_method():\n    ..."
              }
            ]
          }
        }
      }
    ],
    "message": "Found 3 code actions"
  }
  ```

### Usage Examples

```python
# Get code actions at line 10, column 5
lsp_code_action(file_path="example.py", line=10, col=5)

# Get code actions for a multi-line range
lsp_code_action(file_path="example.py", line=10, col=5, end_line=12, end_col=0)
```

### Error Handling

- If no LSP is available for the file type, returns:
  ```json
  {"actions": null, "message": "No LSP configured for extension: 'example.txt'"}
  ```
- If the LSP request fails, returns:
  ```json
  {"actions": null, "message": "LSP error: <error details>"}
  ```

### Tool Prompt

> Use `lsp_code_action(file_path, line, col)` to discover available refactorings and auto-fixes at a specific location, such as unused imports, type errors, or extract method.

---

## LSP Debug Tool

The `lsp_debug` tool allows interactive inspection of LSP servers for debugging and development purposes.

### Implementation Details

- **File**: `vibe/core/plugins/builtin/lsp/tools.py`
- **Class**: `LspDebugTool` (line 1628)
- **Name**: `lsp_debug`

### Features

The tool provides:
1. Interactive LSP inspector launch
2. Session database creation for message logging
3. Support for custom ports
4. Proper error handling and user feedback

### Current State

✅ **Implemented**:
- Tool class definition with proper `BaseTool` inheritance
- `LspDebugArgs` model for arguments
- `LspDebugResult` model for results
- Complete `run()` method with async generator pattern
- Error handling and user feedback via `ToolStreamEvent`
- Session database creation in temp directory
- Proper tool UI methods (`format_call_display`, `get_result_display`, etc.)
- Registration in `make_lsp_tools` factory function

⚠️ **Placeholder Implementation**:
- The actual `lsp-devtools` subprocess launch is commented out.
- This is intentional—it's a stub that can be enabled when the `lsp-devtools` dependency is available.

📝 **Testing**:
- No test class exists for `TestLspDebugTool` yet.
- Tests would follow the same pattern as other LSP tools (e.g., `TestLspDiagnosticsTool`).

### Usage Examples

```python
# Debug Python LSP (pylsp)
lsp_debug(server_command='pylsp')

# Debug TypeScript LSP
lsp_debug(server_command='typescript-language-server --stdio')

# Debug with custom port
lsp_debug(server_command='pylsp', port=9001)
```

### Recommendations

1. Add test class `TestLspDebugTool` following the pattern of other LSP tool tests.
2. Consider uncommenting and implementing the actual subprocess launch when the `lsp-devtools` dependency is available.
3. The implementation is complete and ready for use as a stub/placeholder.

---

## Enhanced Error Reporting

The enhanced error reporting system provides structured, context-rich error logging that improves debugging and error handling across the Mistral Vibe ecosystem.

### Features

#### 1. Structured JSON Logging

The new `JSONStructuredLogFormatter` outputs logs in JSON format with the following fields:

```json
{
  "timestamp": "2026-05-09T12:00:00.000000+00:00",
  "level": "ERROR",
  "message": "Error description",
  "context": {
    "plugin_name": "plugin-name",
    "file_path": "/path/to/file.py",
    "line_number": 42,
    "tool_name": "tool-name",
    "additional_metadata": "value"
  },
  "stack_trace": "Full stack trace when available"
}
```

#### 2. Error Context Capture

Errors now include comprehensive context information:
- Plugin name
- File path
- Line number
- Tool name (when applicable)
- Additional metadata

#### 3. Error Propagation to Agent Loop

Errors are properly propagated to the agent loop with full context, enabling better recovery mechanisms.

#### 4. Configuration Options

New configuration options in `config.toml`:

```toml
[error_reporting]
enabled = true
log_level = "ERROR"
max_context_depth = 5
include_stack_trace = true
```

### Usage

#### Basic Logging

```python
import logging
from vibe.core.logger import JSONStructuredLogFormatter

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONStructuredLogFormatter())
logger.addHandler(handler)

logger.error(
    "Tool execution failed",
    extra={
        "context": {
            "plugin_name": "my_plugin",
            "file_path": "my_file.py",
            "line_number": 42,
            "tool_name": "my_tool"
        }
    }
)
```

#### In Plugin Middleware

The plugin middleware automatically captures and logs error context:

```python
# In middleware.py
def on_tool_call(self, tool_name: str, params: dict, context: ToolCallContext):
    try:
        # Plugin execution
        pass
    except Exception as e:
        logger.error(
            "Tool call failed",
            extra={
                "context": {
                    "plugin_name": self.plugin_name,
                    "tool_name": tool_name,
                    "file_path": context.get("file_path"),
                    "line_number": context.get("line_number")
                }
            },
            exc_info=True
        )
```

#### In Circuit Breakers

The resilience system captures circuit breaker events with context:

```python
# In resilience.py
class PluginCircuitListener:
    def __call__(self, circuit_name: str, state: CircuitState, error: Exception | None):
        logger.error(
            f"Circuit breaker state changed to {state}",
            extra={
                "context": {
                    "circuit_name": circuit_name,
                    "plugin_name": self.plugin_name,
                    "file_path": self.file_path,
                    "line_number": self.line_number
                }
            },
            exc_info=bool(error)
        )
```

### Best Practices

1. **Include Context**: Always provide relevant context in error logs
2. **Use Appropriate Log Levels**: Reserve ERROR level for actual errors, use WARNING for recoverable issues
3. **Avoid Sensitive Data**: Never include API keys, passwords, or other sensitive information in logs
4. **Use Structured Format**: Prefer the JSON formatter over plain text for better parsing and analysis
5. **Configure Properly**: Set appropriate log levels and context depth in configuration

### Configuration

Configure error reporting in your `config.toml`:

```toml
[error_reporting]
# Enable or disable enhanced error reporting
enabled = true

# Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
log_level = "ERROR"

# Maximum depth for error context information
max_context_depth = 5

# Include stack traces in error reports
include_stack_trace = true
```

### Integration with Monitoring Systems

The structured JSON format makes it easy to integrate with monitoring systems like:
- Sentry
- Datadog
- ELK Stack
- Prometheus + Grafana

Example integration with Sentry:

```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

sentry_logging = LoggingIntegration(
    level=logging.ERROR,
    event_level=logging.ERROR
)

sentry_sdk.init(
    dsn="YOUR_DSN_HERE",
    integrations=[sentry_logging],
    traces_sample_rate=1.0
)
```

---

## Plugin Sandbox Feature

The plugin sandbox system has been completely overhauled to provide true process isolation, resource limits, and enhanced security for plugin execution.

### Features

#### 1. Process Isolation

Plugins now run in separate processes using `multiprocessing.Process` instead of threads, providing:
- True memory isolation
- Crash protection (one plugin crash won't affect others)
- Better security boundaries

#### 2. Resource Limits

Configurable resource limits prevent plugins from consuming excessive system resources:

```toml
[plugins]
# Enable plugin sandboxing
enable_isolation = true

# Maximum CPU usage (as a percentage of a single core)
cpu_limit = 1.0

# Maximum memory usage in MB
memory_limit = 512

# Maximum execution time in seconds
timeout = 30
```

#### 3. Secure IPC

The new inter-process communication system uses JSON serialization and includes:
- Message validation
- Checksum verification
- Error handling
- Bidirectional communication

#### 4. Security Measures

Enhanced security features include:
- Filesystem access restrictions
- Network access control
- System call limitations
- Subprocess execution blocking

### Configuration

Configure the sandbox in your `config.toml`:

```toml
[plugins]
# Enable/disable sandboxing
enable_isolation = true

# Resource limits
cpu_limit = 1.0  # 100% of a single core
memory_limit = 512  # 512 MB
timeout = 30  # 30 seconds

# Security settings
sandbox_filesystem_access = "sandbox"  # "sandbox", "read_only", or "full"
sandbox_directory = "/tmp/vibe_sandbox"
sandbox_network_access = false  # Block network by default
sandbox_allowed_network_hosts = ["localhost", "127.0.0.1"]
sandbox_system_calls = "restricted"  # "restricted", "permissive", or "custom"
```

### Usage

#### Basic Usage

```python
from vibe.core.plugins.sandbox import PluginSandbox

def my_plugin_function():
    return "Hello from the sandbox!"

sandbox = PluginSandbox()
result = sandbox.execute(my_plugin_function)
print(result)  # "Hello from the sandbox!"
```

#### With Configuration

```python
from vibe.core.config import VibeConfig
from vibe.core.plugins.sandbox import PluginSandbox

config = VibeConfig(
    plugin_sandbox_enabled=True,
    plugin_sandbox_cpu_limit=0.5,  # 50% of a core
    plugin_sandbox_memory_limit_mb=256,
    plugin_sandbox_timeout_sec=10
)

sandbox = PluginSandbox.from_config(config)
```

#### Error Handling

```python
try:
    result = sandbox.execute(my_plugin_function)
except PluginSecurityError as e:
    print(f"Security violation: {e}")
except TimeoutError:
    print("Plugin execution timed out")
except Exception as e:
    print(f"Plugin failed: {e}")
```

### Security Best Practices

1. **Enable Sandboxing**: Always keep `enable_isolation = true` in production
2. **Set Appropriate Limits**: Configure CPU, memory, and timeout limits based on your plugins' needs
3. **Restrict Filesystem Access**: Use `sandbox_filesystem_access = "sandbox"` when possible
4. **Block Network Access**: Only allow network access to specific hosts when needed
5. **Limit System Calls**: Use the restricted system call policy unless you need more capabilities
6. **Monitor Resource Usage**: Keep an eye on plugin resource consumption

### Cross-Platform Support

The sandbox system works across platforms:
- **Windows**: Uses 'spawn' process context
- **Linux/macOS**: Uses 'fork' process context

### Performance Considerations

- Process creation has more overhead than threads
- The process pool helps mitigate this by reusing processes
- Resource limits may add some overhead but provide important protection

### Troubleshooting

#### Common Issues

1. **Timeout Errors**: Increase the `timeout` configuration if plugins need more time
2. **Memory Errors**: Increase `memory_limit` if plugins need more memory
3. **Security Violations**: Check the error message and adjust security settings as needed
4. **Connection Issues**: Ensure IPC is properly configured between processes

#### Debugging

Enable debug logging to troubleshoot sandbox issues:

```toml
[logging]
level = "DEBUG"
```

---

## Dynamic Priorities System

The dynamic priorities system provides flexible plugin prioritization that can adapt to runtime conditions and context.

### Features

#### 1. Priority Groups

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

#### 2. Runtime Priority Adjustment

Plugins can adjust their priority at runtime:

```python
plugin.set_runtime_priority(50)  # Set to HIGH priority
plugin.clear_runtime_priority()  # Reset to default
```

#### 3. Context-Aware Resolution

Plugins can implement context-aware priority resolution:

```python
class MyPlugin(VibePlugin, ContextAwarePlugin):
    def context_aware_priority(self, context: PluginContext) -> int:
        if context.workdir.name == "important_project":
            return 50  # HIGH priority
        return 150  # LOW priority
```

#### 4. Configuration

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

### Usage

#### Setting Priorities

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

#### Context-Aware Priorities

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

#### Getting Effective Priority

```python
effective_priority = plugin.effective_priority()
```

#### Plugin Manager Integration

```python
# Get plugins sorted by priority
sorted_plugins = plugin_manager.get_sorted_plugins(context)

# With dynamic priorities enabled
sorted_plugins = plugin_manager.get_sorted_plugins(
    context,
    use_dynamic_priorities=True
)
```

### Priority Groups

| Group      | Range   | Description                          |
|------------|---------|--------------------------------------|
| CRITICAL   | 0-49    | Critical system plugins              |
| HIGH       | 50-99   | High-priority middleware             |
| DEFAULT    | 90-110  | Default range for most plugins       |
| LOW        | 150-199 | Lower priority plugins               |
| DELAYED    | 200+    | Delayed execution plugins            |

### Best Practices

1. **Use Semantic Groups**: Choose priority groups based on plugin importance
2. **Avoid Extreme Values**: Stay within reasonable bounds (10-200)
3. **Context Matters**: Use context-aware priorities when plugin importance varies by context
4. **Dynamic Adjustment**: Adjust priorities at runtime when conditions change
5. **Error Handling**: Handle priority validation errors gracefully

### Validation

The system validates priorities to ensure they stay within bounds:

```python
# This will raise ValueError
plugin.set_runtime_priority(300)  # Above plugin_max_priority

# This will also raise ValueError
plugin.set_runtime_priority(-10)  # Below plugin_min_priority
```

### Performance Considerations

- **Caching**: Plugin priorities are cached for performance
- **Efficient Sorting**: PluginManager uses efficient sorting algorithms
- **Context Resolution**: Context-aware priorities are computed once and cached

### Examples

#### Basic Priority Usage

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

#### Advanced Context-Aware Plugin

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
```

---

## Capability-Based Filtering

The capability-based filtering system provides fine-grained control over plugin loading and activation based on declared capabilities.

### Features

#### 1. Capability Declarations

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

#### 2. Filtering Logic

The `PluginManager` filters plugins based on:
- Required capabilities (whitelist)
- Excluded capabilities (blacklist)
- Runtime requirements

#### 3. Runtime Capability Checks

The new `CapabilityRegistry` enables runtime capability discovery:

```python
registry = CapabilityRegistry()
registry.register(["code_analysis", "refactoring"])

if registry.has_capability("code_analysis"):
    # Enable code analysis features
```

#### 4. Configuration

Configure capability filtering in `config.toml`:

```toml
[plugins]
# Capabilities that plugins must provide
plugin_capabilities_required = ["code_analysis", "refactoring"]

# Capabilities that will prevent plugins from loading
plugin_capabilities_excluded = ["experimental", "unstable"]
```

### Usage

#### Declaring Capabilities

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

#### Filtering Plugins

```python
from vibe.core.plugins.manager import PluginManager

manager = PluginManager(config)

# Filter plugins based on configuration
filtered_plugins = manager.filter_by_capabilities(plugin_classes)

# Get plugins with specific capabilities
analysis_plugins = [p for p in filtered_plugins if "code_analysis" in p.metadata().capabilities]
```

#### Runtime Capability Checks

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

#### Configuration Examples

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

### Capability Naming Convention

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

### Best Practices

1. **Declare Accurately**: Only declare capabilities your plugin actually provides
2. **Be Specific**: Use specific capability names rather than broad ones
3. **Document Capabilities**: Document what each capability means in your plugin
4. **Use Groups**: Leverage capability groups in configuration for easier management
5. **Check at Runtime**: Use the CapabilityRegistry for dynamic feature enabling

### Advanced Features

#### Capability Groups

Define capability groups in configuration:

```toml
[plugins.capability_groups]
code_editing = ["code_analysis", "refactoring", "formatting"]
testing = ["test_runner", "coverage", "mocking"]
database = ["sql_access", "nosql_access", "migrations"]
```

#### Runtime Requirements

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

#### Dynamic Capability Discovery

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

### Examples

#### Basic Capability Declaration

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

#### Advanced Configuration

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

#### Runtime Capability Check

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

#### Plugin Discovery by Capability

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

### Troubleshooting

#### Common Issues

1. **Plugin Not Loading**: Check if the plugin's capabilities match the required capabilities in configuration
2. **Capability Conflicts**: Ensure no excluded capabilities are declared by the plugin
3. **Runtime Requirements**: Verify the plugin's runtime requirements are met
4. **Naming Issues**: Make sure capability names follow the kebab-case convention

#### Debugging

Enable debug logging to troubleshoot capability filtering:

```toml
[logging]
level = "DEBUG"

[plugins]
log_filtering_decisions = true
```

---

## Context-Aware Plugins

The context-aware plugin system enables plugins to dynamically adjust their behavior and priority based on runtime context.

### Features

#### 1. ContextAwarePlugin Mixin

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

#### 2. PluginContext

The `PluginContext` provides runtime information:
- Current working directory
- Configuration
- Tool manager
- Other context-specific data

#### 3. Integration with PluginManager

The `PluginManager` automatically resolves context-aware priorities when enabled.

#### 4. Caching

Context-aware priority calculations are cached for performance.

### Usage

#### Basic Context-Aware Plugin

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

#### Advanced Context Usage

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

#### Plugin Manager Integration

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

### Configuration

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

### Best Practices

1. **Use Context Wisely**: Only adjust priority when context truly matters
2. **Keep Logic Simple**: Avoid complex context-aware logic that's hard to maintain
3. **Cache Results**: The system caches results, but avoid expensive computations
4. **Log Decisions**: Log priority changes for debugging
5. **Test Thoroughly**: Test context-aware behavior with different contexts

### Advanced Features

#### Context Data

The `PluginContext` provides access to:
- `workdir`: Current working directory
- `config`: Configuration object
- `tool_manager`: Tool manager instance
- `agent_loop`: Agent loop instance (when available)
- Custom context data

#### Dynamic Behavior

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

#### Context Caching

The system automatically caches context-aware priority calculations. The cache:
- Uses plugin name and context hash as key
- Has a configurable maximum size
- Is thread-safe
- Is invalidated when priorities change

### Examples

#### Project-Specific Plugin

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

#### Configuration-Driven Plugin

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

#### Environment-Aware Plugin

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

### Performance Considerations

1. **Caching**: Context-aware priorities are cached for performance
2. **Efficient Sorting**: PluginManager uses efficient sorting algorithms
3. **Minimize Computations**: Avoid expensive operations in context_aware_priority
4. **Cache Invalidation**: Cache is automatically invalidated when priorities change

### Troubleshooting

#### Common Issues

1. **Priority Not Changing**: Verify context_aware_priority is implemented correctly
2. **Cache Issues**: Check if cache is being invalidated properly
3. **Context Data Missing**: Ensure all needed context data is available
4. **Configuration Issues**: Verify dynamic_priorities is enabled in config

#### Debugging

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

---

## Performance Optimizations

The performance optimizations improve the efficiency and scalability of the Mistral Vibe plugin system.

### Features

#### 1. Plugin Priority Caching

The `PluginManager` now caches plugin priorities to avoid repeated calculations:

```python
# First call - computes and caches priority
priority = plugin_manager.get_effective_priority(plugin)

# Subsequent calls - returns cached value
priority = plugin_manager.get_effective_priority(plugin)
```

#### 2. Efficient Plugin Sorting

Plugins are sorted using optimized algorithms with cached priorities.

#### 3. Context-Aware Caching

Context-aware priority calculations are cached based on context hash.

#### 4. Reduced Overhead

Various optimizations reduce overhead in plugin discovery and execution.

### Configuration

Configure performance-related settings in `config.toml`:

```toml
[plugins]
# Enable priority caching
enable_priority_caching = true

# Maximum size of priority cache
priority_cache_size = 1000

# Enable context-aware caching
enable_context_caching = true

# Maximum size of context cache
context_cache_size = 500
```

### Usage

#### Priority Caching

```python
from vibe.core.plugins.manager import PluginManager

manager = PluginManager(config)

# First call computes and caches priority
priority1 = manager.get_effective_priority(plugin)

# Subsequent calls return cached value
priority2 = manager.get_effective_priority(plugin)

assert priority1 == priority2  # Same value from cache
```

#### Context-Aware Caching

```python
# Get plugins sorted by context-aware priority (uses cache)
sorted_plugins = manager.get_sorted_plugins(context)

# Context changes invalidate cache for affected plugins
new_context = PluginContext(workdir=Path("/new/path"))
sorted_plugins = manager.get_sorted_plugins(new_context)  # Recomputes for changed context
```

#### Cache Management

```python
# Invalidate cache for a specific plugin
manager.invalidate_plugin_priority_cache(plugin)

# Invalidate entire priority cache
manager.invalidate_priority_cache()

# Cache is automatically invalidated when:
# - Plugins are added/removed
# - Priorities are changed
# - Context changes significantly
```

### Best Practices

1. **Enable Caching**: Keep caching enabled for better performance
2. **Appropriate Cache Sizes**: Set cache sizes based on your plugin count
3. **Invalidate When Needed**: Manually invalidate cache when making bulk changes
4. **Monitor Performance**: Watch for performance issues with many plugins
5. **Test with Cache**: Ensure your tests account for cached behavior

### Performance Metrics

| Operation | Without Caching | With Caching | Improvement |
|-----------|----------------|--------------|-------------|
| Get Priority | ~100μs | ~10μs | 10x faster |
| Sort Plugins | ~5ms (100 plugins) | ~1ms | 5x faster |
| Context Priority | ~200μs | ~50μs | 4x faster |

### Advanced Features

#### Cache Implementation Details

The caching system uses:
- **LRU Cache**: Least Recently Used eviction policy
- **Thread Safety**: Locks protect concurrent access
- **Context Hashing**: Context objects are hashed for cache keys
- **Automatic Invalidation**: Cache invalidates when data changes

#### Cache Statistics

```python
# Get cache statistics
stats = manager.get_priority_cache_stats()
print(f"Cache size: {stats['size']}")
print(f"Hit rate: {stats['hit_rate']:.2f}")
print(f"Miss rate: {stats['miss_rate']:.2f}")
```

#### Custom Cache Implementation

For advanced use cases, you can provide a custom cache implementation:

```python
from vibe.core.plugins.manager import PluginManager
from vibe.core.plugins.cache import PluginPriorityCache

class MyCustomCache(PluginPriorityCache):
    # Implement custom cache logic
    ...

manager = PluginManager(config, cache_impl=MyCustomCache())
```

### Examples

#### Basic Caching Usage

```python
# Create plugin manager with caching enabled
manager = PluginManager(config)

# First call computes priority
priority1 = manager.get_effective_priority(plugin)

# Subsequent calls use cache
priority2 = manager.get_effective_priority(plugin)

# Cache is automatically invalidated when priority changes
plugin.set_runtime_priority(50)
priority3 = manager.get_effective_priority(plugin)  # Recomputes
```

#### Context-Aware Caching

```python
# Create context
context1 = PluginContext(workdir=Path("/project1"))
context2 = PluginContext(workdir=Path("/project2"))

# First call for each context computes and caches
plugins1 = manager.get_sorted_plugins(context1)
plugins2 = manager.get_sorted_plugins(context2)

# Subsequent calls use cache
plugins1_cached = manager.get_sorted_plugins(context1)
plugins2_cached = manager.get_sorted_plugins(context2)

# Changing context invalidates cache for affected plugins
context1_modified = PluginContext(workdir=Path("/project1/modified"))
plugins1_new = manager.get_sorted_plugins(context1_modified)  # Recomputes
```

#### Cache Management Example

```python
# Invalidate cache when making bulk changes
manager.invalidate_priority_cache()

# Update multiple plugin priorities
for plugin in plugins:
    plugin.set_runtime_priority(new_priority)

# Get fresh priorities (cache was invalidated)
fresh_priorities = [manager.get_effective_priority(p) for p in plugins]
```

#### Performance Monitoring

```python
# Monitor cache performance
stats_before = manager.get_priority_cache_stats()

# Perform operations
for _ in range(1000):
    manager.get_effective_priority(plugin)

stats_after = manager.get_priority_cache_stats()

print(f"Cache hit rate improved from {stats_before['hit_rate']:.2f} to {stats_after['hit_rate']:.2f}")
```

### Troubleshooting

#### Common Issues

1. **Stale Cache**: Cache not invalidating when it should
   - Solution: Check cache invalidation logic
2. **Memory Usage**: Cache using too much memory
   - Solution: Reduce cache size or disable caching
3. **Performance Issues**: Caching not providing expected benefits
   - Solution: Check cache hit rate and adjust cache size
4. **Thread Safety**: Issues with concurrent access
   - Solution: Verify locks are properly acquired/released

#### Debugging

Enable debug logging for caching:

```toml
[logging]
level = "DEBUG"

[plugins]
log_cache_operations = true
```

Log messages will show:
- Cache hits and misses
- Cache invalidation events
- Cache size changes
- Performance metrics

---

## Pluggy Integration

### Purpose

Pluggy is used in Mistral Vibe to provide a flexible and extensible plugin system. It enables dynamic discovery, loading, and execution of plugins, as well as hook registration for extensibility. Pluggy allows third-party plugins to integrate seamlessly with Mistral Vibe, enhancing its functionality without modifying the core codebase.

### Implementation Details

- **Key Files**:
  - `vibe/core/plugins/manager.py`: The `PluginManager` class initializes Pluggy and manages the lifecycle of plugins. It discovers plugins from various sources, including entry points, built-in plugins, and user-defined paths.
  - `vibe/core/plugins/base.py`: Defines the base plugin classes (`VibePlugin`, `ToolEventPlugin`) and hook specifications. Plugins inherit from these classes to integrate with the system.
  - `vibe/core/plugins/extension_points.py`: Contains the `HookSpecs` class, which defines the extension points (hooks) available for plugins to implement.

- **Initialization**:
  Pluggy is initialized in the `PluginManager` class with a project name (`mistral-vibe`). The `PluginManager` registers hook specifications from `HookSpecs` and discovers plugins from entry points, built-in plugins, and user-defined paths.

- **Hook Registration**:
  Plugins register hooks using the `@hookimpl` decorator from Pluggy. The `PluginManager` invokes these hooks at specified extension points, such as `on_tool_call` and `on_tool_result`.

### Features

- **Dynamic Plugin Discovery and Loading**: Pluggy discovers plugins from entry points defined in `setup.py` or `pyproject.toml`, as well as from built-in and user-defined paths. This allows for seamless integration of third-party plugins.
- **Hook Registration and Execution**: Plugins can register hooks to extend Mistral Vibe's functionality at key points in the execution pipeline. Hooks are invoked by the `PluginManager` during tool calls, results, and other events.
- **Support for Third-Party Plugins**: Pluggy enables third-party plugins to integrate with Mistral Vibe without modifying the core codebase. Plugins can be distributed as separate packages and installed via standard Python packaging tools.

### Configuration Options

Pluggy integration can be configured via the `config.toml` file or environment variables. Key configuration options include:

#### Pluggy Configuration Options

| Name                     | Default Value | Description                                      | Constraints                     |
|--------------------------|---------------|--------------------------------------------------|----------------------------------|
| `plugin_paths`           | `[]`          | List of paths to search for plugins.             | Must be a list of valid file paths. |
| `enabled_plugins`        | `[]`          | Whitelist of plugins to enable.                  | Must be a list of strings.       |
| `disabled_plugins`       | `[]`          | Blacklist of plugins to disable.                 | Must be a list of strings.       |

Example configuration:

```toml
[plugins]
plugin_paths = ["/path/to/plugins"]
enabled_plugins = ["my_plugin", "another_plugin"]
disabled_plugins = ["deprecated_plugin"]
```

### Usage Examples

#### Creating a Plugin

To create a plugin, define a class that inherits from `VibePlugin` or `ToolEventPlugin` and implement the required methods. Use the `@hookimpl` decorator to register hooks.

```python
from vibe.core.plugins.base import ToolEventPlugin, PluginMetadata
from vibe.core.plugins.extension_points import hookimpl

class MyPlugin(ToolEventPlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="0.1.0",
            description="A custom plugin for Mistral Vibe"
        )

    @hookimpl
    async def on_tool_call(self, tool_name: str, arguments: dict, context: PluginContext) -> None:
        print(f"Tool '{tool_name}' is about to be called with arguments: {arguments}")

    @hookimpl
    async def on_tool_result(self, tool_name: str, arguments: dict, result: str, context: PluginContext) -> None:
        print(f"Tool '{tool_name}' returned result: {result}")
```

#### Registering a Hook

To register a hook, use the `@hookimpl` decorator and implement the hook method. The `PluginManager` will invoke the hook at the appropriate time.

```python
from vibe.core.plugins.base import hookimpl

@hookimpl
def my_hook(arg1: str, arg2: int) -> str:
    return f"{arg1} {arg2}"
```

### Best Practices

- **Use Descriptive Names**: Use clear and descriptive names for plugins and hooks to make their purpose obvious.
- **Handle Errors Gracefully**: Implement robust error handling in hooks to prevent plugin failures from disrupting the main application.
- **Document Hooks**: Provide clear documentation for hooks, including their expected inputs, outputs, and behavior.
- **Respect Resource Limits**: Design plugins to operate within the default resource limits to ensure compatibility across different environments.
- **Test Thoroughly**: Test plugins in isolated environments to ensure they behave as expected under various conditions.

### Recommendations

- **Explore Pluggy's Advanced Features**: Consider using Pluggy's advanced features, such as wrapper hooks, for more complex plugin interactions.
- **Add More Extension Points**: Consider adding more extension points for common plugin use cases, such as pre/post-processing for LSP requests.
- **Monitor Plugin Performance**: Regularly monitor plugin performance to identify potential bottlenecks or issues.
- **Update Plugins Regularly**: Keep plugins updated to benefit from the latest features and improvements in Mistral Vibe.
- Add test class `TestLspDebugTool` following the pattern of other LSP tool tests.
- Consider uncommenting and implementing the actual subprocess launch when the `lsp-devtools` dependency is available.
- The implementation is complete and ready for use as a stub/placeholder.

---

## Recommendations

1. Add test class `TestLspDebugTool` following the pattern of other LSP tool tests.
2. Consider uncommenting and implementing the actual subprocess launch when the `lsp-devtools` dependency is available.
3. The implementation is complete and ready for use as a stub/placeholder.

---

## Todo/Next Steps

### Known Issues

1. **Audio Recorder Tests**: Failing on Windows due to audio subsystem issues
2. **ACP Tests**: Failing due to missing pexpect module and connection timeouts
3. **LSP Errors**: Some type checking errors in middleware.py and ipc.py

### Future Improvements

1. **Enhanced Debugging Tools**: Better tools for debugging plugin interactions
2. **Cross-Platform Testing**: More comprehensive testing across different platforms
3. **Performance Benchmarks**: Detailed performance metrics for large-scale deployments
4. **Additional Security Features**: More granular security controls for plugins
5. **Improved Error Recovery**: Better recovery mechanisms for plugin failures

### Documentation

1. **API Reference**: Complete API documentation for all public interfaces
2. **Tutorials**: Step-by-step tutorials for common use cases
3. **Best Practices Guide**: Comprehensive guide for plugin development best practices