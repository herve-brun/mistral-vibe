"""Test the Plugin Isolation and Sandboxing implementation."""

import pytest
from vibe.core.plugins.sandbox import PluginSandbox


def test_plugin_sandbox_initialization():
    """Test that the PluginSandbox can be initialized with resource limits."""
    sandbox = PluginSandbox(timeout=10, memory_limit_mb=200, cpu_limit=2.0)
    
    assert sandbox.timeout == 10
    assert sandbox.memory_limit_mb == 200
    assert sandbox.cpu_limit == 2.0


def test_plugin_sandbox_default_values():
    """Test that the PluginSandbox has sensible default values."""
    sandbox = PluginSandbox()
    
    assert sandbox.timeout == 10
    assert sandbox.memory_limit_mb == 100
    assert sandbox.cpu_limit == 1.0


def test_plugin_sandbox_from_config():
    """Test creating a PluginSandbox from configuration."""
    # Create a mock config object
    class MockConfig:
        plugin_sandbox_timeout_sec = 15
        plugin_sandbox_memory_limit_mb = 256
        plugin_sandbox_cpu_limit = 1.5
    
    config = MockConfig()
    sandbox = PluginSandbox().from_config(config)
    
    assert sandbox.timeout == 15
    assert sandbox.memory_limit_mb == 256
    assert sandbox.cpu_limit == 1.5


def test_plugin_sandbox_from_config_defaults():
    """Test creating a PluginSandbox from configuration with missing values."""
    # Create a mock config object with missing values
    class MockConfig:
        pass
    
    config = MockConfig()
    sandbox = PluginSandbox().from_config(config)
    
    # Should use defaults
    assert sandbox.timeout == 10
    assert sandbox.memory_limit_mb == 100
    assert sandbox.cpu_limit == 1.0


def test_plugin_sandbox_context_creation():
    """Test that the PluginSandbox creates the appropriate multiprocessing context."""
    import platform
    
    sandbox = PluginSandbox()
    
    # Check that context is created
    assert hasattr(sandbox, 'context')
    assert sandbox.context is not None
    
    # On Windows, should use 'spawn' context
    if platform.system() == 'Windows':
        # The spawn context should be used
        assert sandbox.context.get_start_method() == 'spawn'
    else:
        # On Unix, should use default context
        assert sandbox.context.get_start_method() in ['fork', 'spawn']


def test_plugin_sandbox_worker_function_signature():
    """Test that the worker function has the correct signature for resource limits."""
    import inspect
    
    sandbox = PluginSandbox()
    worker_func = sandbox._worker_function
    
    # Check the function signature
    sig = inspect.signature(worker_func)
    params = list(sig.parameters.keys())
    
    # Should have parameters for resource limits
    assert 'memory_limit_mb' in params
    assert 'cpu_limit' in params
    
    # Should have other expected parameters
    assert 'func' in params
    assert 'args' in params
    assert 'kwargs' in params
    assert 'result_queue' in params