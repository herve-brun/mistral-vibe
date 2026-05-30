"""Test plugin middleware reset functionality with log level filtering."""

import logging
from unittest.mock import Mock
import pytest
from vibe.core.plugins.middleware import PluginMiddleware
from vibe.core.plugins.base import ToolEventPlugin, PluginMetadata, PluginContext


class TestPlugin(ToolEventPlugin):
    """Test plugin that can simulate different reset behaviors."""
    
    def __init__(self, reset_behavior: str = "success"):
        self.reset_behavior = reset_behavior
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(name="test-plugin", version="1.0.0", description="Test plugin")
    
    async def setup(self, context: PluginContext) -> None:
        pass
    
    async def teardown(self) -> None:
        pass
    
    def reset(self, reset_reason: str = "stop") -> None:
        if self.reset_behavior == "critical_error":
            raise RuntimeError("Critical reset error")
        elif self.reset_behavior == "non_critical_error":
            raise TimeoutError("Non-critical timeout error")
        elif self.reset_behavior == "success":
            pass  # Success case
        else:
            raise ValueError(f"Unknown reset behavior: {self.reset_behavior}")


class TestPluginMiddlewareReset:
    """Test suite for PluginMiddleware reset functionality."""
    
    def test_determine_error_log_level_critical_errors(self):
        """Test that critical errors are classified as ERROR level."""
        middleware = PluginMiddleware.__new__(PluginMiddleware)
        
        critical_errors = [
            RuntimeError("Critical error"),
            MemoryError("Memory error"),
            RecursionError("Recursion error"),
            SystemError("System error"),
            KeyboardInterrupt("Keyboard interrupt"),
        ]
        
        for error in critical_errors:
            level = middleware._determine_error_log_level(error)
            assert level == "ERROR", f"Expected ERROR for {type(error).__name__}, got {level}"
    
    def test_determine_error_log_level_non_critical_errors(self):
        """Test that non-critical errors are classified as WARNING level."""
        middleware = PluginMiddleware.__new__(PluginMiddleware)
        
        non_critical_errors = [
            TimeoutError("Timeout error"),
            ConnectionError("Connection error"),
            FileNotFoundError("File not found"),
            PermissionError("Permission error"),
            OSError("OS error"),
            ValueError("Value error"),
            TypeError("Type error"),
            AttributeError("Attribute error"),
        ]
        
        for error in non_critical_errors:
            level = middleware._determine_error_log_level(error)
            assert level == "WARNING", f"Expected WARNING for {type(error).__name__}, got {level}"
    
    def test_determine_error_log_level_unknown_errors(self):
        """Test that unknown error types default to ERROR level."""
        middleware = PluginMiddleware.__new__(PluginMiddleware)
        
        class CustomError(Exception):
            pass
        
        error = CustomError("Custom error")
        level = middleware._determine_error_log_level(error)
        assert level == "ERROR", f"Expected ERROR for unknown error type, got {level}"
    
    def test_should_log_error_filtering(self):
        """Test log level filtering logic."""
        middleware = PluginMiddleware.__new__(PluginMiddleware)
        
        # Test cases: (error_level, reset_log_level, expected_result)
        test_cases = [
            ("WARNING", "WARNING", True),   # WARNING >= WARNING = True
            ("WARNING", "ERROR", False),    # WARNING >= ERROR = False
            ("ERROR", "WARNING", True),     # ERROR >= WARNING = True
            ("DEBUG", "WARNING", False),    # DEBUG >= WARNING = False
            ("INFO", "WARNING", False),     # INFO >= WARNING = False
            ("CRITICAL", "WARNING", True),  # CRITICAL >= WARNING = True
            ("ERROR", "ERROR", True),       # ERROR >= ERROR = True
            ("DEBUG", "DEBUG", True),       # DEBUG >= DEBUG = True
        ]
        
        for error_level, reset_level, expected in test_cases:
            result = middleware._should_log_error(error_level, reset_level)
            assert result == expected, f"Expected {expected} for {error_level} >= {reset_level}, got {result}"
    
    def test_reset_with_log_level_filtering(self, caplog):
        """Test that reset errors are filtered based on configured log level."""
        # Create mock config
        mock_config = Mock()
        mock_config.plugin_reset_log_level = "WARNING"
        
        # Create mock plugin manager
        plugin_manager = Mock()
        plugin_manager._config = mock_config
        
        # Create test plugins
        critical_error_plugin = TestPlugin("critical_error")
        non_critical_error_plugin = TestPlugin("non_critical_error")
        success_plugin = TestPlugin("success")
        
        plugin_manager.tool_event_plugins = [
            critical_error_plugin,
            non_critical_error_plugin,
            success_plugin
        ]
        
        # Create mock context
        mock_context = Mock(spec=PluginContext)
        
        # Create middleware
        middleware = PluginMiddleware(plugin_manager, mock_context)
        
        # Test with WARNING log level
        with caplog.at_level(logging.DEBUG):
            # Reset all plugins
            middleware.reset("test_reset")
            
            # Check that critical error was logged
            critical_error_logs = [
                record for record in caplog.records 
                if "Critical reset error" in record.message and record.levelname == "ERROR"
            ]
            assert len(critical_error_logs) > 0, "Critical error should be logged at ERROR level"
            
            # Check that non-critical error was suppressed or logged at DEBUG
            non_critical_logs = [
                record for record in caplog.records 
                if "Non-critical timeout error" in record.message
            ]
            
            # The non-critical error should either be suppressed or logged at DEBUG level
            debug_logs = [record for record in non_critical_logs if record.levelname == "DEBUG"]
            error_logs = [record for record in non_critical_logs if record.levelname == "ERROR"]
            
            assert len(debug_logs) > 0 or len(error_logs) == 0, "Non-critical error should be suppressed or logged at DEBUG"
    
    def test_reset_with_error_log_level(self, caplog):
        """Test reset behavior with ERROR log level."""
        # Create mock config
        mock_config = Mock()
        mock_config.plugin_reset_log_level = "ERROR"
        
        # Create mock plugin manager
        plugin_manager = Mock()
        plugin_manager._config = mock_config
        
        # Create test plugins
        critical_error_plugin = TestPlugin("critical_error")
        non_critical_error_plugin = TestPlugin("non_critical_error")
        
        plugin_manager.tool_event_plugins = [
            critical_error_plugin,
            non_critical_error_plugin
        ]
        
        # Create mock context
        mock_context = Mock(spec=PluginContext)
        
        # Create middleware
        middleware = PluginMiddleware(plugin_manager, mock_context)
        
        # Test with ERROR log level
        with caplog.at_level(logging.DEBUG):
            # Reset all plugins
            middleware.reset("test_reset")
            
            # Check that critical error was logged
            critical_error_logs = [
                record for record in caplog.records 
                if "Critical reset error" in record.message and record.levelname == "ERROR"
            ]
            assert len(critical_error_logs) > 0, "Critical error should be logged at ERROR level"
            
            # Check that non-critical error was suppressed
            non_critical_logs = [
                record for record in caplog.records 
                if "Non-critical timeout error" in record.message and record.levelname == "ERROR"
            ]
            assert len(non_critical_logs) == 0, "Non-critical error should be suppressed at ERROR log level"