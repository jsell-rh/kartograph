# Contract: Prompt Management System

## Purpose

Defines the prompt template system to enable:

- **Configuration over code** (prompts as YAML, not hardcoded strings)
- **Variable discovery** (introspectable variable definitions)
- **Type safety** (validated variable types)
- **Documentation** (auto-generated docs from templates)
- **Versioning** (track prompt changes over time)
- **Testing** (validate prompts without LLM calls)

## Interface Definition

### Core Models

```python
from pydantic import BaseModel, Field
from typing import Any, Dict
from pathlib import Path
from jinja2 import Environment, StrictUndefined, Template

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
        """Validate that value matches expected type."""
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
    variables: Dict[str, PromptVariable]
    system_prompt: str = Field(description="Jinja2 template for system prompt")
    user_prompt: str = Field(description="Jinja2 template for user prompt")

    def render(self, **kwargs) -> tuple[str, str]:
        """
        Render system and user prompts with provided variables.

        Args:
            **kwargs: Variable values to render into template

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            ValueError: Missing required variable
            TemplateError: Invalid template syntax
            UndefinedError: Variable used in template but not provided
        """
        # Validate required variables
        missing = [
            name for name, var in self.variables.items()
            if var.required and name not in kwargs
        ]
        if missing:
            raise ValueError(
                f"Missing required variables: {', '.join(missing)}"
            )

        # Apply defaults
        render_vars = {
            name: kwargs.get(name, var.default)
            for name, var in self.variables.items()
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
        except Exception as e:
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
        """List all variable names."""
        return list(self.variables.keys())

    def get_variable(self, name: str) -> PromptVariable:
        """Get variable definition by name."""
        if name not in self.variables:
            raise KeyError(f"Variable not found: {name}")
        return self.variables[name]


class TemplateError(Exception):
    """Error rendering template."""
    pass
```

### Prompt Loader

```python
from typing import Protocol
import yaml

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
```

## Implementations

### Production Implementation (Disk-Based)

```python
class DiskPromptLoader:
    """Disk-based prompt loader with caching."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self._cache: Dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """Load template from disk (with caching)."""
        if name in self._cache:
            return self._cache[name]

        template = self._load_from_disk(name)
        self._cache[name] = template
        return template

    def list_templates(self) -> list[str]:
        """List all available templates."""
        templates = [
            f.stem for f in self.template_dir.glob("*.yaml")
        ]
        return sorted(templates)

    def reload(self, name: str) -> PromptTemplate:
        """Reload template from disk (bypass cache)."""
        template = self._load_from_disk(name)
        self._cache[name] = template
        return template

    def _load_from_disk(self, name: str) -> PromptTemplate:
        """Load template from YAML file."""
        template_file = self.template_dir / f"{name}.yaml"

        if not template_file.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {template_file}"
            )

        try:
            with open(template_file) as f:
                data = yaml.safe_load(f)

            return PromptTemplate(
                metadata=PromptMetadata(**data["metadata"]),
                variables={
                    k: PromptVariable(**v)
                    for k, v in data["variables"].items()
                },
                system_prompt=data["system_prompt"],
                user_prompt=data["user_prompt"],
            )
        except Exception as e:
            raise TemplateError(f"Failed to load template {name}: {e}") from e

    def generate_docs(self, output_dir: Path) -> None:
        """Generate documentation for all templates."""
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
```

### Test Implementation (In-Memory)

```python
class InMemoryPromptLoader:
    """In-memory prompt loader for testing."""

    def __init__(self, templates: Dict[str, PromptTemplate] | None = None):
        self._templates = templates or {}

    def load(self, name: str) -> PromptTemplate:
        """Load template from memory."""
        if name not in self._templates:
            raise FileNotFoundError(f"Template not found: {name}")
        return self._templates[name]

    def list_templates(self) -> list[str]:
        """List all templates."""
        return sorted(self._templates.keys())

    def reload(self, name: str) -> PromptTemplate:
        """Reload template (no-op for in-memory)."""
        return self.load(name)

    # Test helpers
    def add_template(self, name: str, template: PromptTemplate) -> None:
        """Add template for testing."""
        self._templates[name] = template

    def remove_template(self, name: str) -> None:
        """Remove template."""
        del self._templates[name]

    def clear(self) -> None:
        """Clear all templates."""
        self._templates.clear()
```

## YAML Template Format

```yaml
metadata:
  name: entity_extraction
  version: "1.0.0"
  description: "Main entity extraction prompt for KG extraction"
  author: "KG Extraction Team"
  created: "2025-01-23"
  updated: "2025-01-24"

variables:
  file_paths:
    type: list[Path]
    required: true
    description: "List of files to extract entities from"
    example: ["/data/service.yaml", "/data/team.yaml"]

  schema_dir:
    type: Path
    required: false
    default: null
    description: "Directory containing schema files for reference"
    example: "/schemas"

  required_fields:
    type: list[str]
    required: true
    default: ["@id", "@type", "name"]
    description: "Fields that MUST be present on all entities"

  max_entities:
    type: int
    required: false
    default: 1000
    description: "Maximum entities to extract (prevents runaway generation)"

system_prompt: |
  # Knowledge Graph Entity Extraction

  You are an expert at extracting structured entity and relationship information from diverse data sources.

  ## Input Files

  {% for path in file_paths %}
  - `{{ path }}`
  {% endfor %}

  ## Task

  Extract ALL entities and relationships from the provided files.

  ### Required Fields

  ALL entities MUST have:
  {% for field in required_fields %}
  - `{{ field }}`
  {% endfor %}

  {% if schema_dir %}
  ## Schema Reference

  Schema files are available in `{{ schema_dir }}` for reference.
  {% endif %}

  Extract up to {{ max_entities }} entities.

user_prompt: |
  Please extract all entities and relationships from the provided files.

  Return your result as a JSON object with this structure:

  ```json
  {
    "entities": [
      {
        "@id": "urn:type:identifier",
        "@type": "TypeName",
        "name": "Display Name",
        ...
      }
    ],
    "metadata": {
      "entity_count": 123,
      "types_discovered": ["Service", "User"]
    }
  }
  ```

```

## Usage Examples

### Basic Usage

```python
from kg_extractor.prompts import DiskPromptLoader
from pathlib import Path

# Create loader
loader = DiskPromptLoader(template_dir=Path("kg_extractor/prompts/templates"))

# Load template
template = loader.load("entity_extraction")

# Render with variables
system, user = template.render(
    file_paths=[Path("/data/service.yaml"), Path("/data/team.yaml")],
    schema_dir=Path("/schemas"),
    required_fields=["@id", "@type", "name"],
)

print(system)  # Rendered system prompt
print(user)    # Rendered user prompt
```

### Generate Documentation

```bash
# CLI command
extractor prompt docs --output ./docs/prompts/

# Output:
# ./docs/prompts/entity_extraction.md
# ./docs/prompts/deduplication.md
# ./docs/prompts/validation.md
```

### List Available Prompts

```bash
# CLI command
extractor prompt list

# Output:
# Available prompts:
# - entity_extraction (v1.0.0): Main entity extraction prompt
# - deduplication (v1.0.0): Semantic entity deduplication
# - validation (v1.0.0): Entity validation and error reporting
```

### Testing with Mocks

```python
# tests/test_extraction.py
def test_extraction_prompt_rendering():
    # Arrange: Create in-memory loader
    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test prompt",
            created="2025-01-23",
        ),
        variables={
            "name": PromptVariable(
                type="str",
                required=True,
                description="Test name",
            ),
        },
        system_prompt="Hello, {{ name }}!",
        user_prompt="Extract data.",
    )

    loader = InMemoryPromptLoader(templates={"test": template})

    # Act: Render prompt
    system, user = loader.load("test").render(name="World")

    # Assert
    assert system == "Hello, World!"
    assert user == "Extract data."
```

## Design Rationale

### Why YAML Instead of JSON?

**Human-Friendliness**:

- Better for multi-line strings
- Comments supported
- Less verbose
- Standard for config files

### Why Jinja2 Instead of f-strings?

**Power + Safety**:

- Conditional logic (`{% if %}`)
- Loops (`{% for %}`)
- Filters (`{{ value|upper }}`)
- Strict undefined checking
- Industry standard

### Why Separate Metadata?

**Documentation + Versioning**:

- Track prompt changes over time
- Auto-generate documentation
- Prompt attribution
- Change management

### Why Variable Definitions?

**Discoverability + Validation**:

- Know what variables are available
- Type documentation
- Example values
- Required vs. optional
- Auto-generated docs

## CLI Commands

```bash
# List all prompts
extractor prompt list

# Show prompt details
extractor prompt show entity_extraction

# Generate documentation
extractor prompt docs --output ./docs/prompts/

# Validate prompt syntax
extractor prompt validate entity_extraction

# Test prompt rendering
extractor prompt test entity_extraction \
  --var file_paths='["/data/test.yaml"]' \
  --var schema_dir='/schemas'
```

## Testing Contract

All implementations of `PromptLoader` MUST pass this test suite:

```python
# tests/contracts/test_prompt_loader_contract.py
import pytest
from typing import Type

@pytest.mark.parametrize("loader_class", [
    DiskPromptLoader,
    InMemoryPromptLoader,
])
def test_prompt_loader_contract(loader_class: Type[PromptLoader], tmp_path: Path):
    """All PromptLoader implementations must satisfy this contract."""
    loader = create_loader(loader_class, tmp_path)

    # List templates
    templates = loader.list_templates()
    assert isinstance(templates, list)

    # Load template
    if len(templates) > 0:
        template = loader.load(templates[0])
        assert isinstance(template, PromptTemplate)

        # Render template
        system, user = template.render(**get_test_variables(template))
        assert isinstance(system, str)
        assert isinstance(user, str)
```

## Migration Path

**Phase 1 (Skateboard)**: Basic templates

- DiskPromptLoader
- Core templates (extraction, deduplication)
- Basic variable types

**Phase 2 (Scooter)**: Enhanced features

- Template validation CLI
- Prompt versioning tracking
- Auto-generated docs

**Phase 3 (Bicycle)**: Advanced features

- Prompt A/B testing framework
- Usage analytics (which prompts used)
- Prompt performance tracking

**Phase 4 (Car)**: Enterprise features

- Prompt registry service
- Centralized prompt management
- Prompt approval workflows

## References

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [YAML Specification](https://yaml.org/spec/)
- [Semantic Versioning](https://semver.org/)
