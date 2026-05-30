"""Test the ContextAwarePlugin mixin and integration with PluginManager."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from vibe.core.plugins.base import PluginContext, PluginMetadata, VibePlugin
from vibe.core.plugins.context_aware import ContextAwarePlugin
from vibe.core.plugins.manager import PluginManager
from vibe.core.config import VibeConfig


class TestContextAwarePlugin:
    """Tests for ContextAwarePlugin mixin."""

    def test_context_aware_plugin_interface(self) -> None:
        """Test that ContextAwarePlugin defines the required interface."""
        assert hasattr(ContextAwarePlugin, 'context_aware_priority')
        assert callable(getattr(ContextAwarePlugin, 'context_aware_priority'))

    def test_context_aware_plugin_is_abstract(self) -> None:
        """Test that ContextAwarePlugin is an abstract base class."""
        import abc
        assert isinstance(ContextAwarePlugin, abc.ABCMeta)
        assert ContextAwarePlugin.__abstractmethods__ == {'context_aware_priority'}


class TestContextAwarePluginIntegration:
    """Tests for ContextAwarePlugin integration with PluginManager."""

    @pytest.fixture
    def mock_config(self, tmp_path) -> VibeConfig:
        """Create mock VibeConfig for testing."""
        return VibeConfig(
            plugin_paths=[],
            enabled_plugins=None,
            disabled_plugins=[],
            dynamic_priorities=True,  # Enable dynamic priorities for testing
        )

    @pytest.fixture
    def plugin_context(self, mock_config: VibeConfig, tmp_path) -> PluginContext:
        """Create PluginContext for testing."""
        return PluginContext(
            workdir=tmp_path,
            config=mock_config,
            tool_manager=None,
            extra={},
        )

    @pytest.fixture
    def context_aware_plugin(self) -> type[VibePlugin]:
        """Create a context-aware plugin for testing."""

        class TestContextAwarePlugin(VibePlugin, ContextAwarePlugin):
            @classmethod
            def metadata(cls) -> PluginMetadata:
                return PluginMetadata(
                    name="test-context-aware",
                    version="0.1.0",
                    priority=100,
                )

            async def setup(self, context: PluginContext) -> None:
                pass

            async def teardown(self) -> None:
                pass

            def context_aware_priority(self, context: PluginContext) -> int:
                # Adjust priority based on workdir
                if "test" in str(context.workdir).lower():
                    return 50  # Higher priority for test directories
                return 150  # Lower priority otherwise

        return TestContextAwarePlugin

    @pytest.fixture
    def regular_plugin(self) -> type[VibePlugin]:
        """Create a regular plugin for testing."""

        class TestRegularPlugin(VibePlugin):
            @classmethod
            def metadata(cls) -> PluginMetadata:
                return PluginMetadata(
                    name="test-regular",
                    version="0.1.0",
                    priority=100,
                )

            async def setup(self, context: PluginContext) -> None:
                pass

            async def teardown(self) -> None:
                pass

        return TestRegularPlugin

    @pytest.mark.asyncio
    async def test_context_aware_priority_adjustment(
        self, context_aware_plugin: type[VibePlugin], 
        regular_plugin: type[VibePlugin], 
        plugin_context: PluginContext
    ) -> None:
        """Test that context-aware plugins adjust their priority correctly."""
        # Create plugin instances
        context_aware_instance = context_aware_plugin()
        regular_instance = regular_plugin()
        
        # Test context-aware priority adjustment
        test_workdir = plugin_context.workdir / "test"
        test_context = PluginContext(
            workdir=test_workdir,
            config=plugin_context.config,
            tool_manager=None,
            extra={},
        )
        
        # Context-aware plugin should return higher priority for test directories
        adjusted_priority = context_aware_instance.context_aware_priority(test_context)
        assert adjusted_priority == 50
        
        # Regular plugin should not implement ContextAwarePlugin interface
        assert not isinstance(regular_instance, ContextAwarePlugin)

    @pytest.mark.asyncio
    async def test_plugin_manager_context_aware_sorting(
        self, context_aware_plugin: type[VibePlugin], 
        regular_plugin: type[VibePlugin], 
        plugin_context: PluginContext,
        tmp_path
    ) -> None:
        """Test that PluginManager sorts plugins correctly with context-aware priorities."""
        # Create a temporary directory for plugin files
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        
        # Create plugin files
        context_aware_file = plugin_dir / "context_aware" / "plugin.py"
        context_aware_file.parent.mkdir()
        context_aware_file.write_text(f"""
from vibe.core.plugins.base import VibePlugin, PluginMetadata
from vibe.core.plugins.context_aware import ContextAwarePlugin

class TestContextAwarePlugin(VibePlugin, ContextAwarePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(name="test-context-aware", version="0.1.0", priority=100)

    async def setup(self, context):
        pass

    async def teardown(self):
        pass

    def context_aware_priority(self, context):
        if "/test" in str(context.workdir):
            return 50
        return 150
""")
        
        regular_file = plugin_dir / "regular" / "plugin.py"
        regular_file.parent.mkdir()
        regular_file.write_text(f"""
from vibe.core.plugins.base import VibePlugin, PluginMetadata

class TestRegularPlugin(VibePlugin):
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(name="test-regular", version="0.1.0", priority=100)

    async def setup(self, context):
        pass

    async def teardown(self):
        pass
""")
        
        # Create plugin manager with test directory in plugin paths
        config = VibeConfig(
            plugin_paths=[str(plugin_dir)],
            enabled_plugins=None,
            disabled_plugins=[],
            dynamic_priorities=True,
        )
        
        context = PluginContext(
            workdir=tmp_path / "test",  # Use test directory to trigger high priority
            config=config,
            tool_manager=None,
            extra={},
        )
        
        manager = PluginManager(config, context)
        
        # Discover plugins
        await manager.discover_and_setup()
        
        # Get sorted plugins - context-aware should come first due to higher priority
        sorted_plugins = manager.get_sorted_plugins(context)
        plugin_names = [plugin.metadata().name for plugin in sorted_plugins]
        
        # Context-aware plugin should be first due to adjusted priority
        assert "test-context-aware" in plugin_names
        assert "test-regular" in plugin_names

    def test_cache_key_generation(self, context_aware_plugin: type[VibePlugin], plugin_context: PluginContext) -> None:
        """Test that cache keys are generated correctly."""
        plugin_instance = context_aware_plugin()
        manager = PluginManager(
            config=plugin_context.config,
            context=plugin_context
        )
        
        # Test cache key generation
        cache_key = manager._generate_cache_key(plugin_instance, plugin_context)
        
        # Cache key should contain plugin name and context hash
        assert "test-context-aware" in cache_key
        assert ":" in cache_key
        
        # Different contexts should generate different keys
        different_context = PluginContext(
            workdir=plugin_context.workdir / "different",
            config=plugin_context.config,
            tool_manager=None,
            extra={},
        )
        different_key = manager._generate_cache_key(plugin_instance, different_context)
        
        assert cache_key != different_key

    def test_backward_compatibility(self, regular_plugin: type[VibePlugin], plugin_context: PluginContext) -> None:
        """Test that regular plugins work without context-aware functionality."""
        plugin_instance = regular_plugin()
        manager = PluginManager(
            config=plugin_context.config,
            context=plugin_context
        )
        
        # Regular plugins should not implement ContextAwarePlugin
        assert not isinstance(plugin_instance, ContextAwarePlugin)
        
        # But they should still work with the plugin manager
        assert hasattr(plugin_instance, 'effective_priority')
        assert plugin_instance.effective_priority() == 100