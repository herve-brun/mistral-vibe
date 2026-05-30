# Mistral Vibe Changelog

## [Unreleased] - 2026-05-09

### 🚀 Major Improvements

#### Enhanced Error Reporting System
- **Structured JSON Logging**: New `JSONStructuredLogFormatter` for consistent, machine-readable logs
- **Error Context Capture**: Automatic inclusion of plugin name, file path, line number, and tool name
- **Error Propagation**: Improved error handling and propagation to agent loop
- **Configuration Options**: New error reporting settings in `config.toml`
- **Integration**: Seamless integration with monitoring systems like Sentry, Datadog

#### Plugin Sandbox Security
- **Process Isolation**: True process isolation using `multiprocessing.Process` instead of threads
- **Resource Limits**: Configurable CPU, memory, and execution time limits
- **Secure IPC**: JSON-based inter-process communication with message validation
- **Security Measures**: Filesystem access restrictions, network controls, and system call limitations
- **Cross-Platform Support**: Works on Windows, Linux, and macOS

#### Dynamic Priorities System
- **Priority Groups**: Semantic priority ranges (CRITICAL, HIGH, DEFAULT, LOW, DELAYED)
- **Runtime Adjustment**: Plugins can adjust priority at runtime with bounds checking
- **Context-Aware Resolution**: Priorities can adapt based on runtime context
- **Validation**: Priority range validation with clear error messages
- **Caching**: Efficient caching of priority calculations

#### Capability-Based Filtering
- **Capability Declarations**: Plugins declare capabilities in metadata
- **Filtering Logic**: PluginManager filters based on required/excluded capabilities
- **Runtime Requirements**: Validation of Python version, platform, and other requirements
- **Capability Registry**: New `CapabilityRegistry` class for runtime capability checks
- **Configuration**: Fine-grained control via `config.toml`

#### Context-Aware Plugins
- **ContextAwarePlugin Mixin**: Standard interface for context-aware behavior
- **PluginContext**: Runtime context information including workdir, config, and tool manager
- **Integration**: Automatic context-aware priority resolution in PluginManager
- **Caching**: Context-aware calculations are cached for performance

#### Performance Optimizations
- **Priority Caching**: LRU cache for plugin priorities with thread safety
- **Efficient Sorting**: Optimized plugin sorting algorithms
- **Context-Aware Caching**: Cache based on context hash
- **Reduced Overhead**: Various optimizations for plugin discovery and execution

### 🔧 Configuration Changes

New configuration options in `config.toml`:

```toml
[error_reporting]
enabled = true
log_level = "ERROR"
max_context_depth = 5
include_stack_trace = true

[plugins]
enable_isolation = true
cpu_limit = 1.0
memory_limit = 512
timeout = 30
sandbox_filesystem_access = "sandbox"
sandbox_directory = "/tmp/vibe_sandbox"
sandbox_network_access = false
dynamic_priorities = true
plugin_error_penalty = 10
plugin_usage_boost = 5
plugin_min_priority = 10
plugin_max_priority = 200
plugin_capabilities_required = []
plugin_capabilities_excluded = []

[plugins.capability_groups]
# Define capability groups for easier configuration
```

### 🐛 Bug Fixes

- Fixed priority validation in PluginMetadata
- Improved error handling in plugin middleware
- Enhanced security error messages in PluginSandbox
- Fixed context propagation in dynamic priorities

### 📚 Documentation

- Comprehensive documentation for all new features
- Updated LSP.md with all improvements
- Added examples and best practices
- Created API reference for new interfaces

### 🧪 Testing

- 525 tests passing (96.2%)
- Core plugin system tests all passing
- Added comprehensive test coverage for new features

### 🔄 Deprecations

- Old thread-based sandbox (replaced with process isolation)
- Basic priority system (enhanced with dynamic priorities)

## 📋 Todo/Next Steps

### Known Issues

1. **Audio Recorder Tests**: Failing on Windows due to audio subsystem issues
2. **ACP Tests**: Failing due to missing pexpect module and connection timeouts

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

## 🤝 Contributing

We welcome contributions to Mistral Vibe! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to:
- Report issues
- Submit pull requests
- Suggest new features
- Improve documentation

## 📌 Versioning

Mistral Vibe follows [Semantic Versioning](https://semver.org/) for all releases.

## 📄 License

Mistral Vibe is released under the [Apache License 2.0](LICENSE).