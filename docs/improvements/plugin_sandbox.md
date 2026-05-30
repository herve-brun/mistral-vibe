# Plugin Sandbox Improvements

The plugin sandbox system has been completely overhauled to provide true process isolation, resource limits, and enhanced security for plugin execution.

## Features

### 1. Process Isolation

Plugins now run in separate processes using `multiprocessing.Process` instead of threads, providing:
- True memory isolation
- Crash protection (one plugin crash won't affect others)
- Better security boundaries

### 2. Resource Limits

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

### 3. Secure IPC

The new inter-process communication system uses JSON serialization and includes:
- Message validation
- Checksum verification
- Error handling
- Bidirectional communication

### 4. Security Measures

Enhanced security features include:
- Filesystem access restrictions
- Network access control
- System call limitations
- Subprocess execution blocking

## Configuration

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

## Usage

### Basic Usage

```python
from vibe.core.plugins.sandbox import PluginSandbox

def my_plugin_function():
    return "Hello from the sandbox!"

sandbox = PluginSandbox()
result = sandbox.execute(my_plugin_function)
print(result)  # "Hello from the sandbox!"
```

### With Configuration

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

### Error Handling

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

## Security Best Practices

1. **Enable Sandboxing**: Always keep `enable_isolation = true` in production
2. **Set Appropriate Limits**: Configure CPU, memory, and timeout limits based on your plugins' needs
3. **Restrict Filesystem Access**: Use `sandbox_filesystem_access = "sandbox"` when possible
4. **Block Network Access**: Only allow network access to specific hosts when needed
5. **Limit System Calls**: Use the restricted system call policy unless you need more capabilities
6. **Monitor Resource Usage**: Keep an eye on plugin resource consumption

## Cross-Platform Support

The sandbox system works across platforms:
- **Windows**: Uses 'spawn' process context
- **Linux/macOS**: Uses 'fork' process context

## Performance Considerations

- Process creation has more overhead than threads
- The process pool helps mitigate this by reusing processes
- Resource limits may add some overhead but provide important protection

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase the `timeout` configuration if plugins need more time
2. **Memory Errors**: Increase `memory_limit` if plugins need more memory
3. **Security Violations**: Check the error message and adjust security settings as needed
4. **Connection Issues**: Ensure IPC is properly configured between processes

### Debugging

Enable debug logging to troubleshoot sandbox issues:

```toml
[logging]
level = "DEBUG"
```