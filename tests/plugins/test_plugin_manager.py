"""Unit tests for PluginManager's get_plugin_statistics method."""

import pytest
from unittest.mock import MagicMock
from vibe.core.plugins.manager import PluginManager
from vibe.core.plugins.base import VibePlugin, PluginMetadata


class MockPlugin(VibePlugin):
    """Mock plugin for testing."""

    def __init__(self, name: str, version: str, priority: int):
        self._name = name
        self._version = version
        self._priority = priority

    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="mock-plugin",
            version="0.1.0",
            description="A mock plugin for testing.",
            priority=100,
        )

    async def setup(self, context):
        pass

    async def teardown(self):
        pass


def test_get_plugin_statistics():
    """Test that PluginManager.get_plugin_statistics returns correct statistics."""
    # Setup
    config = MagicMock()
    context = MagicMock()
    manager = PluginManager(config, context)

    # Add mock plugins
    plugin1 = MagicMock(spec=VibePlugin)
    plugin1.metadata.return_value = PluginMetadata(
        name="plugin1", version="1.0.0", priority=50
    )

    plugin2 = MagicMock(spec=VibePlugin)
    plugin2.metadata.return_value = PluginMetadata(
        name="plugin2", version="2.0.0", priority=100
    )

    manager._plugins = [plugin1, plugin2]

    # Execute
    stats = manager.get_plugin_statistics()

    # Verify
    assert len(stats) == 2
    assert stats[0]["name"] == "plugin1"
    assert stats[0]["version"] == "1.0.0"
    assert stats[0]["priority"] == 50
    assert stats[0]["active"] is True

    assert stats[1]["name"] == "plugin2"
    assert stats[1]["version"] == "2.0.0"
    assert stats[1]["priority"] == 100
    assert stats[1]["active"] is True
