"""Prompt loader implementations."""

from pathlib import Path

import yaml

from kg_extractor.prompts.models import (
    PromptMetadata,
    PromptTemplate,
    PromptVariable,
    TemplateError,
)


class DiskPromptLoader:
    """
    Disk-based prompt loader with caching.

    Implements: PromptLoader protocol (via structural subtyping)

    Loads prompt templates from YAML files on disk and caches them
    for performance.
    """

    def __init__(self, template_dir: Path):
        """
        Initialize disk prompt loader.

        Args:
            template_dir: Directory containing template YAML files
        """
        self.template_dir = template_dir
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """
        Load template from disk (with caching).

        Args:
            name: Template name (without extension)

        Returns:
            Loaded prompt template

        Raises:
            FileNotFoundError: Template not found
            TemplateError: Failed to parse template
        """
        if name in self._cache:
            return self._cache[name]

        template = self._load_from_disk(name)
        self._cache[name] = template
        return template

    def list_templates(self) -> list[str]:
        """
        List all available templates.

        Returns:
            List of template names (sorted alphabetically)
        """
        templates = [f.stem for f in self.template_dir.glob("*.yaml")]
        return sorted(templates)

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
        template = self._load_from_disk(name)
        self._cache[name] = template
        return template

    def _load_from_disk(self, name: str) -> PromptTemplate:
        """
        Load template from YAML file.

        Args:
            name: Template name

        Returns:
            Loaded prompt template

        Raises:
            FileNotFoundError: Template not found
            TemplateError: Failed to parse template
        """
        template_file = self.template_dir / f"{name}.yaml"

        if not template_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_file}")

        try:
            with open(template_file) as f:
                data = yaml.safe_load(f)

            return PromptTemplate(
                metadata=PromptMetadata(**data["metadata"]),
                variables={
                    k: PromptVariable(**v) for k, v in data.get("variables", {}).items()
                },
                system_prompt=data["system_prompt"],
                user_prompt=data["user_prompt"],
            )
        except Exception as e:
            raise TemplateError(f"Failed to load template {name}: {e}") from e

    def generate_docs(self, output_dir: Path) -> None:
        """
        Generate documentation for all templates.

        Args:
            output_dir: Directory to write documentation files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        for name in self.list_templates():
            template = self.load(name)
            doc = template.generate_documentation()

            doc_file = output_dir / f"{name}.md"
            with open(doc_file, "w") as f:
                f.write(doc)

    def clear_cache(self) -> None:
        """Clear template cache."""
        self._cache.clear()


class InMemoryPromptLoader:
    """
    In-memory prompt loader for testing.

    Implements: PromptLoader protocol (via structural subtyping)

    Stores prompt templates in memory for fast testing without I/O.
    """

    def __init__(self, templates: dict[str, PromptTemplate] | None = None):
        """
        Initialize in-memory prompt loader.

        Args:
            templates: Optional initial templates
        """
        self._templates = templates or {}

    def load(self, name: str) -> PromptTemplate:
        """
        Load template from memory.

        Args:
            name: Template name

        Returns:
            Prompt template

        Raises:
            FileNotFoundError: Template not found
        """
        if name not in self._templates:
            raise FileNotFoundError(f"Template not found: {name}")
        return self._templates[name]

    def list_templates(self) -> list[str]:
        """
        List all templates.

        Returns:
            List of template names (sorted)
        """
        return sorted(self._templates.keys())

    def reload(self, name: str) -> PromptTemplate:
        """
        Reload template (no-op for in-memory).

        Args:
            name: Template name

        Returns:
            Prompt template
        """
        return self.load(name)

    # Test helpers

    def add_template(self, name: str, template: PromptTemplate) -> None:
        """
        Add template for testing.

        Args:
            name: Template name
            template: Prompt template to add
        """
        self._templates[name] = template

    def remove_template(self, name: str) -> None:
        """
        Remove template.

        Args:
            name: Template name
        """
        del self._templates[name]

    def clear(self) -> None:
        """Clear all templates."""
        self._templates.clear()
