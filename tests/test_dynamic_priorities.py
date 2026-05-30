"""Tests for dynamic priorities feature."""

import pytest
from vibe.core.plugins.base import PriorityGroup, PluginMetadata, VibePlugin, PluginContext
from vibe.core.plugins.manager import PluginManager
from vibe.core.config import VibeConfig
from pathlib import Path


class TestPriorityGroup:
    """Test PriorityGroup enum."""
    
    def test_priority_group_values(self):
        """Test that PriorityGroup enum has correct values."""
        assert PriorityGroup.CRITICAL == 25
        assert PriorityGroup.HIGH == 75
        assert PriorityGroup.DEFAULT == 100
        assert PriorityGroup.LOW == 175
        assert PriorityGroup.DELAYED == 250


class MockPlugin(VibePlugin):
    """Mock plugin for testing."""
    
    def __init__(self, priority=100):
        super().__init__()
        self._custom_priority = priority
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            priority=100
        )
    
    def effective_priority(self) -> int:
        """Override to use custom priority if set."""
        if self._runtime_priority is not None:
            return self._runtime_priority
        return self._custom_priority if hasattr(self, '_custom_priority') else 100

    async def setup(self, context: PluginContext) -> None:
        pass

    async def teardown(self) -> None:
        pass


class TestVibePluginPriority:
    """Test VibePlugin priority methods."""
    
    def test_initial_priority(self):
        """Test that initial priority comes from metadata."""
        plugin = MockPlugin()
        assert plugin.effective_priority() == 100
    
    def test_set_runtime_priority(self):
        """Test setting runtime priority without context (backward compatibility)."""
        plugin = MockPlugin()
        plugin.set_runtime_priority(50)
        assert plugin.effective_priority() == 50
    
    def test_clear_runtime_priority(self):
        """Test clearing runtime priority."""
        plugin = MockPlugin()
        plugin.set_runtime_priority(50)
        assert plugin.effective_priority() == 50
        
        plugin.clear_runtime_priority()
        assert plugin.effective_priority() == 100
    
    def test_priority_override_precedence(self):
        """Test that runtime priority overrides metadata priority."""
        plugin = MockPlugin(priority=75)
        assert plugin.effective_priority() == 75
        
        plugin.set_runtime_priority(25)
        assert plugin.effective_priority() == 25
        
        plugin.clear_runtime_priority()
        assert plugin.effective_priority() == 75

    def test_runtime_priority_bounds_checking(self):
        """Test that runtime priority bounds checking works correctly."""
        config = VibeConfig()
        context = PluginContext(
            workdir=Path.cwd(),
            config=config,
            tool_manager=None
        )
        
        plugin = MockPlugin()
        
        # Test valid priority within bounds
        plugin.set_runtime_priority(50, context)
        assert plugin.effective_priority() == 50
        
        # Test priority below minimum bound
        with pytest.raises(ValueError, match="out of bounds"):
            plugin.set_runtime_priority(5, context)  # Below plugin_min_priority (10)
        
        # Test priority above maximum bound
        with pytest.raises(ValueError, match="out of bounds"):
            plugin.set_runtime_priority(250, context)  # Above plugin_max_priority (200)
        
        # Test that bounds checking is skipped when context is None (backward compatibility)
        plugin.set_runtime_priority(5)  # Should work without context
        assert plugin.effective_priority() == 5
        
        plugin.set_runtime_priority(250)  # Should work without context
        assert plugin.effective_priority() == 250


class HighPriorityPlugin(VibePlugin):
    """High priority mock plugin."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="high-priority",
            version="1.0.0",
            description="High priority plugin",
            priority=50
        )

    async def setup(self, context: PluginContext) -> None:
        pass

    async def teardown(self) -> None:
        pass


class LowPriorityPlugin(VibePlugin):
    """Low priority mock plugin."""
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="low-priority",
            version="1.0.0",
            description="Low priority plugin",
            priority=150
        )

    async def setup(self, context: PluginContext) -> None:
        pass

    async def teardown(self) -> None:
        pass


class TestPluginManagerDynamicPriorities:
    """Test PluginManager dynamic priority handling."""
    
    @pytest.fixture
    def config(self):
        """Create a test config."""
        return VibeConfig()
    
    @pytest.fixture
    def context(self, config):
        """Create a test context."""
        return PluginContext(
            workdir=Path.cwd(),
            config=config,
            tool_manager=None
        )
    
    @pytest.fixture
    def plugin_manager(self, config, context):
        """Create a plugin manager with test plugins."""
        manager = PluginManager(config, context)
        
        # Manually add plugins for testing
        high_plugin = HighPriorityPlugin()
        low_plugin = LowPriorityPlugin()
        default_plugin = MockPlugin()
        
        manager._plugins = [high_plugin, low_plugin, default_plugin]
        return manager
    
    def test_get_sorted_plugins_static(self, plugin_manager, context):
        """Test that plugins are sorted by static priority when dynamic priorities are disabled."""
        sorted_plugins = plugin_manager.get_sorted_plugins(context)
        
        # Should be sorted by priority: high (50), default (100), low (150)
        assert sorted_plugins[0].metadata().name == "high-priority"
        assert sorted_plugins[1].metadata().name == "test-plugin"
        assert sorted_plugins[2].metadata().name == "low-priority"
    
    def test_get_sorted_plugins_with_runtime_override(self, plugin_manager, context):
        """Test that runtime priority overrides affect sorting."""
        # Override priorities with context for bounds checking
        for plugin in plugin_manager.all_plugins:
            if plugin.metadata().name == "high-priority":
                plugin.set_runtime_priority(200, context)  # Make it lowest
            elif plugin.metadata().name == "low-priority":
                plugin.set_runtime_priority(25, context)   # Make it highest
         
        sorted_plugins = plugin_manager.get_sorted_plugins(context)
        
        # Should now be sorted by runtime priority: low (25), default (100), high (200)
        assert sorted_plugins[0].metadata().name == "low-priority"
        assert sorted_plugins[1].metadata().name == "test-plugin"
        assert sorted_plugins[2].metadata().name == "high-priority"
    
    def test_adjust_plugin_priority(self, plugin_manager, context):
        """Test AgentLoop.adjust_plugin_priority method."""
        # This would normally be tested through AgentLoop, but we'll test the plugin method directly
        high_plugin = plugin_manager._plugins[0]  # high-priority plugin
        
        # Initial priority should be 50
        assert high_plugin.effective_priority() == 50
        
        # Adjust priority with context
        high_plugin.set_runtime_priority(75, context)
        assert high_plugin.effective_priority() == 75
        
        # Clear override
        high_plugin.clear_runtime_priority()
        assert high_plugin.effective_priority() == 50


class ContextAwarePlugin(VibePlugin):
    """Plugin with context-aware priority adjustment."""
    
    def __init__(self, base_priority=100):
        super().__init__()
        self._base_priority = base_priority
    
    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="context-aware",
            version="1.0.0",
            description="Context aware plugin",
            priority=100
        )

    async def setup(self, context: PluginContext) -> None:
        pass

    async def teardown(self) -> None:
        pass
    
    def context_aware_priority(self, context: PluginContext) -> int:
        """Adjust priority based on context."""
        # In a real scenario, this might check workdir contents, config settings, etc.
        if "test" in str(context.workdir).lower():
            return PriorityGroup.HIGH  # Higher priority in test directories
        return self._base_priority


class TestContextAwarePriorities:
    """Test context-aware priority resolution."""
    
    @pytest.fixture
    def config_with_dynamic_priorities(self):
        """Create a config with dynamic priorities enabled."""
        config = VibeConfig(dynamic_priorities=True)
        return config
    
    @pytest.fixture
    def context(self, config_with_dynamic_priorities):
        """Create a test context."""
        return PluginContext(
            workdir=Path("/test/workdir"),
            config=config_with_dynamic_priorities,
            tool_manager=None
        )
    
    @pytest.fixture
    def plugin_manager(self, config_with_dynamic_priorities, context):
        """Create a plugin manager with context-aware plugin."""
        manager = PluginManager(config_with_dynamic_priorities, context)
        
        # Add plugins
        context_aware = ContextAwarePlugin(base_priority=150)
        normal_plugin = MockPlugin()
        
        manager._plugins = [context_aware, normal_plugin]
        return manager
    
    def test_context_aware_priority_adjustment(self, plugin_manager, context):
        """Test that context-aware plugins adjust their priority."""
        sorted_plugins = plugin_manager.get_sorted_plugins(context)
        
        # Context-aware plugin should have higher priority (75) in test workdir
        # Normal plugin has default priority (100)
        assert sorted_plugins[0].metadata().name == "context-aware"
        assert sorted_plugins[1].metadata().name == "test-plugin"
    
    def test_context_aware_fallback(self, config_with_dynamic_priorities):
        """Test that context-aware plugins fall back to base priority on failure."""
        context = PluginContext(
            workdir=Path("/test/workdir"),
            config=config_with_dynamic_priorities,
            tool_manager=None
        )
        
        class BrokenContextAwarePlugin(VibePlugin):
            @classmethod
            def metadata(cls) -> PluginMetadata:
                return PluginMetadata(
                    name="broken-context-aware",
                    version="1.0.0",
                    description="Broken context aware plugin",
                    priority=150
                )

            async def setup(self, context: PluginContext) -> None:
                pass

            async def teardown(self) -> None:
                pass
            
            def context_aware_priority(self, context: PluginContext) -> int:
                """This will fail."""
                raise RuntimeError("Context analysis failed")
        
        manager = PluginManager(config_with_dynamic_priorities, context)
        broken_plugin = BrokenContextAwarePlugin()
        normal_plugin = MockPlugin()
        
        manager._plugins = [broken_plugin, normal_plugin]
        
        # Should fall back to base priority and log the error
        sorted_plugins = manager.get_sorted_plugins(context)
        
        # Normal plugin (100) should come before broken plugin (150)
        assert sorted_plugins[0].metadata().name == "test-plugin"
        assert sorted_plugins[1].metadata().name == "broken-context-aware"


class TestBackwardCompatibility:
    """Test backward compatibility with existing plugins."""
    
    def test_plugins_without_priority_group(self):
        """Test that plugins without priority_group field still work."""
        # This tests that our changes don't break existing plugins
        class LegacyPlugin(VibePlugin):
            @classmethod
            def metadata(cls) -> PluginMetadata:
                return PluginMetadata(
                    name="legacy",
                    version="1.0.0",
                    description="Legacy plugin without priority_group",
                    priority=100
                    # No priority_group field
                )

            async def setup(self, context: PluginContext) -> None:
                pass

            async def teardown(self) -> None:
                pass
        
        plugin = LegacyPlugin()
        assert plugin.effective_priority() == 100
        
        # Test backward compatibility - should work without context
        plugin.set_runtime_priority(50)
        assert plugin.effective_priority() == 50