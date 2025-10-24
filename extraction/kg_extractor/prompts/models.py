"""Prompt template models."""

from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError as Jinja2TemplateError
from pydantic import BaseModel, Field


class PromptVariable(BaseModel):
    """Definition of a prompt template variable."""

    type: str = Field(
        description="Variable type (e.g., 'str', 'list[Path]', 'Path')",
    )
    required: bool = Field(
        default=True,
        description="Whether this variable must be provided",
    )
    default: Any = Field(
        default=None,
        description="Default value if not provided",
    )
    description: str = Field(
        description="Human-readable description of variable",
    )
    example: Any = Field(
        default=None,
        description="Example value for documentation",
    )

    def validate_value(self, value: Any) -> None:
        """
        Validate that value matches expected type.

        Type validation happens at render time.
        This is a placeholder for future type checking.

        Args:
            value: Value to validate
        """
        # Type validation happens at render time
        # This is a placeholder for future type checking
        pass


class PromptMetadata(BaseModel):
    """Metadata about a prompt template."""

    name: str = Field(description="Unique prompt name")
    version: str = Field(description="Semantic version (e.g., '1.0.0')")
    description: str = Field(description="What this prompt does")
    author: str = Field(default="KG Extraction Team")
    created: str = Field(description="Creation date (YYYY-MM-DD)")
    updated: str | None = Field(default=None, description="Last update date")


class PromptTemplate(BaseModel):
    """
    A prompt template with metadata, variables, and Jinja2 templates.

    Represents a reusable, documented, versioned prompt.
    """

    metadata: PromptMetadata
    variables: dict[str, PromptVariable]
    system_prompt: str = Field(description="Jinja2 template for system prompt")
    user_prompt: str = Field(description="Jinja2 template for user prompt")

    def render(self, **kwargs: Any) -> tuple[str, str]:
        """
        Render system and user prompts with provided variables.

        Args:
            **kwargs: Variable values to render into template

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            ValueError: Missing required variable
            TemplateError: Invalid template syntax or undefined variable
        """
        # Validate required variables (excluding those with defaults)
        missing = [
            name
            for name, var in self.variables.items()
            if var.required and name not in kwargs and var.default is None
        ]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Apply defaults
        render_vars = {
            name: kwargs.get(name, var.default) for name, var in self.variables.items()
        }

        # Add any extra kwargs not in variable definitions
        for key, value in kwargs.items():
            if key not in render_vars:
                render_vars[key] = value

        # Render with Jinja2 (strict mode - fail on undefined)
        env = Environment(undefined=StrictUndefined)

        try:
            system = env.from_string(self.system_prompt).render(**render_vars)
            user = env.from_string(self.user_prompt).render(**render_vars)
            return system, user
        except Jinja2TemplateError as e:
            raise TemplateError(f"Failed to render template: {e}") from e

    def generate_documentation(self) -> str:
        """
        Generate markdown documentation for this prompt.

        Returns:
            Markdown documentation string
        """
        doc = f"# {self.metadata.name} (v{self.metadata.version})\n\n"
        doc += f"{self.metadata.description}\n\n"

        # Metadata
        doc += "## Metadata\n\n"
        doc += f"- **Author**: {self.metadata.author}\n"
        doc += f"- **Created**: {self.metadata.created}\n"
        if self.metadata.updated:
            doc += f"- **Updated**: {self.metadata.updated}\n"
        doc += "\n"

        # Variables
        doc += "## Variables\n\n"
        for name, var in self.variables.items():
            doc += f"### `{name}`\n\n"
            doc += f"- **Type**: `{var.type}`\n"
            doc += f"- **Required**: {'Yes' if var.required else 'No'}\n"
            if var.default is not None:
                doc += f"- **Default**: `{var.default}`\n"
            doc += f"- **Description**: {var.description}\n"
            if var.example is not None:
                doc += f"- **Example**: `{var.example}`\n"
            doc += "\n"

        # Example usage
        doc += "## Example Usage\n\n"
        doc += "```python\n"
        doc += f'template = loader.load("{self.metadata.name}")\n'
        doc += "system, user = template.render(\n"
        for name, var in self.variables.items():
            if var.example is not None:
                doc += f"    {name}={repr(var.example)},\n"
        doc += ")\n"
        doc += "```\n\n"

        return doc

    def list_variables(self) -> list[str]:
        """
        List all variable names.

        Returns:
            List of variable names
        """
        return list(self.variables.keys())

    def get_variable(self, name: str) -> PromptVariable:
        """
        Get variable definition by name.

        Args:
            name: Variable name

        Returns:
            Variable definition

        Raises:
            KeyError: Variable not found
        """
        if name not in self.variables:
            raise KeyError(f"Variable not found: {name}")
        return self.variables[name]


class TemplateError(Exception):
    """Error rendering template."""

    pass
