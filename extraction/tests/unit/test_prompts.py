"""Unit tests for prompt template system."""

import pytest


def test_prompt_variable_model():
    """Test PromptVariable model."""
    from kg_extractor.prompts.models import PromptVariable

    var = PromptVariable(
        type="str",
        required=True,
        description="Test variable",
        example="test_value",
    )

    assert var.type == "str"
    assert var.required is True
    assert var.description == "Test variable"
    assert var.example == "test_value"
    assert var.default is None


def test_prompt_variable_with_default():
    """Test PromptVariable with default value."""
    from kg_extractor.prompts.models import PromptVariable

    var = PromptVariable(
        type="int",
        required=False,
        default=100,
        description="Optional variable",
    )

    assert var.default == 100
    assert var.required is False


def test_prompt_metadata_model():
    """Test PromptMetadata model."""
    from kg_extractor.prompts.models import PromptMetadata

    metadata = PromptMetadata(
        name="test_prompt",
        version="1.0.0",
        description="Test prompt template",
        created="2025-01-23",
    )

    assert metadata.name == "test_prompt"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test prompt template"
    assert metadata.author == "KG Extraction Team"  # Default
    assert metadata.created == "2025-01-23"
    assert metadata.updated is None


def test_prompt_template_basic_rendering():
    """Test PromptTemplate basic rendering."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "name": PromptVariable(
                type="str",
                required=True,
                description="User name",
            )
        },
        system_prompt="Hello, {{ name }}!",
        user_prompt="Please respond.",
    )

    system, user = template.render(name="World")

    assert system == "Hello, World!"
    assert user == "Please respond."


def test_prompt_template_missing_required_variable():
    """Test PromptTemplate fails with missing required variable."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "name": PromptVariable(
                type="str",
                required=True,
                description="User name",
            )
        },
        system_prompt="Hello, {{ name }}!",
        user_prompt="Please respond.",
    )

    with pytest.raises(ValueError, match="Missing required variables: name"):
        template.render()


def test_prompt_template_with_default_value():
    """Test PromptTemplate uses default values."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "name": PromptVariable(
                type="str",
                required=False,
                default="Default Name",
                description="User name",
            )
        },
        system_prompt="Hello, {{ name }}!",
        user_prompt="Please respond.",
    )

    system, user = template.render()

    assert system == "Hello, Default Name!"


def test_prompt_template_with_jinja2_loop():
    """Test PromptTemplate with Jinja2 loops."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "files": PromptVariable(
                type="list[str]",
                required=True,
                description="List of files",
            )
        },
        system_prompt="Files:\n{% for f in files %}\n- {{ f }}\n{% endfor %}",
        user_prompt="Process files.",
    )

    system, user = template.render(files=["file1.py", "file2.py"])

    assert "- file1.py" in system
    assert "- file2.py" in system


def test_prompt_template_with_jinja2_conditional():
    """Test PromptTemplate with Jinja2 conditionals."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "schema_dir": PromptVariable(
                type="str",
                required=False,
                default=None,
                description="Schema directory",
            )
        },
        system_prompt="{% if schema_dir %}Schema: {{ schema_dir }}{% else %}No schema{% endif %}",
        user_prompt="Extract.",
    )

    # With schema_dir
    system, _ = template.render(schema_dir="/schemas")
    assert system == "Schema: /schemas"

    # Without schema_dir
    system, _ = template.render()
    assert system == "No schema"


def test_prompt_template_undefined_variable_error():
    """Test PromptTemplate fails on undefined variables."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        TemplateError,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Hello, {{ undefined_var }}!",
        user_prompt="Please respond.",
    )

    with pytest.raises(TemplateError, match="Failed to render template"):
        template.render()


def test_prompt_template_generate_documentation():
    """Test PromptTemplate.generate_documentation()."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test_prompt",
            version="1.0.0",
            description="A test prompt",
            author="Test Author",
            created="2025-01-23",
            updated="2025-01-24",
        ),
        variables={
            "name": PromptVariable(
                type="str",
                required=True,
                description="User name",
                example="Alice",
            ),
            "count": PromptVariable(
                type="int",
                required=False,
                default=10,
                description="Item count",
                example=5,
            ),
        },
        system_prompt="System prompt",
        user_prompt="User prompt",
    )

    doc = template.generate_documentation()

    assert "# test_prompt (v1.0.0)" in doc
    assert "A test prompt" in doc
    assert "**Author**: Test Author" in doc
    assert "**Created**: 2025-01-23" in doc
    assert "**Updated**: 2025-01-24" in doc
    assert "### `name`" in doc
    assert "- **Type**: `str`" in doc
    assert "- **Required**: Yes" in doc
    assert "- **Description**: User name" in doc
    assert "- **Example**: `Alice`" in doc
    assert "### `count`" in doc
    assert "- **Required**: No" in doc
    assert "- **Default**: `10`" in doc


def test_prompt_template_list_variables():
    """Test PromptTemplate.list_variables()."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "var1": PromptVariable(type="str", description="Variable 1"),
            "var2": PromptVariable(type="int", description="Variable 2"),
        },
        system_prompt="Test",
        user_prompt="Test",
    )

    variables = template.list_variables()

    assert set(variables) == {"var1", "var2"}


def test_prompt_template_get_variable():
    """Test PromptTemplate.get_variable()."""
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "name": PromptVariable(type="str", description="User name"),
        },
        system_prompt="Test",
        user_prompt="Test",
    )

    var = template.get_variable("name")
    assert var.type == "str"
    assert var.description == "User name"

    with pytest.raises(KeyError, match="Variable not found: missing"):
        template.get_variable("missing")


def test_disk_prompt_loader_load():
    """Test DiskPromptLoader.load()."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    # Create temp template file
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        # Create test template
        template_file = template_dir / "test.yaml"
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test template"
  created: "2025-01-23"

variables:
  name:
    type: str
    required: true
    description: "User name"

system_prompt: "Hello, {{ name }}!"
user_prompt: "Please respond."
"""
        )

        loader = DiskPromptLoader(template_dir=template_dir)
        template = loader.load("test")

        assert template.metadata.name == "test"
        assert template.metadata.version == "1.0.0"
        assert "name" in template.variables

        # Test rendering
        system, user = template.render(name="World")
        assert system == "Hello, World!"


def test_disk_prompt_loader_load_not_found():
    """Test DiskPromptLoader.load() with non-existent template."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        loader = DiskPromptLoader(template_dir=Path(tmpdir))

        with pytest.raises(FileNotFoundError, match="Prompt template not found"):
            loader.load("nonexistent")


def test_disk_prompt_loader_list_templates():
    """Test DiskPromptLoader.list_templates()."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        # Create test templates
        (template_dir / "template1.yaml").write_text(
            "metadata:\n  name: template1\n  version: '1.0.0'\n  description: 'Test'\n  created: '2025-01-23'\nvariables: {}\nsystem_prompt: 'Test'\nuser_prompt: 'Test'"
        )  # pragma: allowlist secret
        (template_dir / "template2.yaml").write_text(
            "metadata:\n  name: template2\n  version: '1.0.0'\n  description: 'Test'\n  created: '2025-01-23'\nvariables: {}\nsystem_prompt: 'Test'\nuser_prompt: 'Test'"
        )  # pragma: allowlist secret

        loader = DiskPromptLoader(template_dir=template_dir)
        templates = loader.list_templates()

        assert templates == ["template1", "template2"]


def test_disk_prompt_loader_caching():
    """Test DiskPromptLoader caches loaded templates."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        template_file = template_dir / "test.yaml"
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test"
  created: "2025-01-23"

variables: {}
system_prompt: "Original"
user_prompt: "Test"
"""
        )

        loader = DiskPromptLoader(template_dir=template_dir)

        # Load first time
        template1 = loader.load("test")
        assert template1.system_prompt == "Original"

        # Modify file
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test"
  created: "2025-01-23"

variables: {}
system_prompt: "Modified"
user_prompt: "Test"
"""
        )

        # Load again - should be cached
        template2 = loader.load("test")
        assert template2.system_prompt == "Original"  # Still cached


def test_disk_prompt_loader_reload():
    """Test DiskPromptLoader.reload() bypasses cache."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        template_file = template_dir / "test.yaml"
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test"
  created: "2025-01-23"

variables: {}
system_prompt: "Original"
user_prompt: "Test"
"""
        )

        loader = DiskPromptLoader(template_dir=template_dir)

        # Load first time
        template1 = loader.load("test")
        assert template1.system_prompt == "Original"

        # Modify file
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test"
  created: "2025-01-23"

variables: {}
system_prompt: "Modified"
user_prompt: "Test"
"""
        )

        # Reload - should bypass cache
        template2 = loader.reload("test")
        assert template2.system_prompt == "Modified"


def test_disk_prompt_loader_clear_cache():
    """Test DiskPromptLoader.clear_cache()."""
    from pathlib import Path

    from kg_extractor.prompts.loader import DiskPromptLoader

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        template_file = template_dir / "test.yaml"
        template_file.write_text(
            """
metadata:
  name: test
  version: "1.0.0"
  description: "Test"
  created: "2025-01-23"

variables: {}
system_prompt: "Test"
user_prompt: "Test"
"""
        )

        loader = DiskPromptLoader(template_dir=template_dir)
        loader.load("test")

        assert len(loader._cache) == 1

        loader.clear_cache()

        assert len(loader._cache) == 0


def test_in_memory_prompt_loader_load():
    """Test InMemoryPromptLoader.load()."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={"name": PromptVariable(type="str", description="Name")},
        system_prompt="Hello, {{ name }}!",
        user_prompt="Test",
    )

    loader = InMemoryPromptLoader(templates={"test": template})
    loaded = loader.load("test")

    assert loaded.metadata.name == "test"
    system, _ = loaded.render(name="World")
    assert system == "Hello, World!"


def test_in_memory_prompt_loader_load_not_found():
    """Test InMemoryPromptLoader.load() with non-existent template."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader

    loader = InMemoryPromptLoader()

    with pytest.raises(FileNotFoundError, match="Template not found: missing"):
        loader.load("missing")


def test_in_memory_prompt_loader_list_templates():
    """Test InMemoryPromptLoader.list_templates()."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
    )

    template1 = PromptTemplate(
        metadata=PromptMetadata(
            name="test1",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Test",
        user_prompt="Test",
    )

    template2 = PromptTemplate(
        metadata=PromptMetadata(
            name="test2",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Test",
        user_prompt="Test",
    )

    loader = InMemoryPromptLoader(templates={"test1": template1, "test2": template2})
    templates = loader.list_templates()

    assert templates == ["test1", "test2"]


def test_in_memory_prompt_loader_add_template():
    """Test InMemoryPromptLoader.add_template()."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
    )

    loader = InMemoryPromptLoader()
    assert loader.list_templates() == []

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Test",
        user_prompt="Test",
    )

    loader.add_template("test", template)
    assert loader.list_templates() == ["test"]


def test_in_memory_prompt_loader_remove_template():
    """Test InMemoryPromptLoader.remove_template()."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Test",
        user_prompt="Test",
    )

    loader = InMemoryPromptLoader(templates={"test": template})
    assert loader.list_templates() == ["test"]

    loader.remove_template("test")
    assert loader.list_templates() == []


def test_in_memory_prompt_loader_clear():
    """Test InMemoryPromptLoader.clear()."""
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
    )

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={},
        system_prompt="Test",
        user_prompt="Test",
    )

    loader = InMemoryPromptLoader(templates={"test": template})
    assert len(loader.list_templates()) == 1

    loader.clear()
    assert len(loader.list_templates()) == 0
