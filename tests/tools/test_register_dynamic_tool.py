"""Tests for ToolManager.register_dynamic_tool method."""

from unittest.mock import MagicMock
import pytest

from vibe.core.tools.base import BaseTool, BaseToolConfig
from vibe.core.tools.manager import ToolManager
from tests.conftest import build_test_vibe_config


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    @classmethod
    def get_name(cls) -> str:
        return "mock_tool"


class AnotherMockTool(BaseTool):
    """Another mock tool for testing."""
    
    @classmethod
    def get_name(cls) -> str:
        return "another_mock_tool"


class DuplicateMockTool(BaseTool):
    """Mock tool with same name as MockTool for testing overwrites."""
    
    @classmethod
    def get_name(cls) -> str:
        return "mock_tool"


@pytest.fixture
def config():
    return build_test_vibe_config(
        system_prompt_id="tests", include_project_context=False
    )


@pytest.fixture
def tool_manager(config):
    return ToolManager(lambda: config)


class TestRegisterDynamicTool:
    """Tests for ToolManager.register_dynamic_tool method."""

    def test_register_new_tool(self, tool_manager):
        """Test registering a new tool."""
        tool_manager.register_dynamic_tool(MockTool, "test_plugin")
        
        assert "mock_tool" in tool_manager._available
        assert tool_manager._available["mock_tool"] is MockTool
        assert "mock_tool" in tool_manager._plugin_tools
        assert tool_manager.get_plugin_for_tool("mock_tool") == "test_plugin"

    def test_register_tool_without_plugin_name(self, tool_manager):
        """Test registering a tool without specifying plugin name."""
        tool_manager.register_dynamic_tool(AnotherMockTool)
        
        assert "another_mock_tool" in tool_manager._available
        assert tool_manager._available["another_mock_tool"] is AnotherMockTool
        assert "another_mock_tool" in tool_manager._plugin_tools
        assert tool_manager.get_plugin_for_tool("another_mock_tool") is None

    def test_register_duplicate_tool_without_overwrite(self, tool_manager, caplog):
        """Test that registering a duplicate tool without overwrite logs warning and skips."""
        # Register first tool
        tool_manager.register_dynamic_tool(MockTool, "test_plugin")
        
        # Try to register duplicate without overwrite
        tool_manager.register_dynamic_tool(DuplicateMockTool, "test_plugin2")
        
        # Should still have original tool
        assert tool_manager._available["mock_tool"] is MockTool
        assert tool_manager.get_plugin_for_tool("mock_tool") == "test_plugin"
        
        # Check warning was logged
        assert "Tool 'mock_tool' already registered, skipping" in caplog.text

    def test_register_duplicate_tool_with_overwrite(self, tool_manager, caplog):
        """Test that registering a duplicate tool with overwrite replaces the tool."""
        # Register first tool
        tool_manager.register_dynamic_tool(MockTool, "test_plugin")
        
        # Register duplicate with overwrite=True
        tool_manager.register_dynamic_tool(DuplicateMockTool, "test_plugin2", overwrite=True)
        
        # Should have new tool
        assert tool_manager._available["mock_tool"] is DuplicateMockTool
        assert tool_manager.get_plugin_for_tool("mock_tool") == "test_plugin2"
        
        # Check debug log for overwrite
        assert "Overwriting existing tool 'mock_tool'" in caplog.text

    def test_register_duplicate_tool_with_overwrite_false(self, tool_manager, caplog):
        """Test that explicitly setting overwrite=False behaves like default."""
        # Register first tool
        tool_manager.register_dynamic_tool(MockTool, "test_plugin")
        
        # Try to register duplicate with explicit overwrite=False
        tool_manager.register_dynamic_tool(DuplicateMockTool, "test_plugin2", overwrite=False)
        
        # Should still have original tool
        assert tool_manager._available["mock_tool"] is MockTool
        assert tool_manager.get_plugin_for_tool("mock_tool") == "test_plugin"
        
        # Check warning was logged
        assert "Tool 'mock_tool' already registered, skipping" in caplog.text

    def test_invalid_tool_class_raises_type_error(self, tool_manager):
        """Test that registering a non-Tool class raises TypeError."""
        with pytest.raises(TypeError, match="is not a valid tool class"):
            tool_manager.register_dynamic_tool(str, "test_plugin")

    def test_base_tool_class_raises_type_error(self, tool_manager):
        """Test that registering BaseTool directly raises TypeError."""
        with pytest.raises(TypeError, match="is not a valid tool class"):
            tool_manager.register_dynamic_tool(BaseTool, "test_plugin")