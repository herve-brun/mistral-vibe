# Enhanced Error Reporting

The enhanced error reporting system provides structured, context-rich error logging that improves debugging and error handling across the Mistral Vibe ecosystem.

## Features

### 1. Structured JSON Logging

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

### 2. Error Context Capture

Errors now include comprehensive context information:
- Plugin name
- File path
- Line number
- Tool name (when applicable)
- Additional metadata

### 3. Error Propagation to Agent Loop

Errors are properly propagated to the agent loop with full context, enabling better recovery mechanisms.

### 4. Configuration Options

New configuration options in `config.toml`:

```toml
[error_reporting]
enabled = true
log_level = "ERROR"
max_context_depth = 5
include_stack_trace = true
```

## Usage

### Basic Logging

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

### In Plugin Middleware

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

### In Circuit Breakers

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

## Best Practices

1. **Include Context**: Always provide relevant context in error logs
2. **Use Appropriate Log Levels**: Reserve ERROR level for actual errors, use WARNING for recoverable issues
3. **Avoid Sensitive Data**: Never include API keys, passwords, or other sensitive information in logs
4. **Use Structured Format**: Prefer the JSON formatter over plain text for better parsing and analysis
5. **Configure Properly**: Set appropriate log levels and context depth in configuration

## Configuration

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

## Integration with Monitoring Systems

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