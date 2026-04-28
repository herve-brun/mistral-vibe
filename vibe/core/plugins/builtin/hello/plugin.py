"""Example plugin that demonstrates how to add custom slash commands.

This plugin adds two new commands:
- /greet: Shows a friendly greeting message
- /time: Displays the current time
"""

from __future__ import annotations

from typing import Any

from vibe.cli.commands import Command, CommandRegistry
from vibe.core.plugins.base import PluginContext, PluginMetadata, VibePlugin
from vibe.core.plugins.command_plugin import CommandPlugin


class ExampleCommandPlugin(VibePlugin, CommandPlugin):
    """Example plugin that adds custom slash commands."""

    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="example-commands",
            version="1.0.0",
            description="Demonstrates how to add custom slash commands",
            priority=100,
            tags=["demo", "example"],
        )

    async def setup(self, context: PluginContext) -> None:
        """Setup the plugin. Required by VibePlugin interface."""
        pass

    async def teardown(self) -> None:
        """Teardown the plugin. Required by VibePlugin interface."""
        pass

    async def register_commands(self, registry: CommandRegistry) -> None:
        """Register our custom commands."""
        # Add a greeting command
        registry.register_command(
            name="greet",
            command=Command(
                aliases=frozenset(["/greet"]),
                description="Show a friendly greeting",
                handler="_show_greeting",
            ),
        )

        # Add a time command
        registry.register_command(
            name="time",
            command=Command(
                aliases=frozenset(["/time"]),
                description="Display current time",
                handler="_show_time",
            ),
        )

    async def _show_greeting(self, **kwargs: Any) -> str:
        """Handler for /greet command."""
        return "Hello there! How can I help you today?"

    async def _show_time(self, **kwargs: Any) -> str:
        """Handler for /time command."""
        from datetime import datetime

        return f"Current time: {datetime.now().strftime('%H:%M:%S')}"
