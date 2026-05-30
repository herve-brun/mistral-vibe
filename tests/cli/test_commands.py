from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from vibe.cli.commands import Command, CommandRegistry


class TestCommandRegistry:
    def test_get_command_name_returns_canonical_name_for_alias(self) -> None:
        registry = CommandRegistry()
        assert registry.get_command_name("/help") == "help"
        assert registry.get_command_name("/config") == "config"
        assert registry.get_command_name("/model") == "model"
        assert registry.get_command_name("/connectors") == "mcp"
        assert registry.get_command_name("/clear") == "clear"
        assert registry.get_command_name("/exit") == "exit"
        assert registry.get_command_name("/data-retention") == "data-retention"

    def test_get_command_name_normalizes_input(self) -> None:
        registry = CommandRegistry()
        assert registry.get_command_name("  /help  ") == "help"
        assert registry.get_command_name("/HELP") == "help"

    def test_get_command_name_returns_none_for_unknown(self) -> None:
        registry = CommandRegistry()
        assert registry.get_command_name("/unknown") is None
        assert registry.get_command_name("hello") is None
        assert registry.get_command_name("") is None

    def test_parse_command_returns_command_when_alias_matches(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/help")
        assert result is not None
        cmd_name, cmd, cmd_args = result
        assert cmd_name == "help"
        assert cmd.handler == "_show_help"
        assert isinstance(cmd, Command)
        assert cmd_args == ""

    def test_parse_command_returns_none_when_no_match(self) -> None:
        registry = CommandRegistry()
        assert registry.parse_command("/nonexistent") is None

    def test_parse_command_uses_get_command_name(self) -> None:
        """parse_command and get_command_name stay in sync for same input."""
        registry = CommandRegistry()
        for alias in ["/help", "/config", "/clear", "/exit"]:
            cmd_name = registry.get_command_name(alias)
            result = registry.parse_command(alias)
            if cmd_name is None:
                assert result is None
            else:
                assert result is not None
                found_name, found_cmd, _ = result
                assert found_name == cmd_name
                assert registry.commands[cmd_name] is found_cmd

    def test_excluded_commands_not_in_registry(self) -> None:
        registry = CommandRegistry(excluded_commands=["exit"])
        assert registry.get_command_name("/exit") is None
        assert registry.parse_command("/exit") is None
        assert registry.get_command_name("/help") == "help"

    def test_resume_command_registration(self) -> None:
        registry = CommandRegistry()
        assert registry.get_command_name("/resume") == "resume"
        assert registry.get_command_name("/continue") == "resume"
        result = registry.parse_command("/resume")
        assert result is not None
        _, cmd, _ = result
        assert cmd.handler == "_show_session_picker"

    def test_parse_command_keeps_args_for_no_arg_commands(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/help extra")
        assert result == ("help", registry.commands["help"], "extra")

    def test_parse_command_keeps_args_for_argument_commands(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/mcp filesystem")
        assert result == ("mcp", registry.commands["mcp"], "filesystem")

    def test_parse_command_maps_connector_alias_to_mcp(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/connectors filesystem")
        assert result == ("mcp", registry.commands["mcp"], "filesystem")

    def test_data_retention_command_registration(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/data-retention")
        assert result is not None
        _, cmd, _ = result
        assert cmd.handler == "_show_data_retention"

    def test_adjust_priority_command_registration(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/adjust-priority")
        assert result is not None
        _, cmd, _ = result
        assert cmd.handler == "_adjust_plugin_priority"

    def test_adjust_priority_command_parses_arguments(self) -> None:
        registry = CommandRegistry()
        result = registry.parse_command("/adjust-priority my_plugin 100")
        assert result is not None
        _, cmd, cmd_args = result
        assert cmd.handler == "_adjust_plugin_priority"
        assert cmd_args == "my_plugin 100"

    def test_adjust_priority_command_handler_exists(self) -> None:
        """Test that the handler method exists in the VibeApp class."""
        from vibe.cli.textual_ui.app import VibeApp
        
        # Check that the handler method exists
        assert hasattr(VibeApp, "_adjust_plugin_priority")
        handler_method = getattr(VibeApp, "_adjust_plugin_priority")
        
        # Check that it's a callable method
        import inspect
        assert callable(handler_method)
        assert inspect.iscoroutinefunction(handler_method)

    @patch("vibe.cli.textual_ui.app.UserCommandMessage")
    async def test_adjust_priority_handler_parses_args_correctly(self, mock_message_class) -> None:
        """Test that the handler correctly parses arguments and calls agent loop."""
        from vibe.cli.textual_ui.app import VibeApp
        
        # Create a mock app instance with agent_loop attribute
        mock_app = MagicMock(spec=VibeApp)
        mock_agent_loop = MagicMock()
        mock_agent_loop.adjust_plugin_priority = MagicMock(return_value=True)
        mock_app.agent_loop = mock_agent_loop
        mock_app._mount_and_scroll = AsyncMock()
        
        # Call the handler method
        await VibeApp._adjust_plugin_priority(mock_app, "test_plugin 50")
        
        # Verify the agent loop method was called correctly
        mock_agent_loop.adjust_plugin_priority.assert_called_once_with("test_plugin", 50)
        
        # Verify success message was mounted
        mock_app._mount_and_scroll.assert_called_once()
        
        # Check that UserCommandMessage was called with the right arguments
        mock_message_class.assert_called_once()
        message_call_args = mock_message_class.call_args[0][0]
        assert "Success" in message_call_args
        assert "test_plugin" in message_call_args
        assert "50" in message_call_args

    @patch("vibe.cli.textual_ui.app.UserCommandMessage")
    async def test_adjust_priority_handler_handles_invalid_args(self, mock_message_class) -> None:
        """Test that the handler handles invalid arguments correctly."""
        from vibe.cli.textual_ui.app import VibeApp
        
        # Create a mock app instance
        mock_app = MagicMock(spec=VibeApp)
        mock_app._mount_and_scroll = AsyncMock()
        
        # Test with too few arguments
        await VibeApp._adjust_plugin_priority(mock_app, "test_plugin")
        
        # Verify error message was mounted
        mock_app._mount_and_scroll.assert_called_once()
        
        # Check that UserCommandMessage was called with usage message
        mock_message_class.assert_called()
        message_call_args = mock_message_class.call_args[0][0]
        assert "Usage" in message_call_args
        
        # Reset mocks
        mock_app._mount_and_scroll.reset_mock()
        mock_message_class.reset_mock()
        
        # Test with invalid priority (non-integer)
        await VibeApp._adjust_plugin_priority(mock_app, "test_plugin invalid")
        
        # Verify error message was mounted
        mock_app._mount_and_scroll.assert_called_once()
        
        # Check that UserCommandMessage was called with error message
        mock_message_class.assert_called()
        message_call_args = mock_message_class.call_args[0][0]
        assert "must be an integer" in message_call_args

    @patch("vibe.cli.textual_ui.app.UserCommandMessage")
    async def test_adjust_priority_handler_handles_plugin_not_found(self, mock_message_class) -> None:
        """Test that the handler handles plugin not found correctly."""
        from vibe.cli.textual_ui.app import VibeApp
        
        # Create a mock app instance with agent_loop attribute
        mock_app = MagicMock(spec=VibeApp)
        mock_agent_loop = MagicMock()
        mock_agent_loop.adjust_plugin_priority = MagicMock(return_value=False)
        mock_app.agent_loop = mock_agent_loop
        mock_app._mount_and_scroll = AsyncMock()
        
        # Call the handler method
        await VibeApp._adjust_plugin_priority(mock_app, "nonexistent_plugin 100")
        
        # Verify the agent loop method was called correctly
        mock_agent_loop.adjust_plugin_priority.assert_called_once_with("nonexistent_plugin", 100)
        
        # Verify warning message was mounted
        mock_app._mount_and_scroll.assert_called_once()
        
        # Check that UserCommandMessage was called with warning message
        mock_message_class.assert_called()
        message_call_args = mock_message_class.call_args[0][0]
        assert "Warning" in message_call_args
        assert "not found" in message_call_args
