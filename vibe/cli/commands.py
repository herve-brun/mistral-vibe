from __future__ import annotations

from dataclasses import dataclass
import sys

ALT_KEY = "⌥" if sys.platform == "darwin" else "Alt"


@dataclass
class Command:
    aliases: frozenset[str]
    description: str
    handler: str
    exits: bool = False


class CommandRegistry:
    def __init__(self, excluded_commands: list[str] | None = None) -> None:
        if excluded_commands is None:
            excluded_commands = []
        self.commands = {
            "help": Command(
                aliases=frozenset(["/help"]),
                description="Show help message",
                handler="_show_help",
            ),
            "config": Command(
                aliases=frozenset(["/config"]),
                description="Edit config settings",
                handler="_show_config",
            ),
            "model": Command(
                aliases=frozenset(["/model"]),
                description="Select active model",
                handler="_show_model",
            ),
            "reload": Command(
                aliases=frozenset(["/reload"]),
                description="Reload configuration, agent instructions, and skills from disk",
                handler="_reload_config",
            ),
            "clear": Command(
                aliases=frozenset(["/clear"]),
                description="Clear conversation history",
                handler="_clear_history",
            ),
            "log": Command(
                aliases=frozenset(["/log"]),
                description="Show path to current interaction log file",
                handler="_show_log_path",
            ),
            "debug": Command(
                aliases=frozenset(["/debug"]),
                description="Toggle debug console",
                handler="action_toggle_debug_console",
            ),
            "compact": Command(
                aliases=frozenset(["/compact"]),
                description="Compact conversation history by summarizing",
                handler="_compact_history",
            ),
            "exit": Command(
                aliases=frozenset(["/exit"]),
                description="Exit the application",
                handler="_exit_app",
                exits=True,
            ),
            "status": Command(
                aliases=frozenset(["/status"]),
                description="Display agent statistics",
                handler="_show_status",
            ),
            "plugins": Command(
                aliases=frozenset(["/plugins"]),
                description="Display plugins statuses",
                handler="_show_plugins_status",
            ),
            "teleport": Command(
                aliases=frozenset(["/teleport"]),
                description="Teleport session to Vibe Nuage",
                handler="_teleport_command",
            ),
            "proxy-setup": Command(
                aliases=frozenset(["/proxy-setup"]),
                description="Configure proxy and SSL certificate settings",
                handler="_show_proxy_setup",
            ),
            "resume": Command(
                aliases=frozenset(["/resume", "/continue"]),
                description="Browse and resume past sessions",
                handler="_show_session_picker",
            ),
            "mcp": Command(
                aliases=frozenset(["/mcp", "/connectors"]),
                description=(
                    "Display available MCP servers and connectors. "
                    "Pass a name to list its tools"
                ),
                handler="_show_mcp",
            ),
            "voice": Command(
                aliases=frozenset(["/voice"]),
                description="Configure voice settings",
                handler="_show_voice_settings",
            ),
            "leanstall": Command(
                aliases=frozenset(["/leanstall"]),
                description="Install the Lean 4 agent (leanstral)",
                handler="_install_lean",
            ),
            "unleanstall": Command(
                aliases=frozenset(["/unleanstall"]),
                description="Uninstall the Lean 4 agent",
                handler="_uninstall_lean",
            ),
            "rewind": Command(
                aliases=frozenset(["/rewind"]),
                description="Rewind to a previous message",
                handler="_start_rewind_mode",
            ),
             "data-retention": Command(
                 aliases=frozenset(["/data-retention"]),
                 description="Show data retention information",
                 handler="_show_data_retention",
             ),
             "adjust-priority": Command(
                  aliases=frozenset(["/adjust-priority"]),
                  description="Adjust plugin priority (usage: /adjust-priority <plugin_name> <priority>)",
                  handler="_adjust_plugin_priority",
              ),
            "plugin-stats": Command(
                aliases=frozenset(["/plugin-stats"]),
                description="Display plugin usage statistics",
                handler="_show_plugin_stats",
            ),
         }

        for command in excluded_commands:
            self.commands.pop(command, None)

        self._alias_map = {}
        for cmd_name, cmd in self.commands.items():
            for alias in cmd.aliases:
                self._alias_map[alias] = cmd_name

        # Map to store handler callables (for plugin commands)
        self._handler_map: dict[str, object] = {}

    def get_command_name(self, user_input: str) -> str | None:
        return self._alias_map.get(user_input.lower().strip())

    def parse_command(self, user_input: str) -> tuple[str, Command, str] | None:
        parts = user_input.strip().split(None, 1)
        if not parts:
            return None

        cmd_word = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""
        cmd_name = self.get_command_name(cmd_word)
        if cmd_name is None:
            return None

        command = self.commands[cmd_name]
        return cmd_name, command, cmd_args

    def find_command(self, user_input: str) -> Command | None:
        cmd_name = self.get_command_name(user_input)
        return self.commands.get(cmd_name) if cmd_name else None

    def register_command(self, name: str, command: Command) -> None:
        """Register a new command dynamically.

        Parameters
        ----------
        name : str
            The canonical command name (e.g., "my_custom_cmd").
        command : Command
            The Command object to register.
        """
        self.commands[name] = command
        for alias in command.aliases:
            self._alias_map[alias] = name

    def register_handler(self, handler_name: str, callable_obj: object) -> None:
        """Register a handler callable for a plugin command.

        Parameters
        ----------
        handler_name : str
            The handler method name (e.g., "_show_greeting").
        callable_obj : object
            The actual method/callable to invoke.
        """
        self._handler_map[handler_name] = callable_obj

    def get_handler(self, handler_name: str) -> object | None:
        """Get the registered handler callable for a given handler name.

        Parameters
        ----------
        handler_name : str
            The handler method name to look up.

        Returns
        -------
        object | None
            The callable if found, None otherwise.
        """
        return self._handler_map.get(handler_name)

    def get_help_text(self) -> str:
        lines: list[str] = [
            "### Keyboard Shortcuts",
            "",
            "- `Enter` Submit message",
            "- `Ctrl+J` / `Shift+Enter` Insert newline",
            "- `Escape` Interrupt agent or close dialogs",
            "- `Ctrl+C` Quit (or clear input if text present)",
            "- `Ctrl+G` Edit input in external editor",
            "- `Ctrl+O` Toggle tool output view",
            "- `Shift+Tab` Toggle auto-approve mode",
            f"- `{ALT_KEY}+↑↓` / `Ctrl+P/N` Rewind to previous/next message",
            "",
            "### Special Features",
            "",
            "- `!<command>` Execute bash command directly",
            "- `@path/to/file/` Autocompletes file paths",
            "",
            "### Commands",
            "",
        ]

        for cmd in self.commands.values():
            aliases = ", ".join(f"`{alias}`" for alias in sorted(cmd.aliases))
            lines.append(f"- {aliases}: {cmd.description}")
        return "\n".join(lines)
