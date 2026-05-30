"""Example of a ContextAwarePlugin that adjusts priority based on context.

This example demonstrates how to create a plugin that dynamically adjusts
its execution priority based on the current working directory and other
context information.
"""

from pathlib import Path
from vibe.core.plugins.base import PluginContext, PluginMetadata, VibePlugin
from vibe.core.plugins.context_aware import ContextAwarePlugin


class SmartCodeAnalysisPlugin(VibePlugin, ContextAwarePlugin):
    """A plugin that provides code analysis with context-aware priority.
    
    This plugin adjusts its priority based on:
    - Whether the current directory contains Python files
    - Whether the directory is a git repository
    - The presence of specific configuration files
    """

    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="smart-code-analysis",
            version="1.0.0",
            description="Context-aware code analysis plugin",
            priority=100,  # Default priority
            capabilities=["code-analysis", "static-analysis"],
        )

    async def setup(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        # Setup code analysis tools, etc.
        pass

    async def teardown(self) -> None:
        """Clean up resources."""
        # Clean up analysis tools, etc.
        pass

    def context_aware_priority(self, context: PluginContext) -> int:
        """Adjust priority based on current context.
        
        Higher priority (lower number) when:
        - Working in a Python project
        - Git repository is present
        - Specific analysis configuration exists
        """
        workdir = context.workdir
        
        # Base priority adjustment
        priority = self.metadata().priority
        
        # Check if this is a Python project
        python_files = list(workdir.rglob("*.py"))
        if python_files:
            priority = max(50, priority - 30)  # Higher priority for Python projects
        
        # Check if this is a git repository
        git_dir = workdir / ".git"
        if git_dir.is_dir():
            priority = max(40, priority - 20)  # Even higher priority for git repos
        
        # Check for specific configuration files
        config_files = [
            workdir / ".codeanalysis",
            workdir / "pyproject.toml",
            workdir / "setup.py",
        ]
        
        for config_file in config_files:
            if config_file.exists():
                priority = max(30, priority - 15)  # Highest priority with config
                break
        
        return priority


class DocumentationPlugin(VibePlugin, ContextAwarePlugin):
    """A plugin that generates documentation with context-aware priority.
    
    This plugin adjusts its priority based on:
    - Presence of documentation files
    - Project type (higher priority for library projects)
    """

    @classmethod
    def metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="smart-documentation",
            version="1.0.0",
            description="Context-aware documentation generator",
            priority=120,  # Slightly lower default priority
            capabilities=["documentation", "doc-generation"],
        )

    async def setup(self, context: PluginContext) -> None:
        """Initialize documentation tools."""
        pass

    async def teardown(self) -> None:
        """Clean up documentation resources."""
        pass

    def context_aware_priority(self, context: PluginContext) -> int:
        """Adjust priority based on documentation needs."""
        workdir = context.workdir
        
        # Base priority
        priority = self.metadata().priority
        
        # Check for existing documentation
        doc_dirs = [
            workdir / "docs",
            workdir / "documentation",
            workdir / "doc",
        ]
        
        has_docs = any(doc_dir.exists() for doc_dir in doc_dirs)
        
        # Check for documentation configuration
        doc_configs = [
            workdir / "docs" / "conf.py",  # Sphinx
            workdir / "mkdocs.yml",        # MkDocs
            workdir / "docusaurus.config.js",  # Docusaurus
        ]
        
        has_doc_config = any(config.exists() for config in doc_configs)
        
        # Adjust priority based on findings
        if has_docs and has_doc_config:
            priority = 80  # High priority if docs exist and are configured
        elif has_docs:
            priority = 100  # Medium priority if docs exist but no config
        elif has_doc_config:
            priority = 90  # Medium-high priority if config exists but no docs yet
        # Otherwise keep default priority (120)
        
        return priority


# Usage example
if __name__ == "__main__":
    from vibe.core.plugins.base import PluginContext
    from vibe.core.config import VibeConfig
    from pathlib import Path
    
    # Create a test context
    config = VibeConfig()
    context = PluginContext(
        workdir=Path.cwd(),
        config=config,
        tool_manager=None,
        extra={},
    )
    
    # Test the context-aware plugins
    analysis_plugin = SmartCodeAnalysisPlugin()
    doc_plugin = DocumentationPlugin()
    
    print("Smart Code Analysis Plugin:")
    print(f"  Base priority: {analysis_plugin.metadata().priority}")
    print(f"  Context-aware priority: {analysis_plugin.context_aware_priority(context)}")
    
    print("\nDocumentation Plugin:")
    print(f"  Base priority: {doc_plugin.metadata().priority}")
    print(f"  Context-aware priority: {doc_plugin.context_aware_priority(context)}")