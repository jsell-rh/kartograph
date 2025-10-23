"""Prompt loader protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy testing with in-memory loaders
- Swappable prompt loading strategies (disk, remote, cached)
"""

from typing import Protocol

from kg_extractor.prompts.models import PromptTemplate


class PromptLoader(Protocol):
    """
    Abstract interface for loading prompt templates.

    This protocol defines the boundary around prompt loading, enabling:
    - Testing with in-memory templates
    - Caching of loaded templates
    - Template discovery and introspection
    """

    def load(self, name: str) -> PromptTemplate:
        """
        Load a prompt template by name.

        Args:
            name: Template name (without extension)

        Returns:
            Loaded prompt template

        Raises:
            FileNotFoundError: Template not found
            TemplateError: Failed to parse template
        """
        ...

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            List of template names (sorted alphabetically)
        """
        ...

    def reload(self, name: str) -> PromptTemplate:
        """
        Reload template from disk (bypass cache).

        Args:
            name: Template name to reload

        Returns:
            Freshly loaded template

        Raises:
            FileNotFoundError: Template not found
            TemplateError: Failed to parse template
        """
        ...
