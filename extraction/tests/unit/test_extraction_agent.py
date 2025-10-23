"""Unit tests for extraction agent."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_extraction_agent_basic():
    """Test ExtractionAgent basic extraction."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.models import Entity
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    # Create mock LLM client
    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [
            {
                "@id": "urn:Service:api1",
                "@type": "Service",
                "name": "API 1",
            }
        ],
        "metadata": {
            "entity_count": 1,
            "types_discovered": ["Service"],
        },
    }

    # Create prompt loader
    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract from: {% for f in file_paths %}{{ f }}{% endfor %}",
        user_prompt="Extract entities.",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})

    # Create validator
    validator = EntityValidator(config=ValidationConfig())

    # Create agent
    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    # Extract
    result = await agent.extract(
        files=[Path("/test/file1.yaml")],
        schema_dir=None,
    )

    # Verify
    assert len(result.entities) == 1
    assert result.entities[0].id == "urn:Service:api1"
    assert result.entities[0].name == "API 1"
    assert result.validation_errors == []
    assert result.metadata["entity_count"] == 1


@pytest.mark.asyncio
async def test_extraction_agent_with_schema_dir():
    """Test ExtractionAgent with schema directory."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [],
        "metadata": {"entity_count": 0},
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            ),
            "schema_dir": PromptVariable(
                type="Path",
                required=False,
                default=None,
                description="Schema dir",
            ),
        },
        system_prompt="Files: {{ file_paths }} Schema: {{ schema_dir }}",
        user_prompt="Extract.",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    result = await agent.extract(
        files=[Path("/test/file1.yaml")],
        schema_dir=Path("/schemas"),
    )

    # Verify LLM was called with schema_dir
    mock_llm.extract_entities.assert_called_once()
    call_args = mock_llm.extract_entities.call_args
    assert call_args[1]["schema_dir"] == Path("/schemas")


@pytest.mark.asyncio
async def test_extraction_agent_validates_entities():
    """Test ExtractionAgent validates extracted entities."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    # Return entity with invalid URN (missing urn: prefix)
    mock_llm.extract_entities.return_value = {
        "entities": [
            {
                "@id": "invalid-urn",  # Invalid
                "@type": "Service",
                "name": "API 1",
            }
        ],
        "metadata": {"entity_count": 1},
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})

    # Use strict URN validation
    validator = EntityValidator(config=ValidationConfig(strict_urn_format=True))

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    result = await agent.extract(
        files=[Path("/test/file1.yaml")],
        schema_dir=None,
    )

    # Entity should still be returned but with validation errors
    assert len(result.entities) == 1
    assert len(result.validation_errors) > 0
    assert any("URN" in err.message for err in result.validation_errors)


@pytest.mark.asyncio
async def test_extraction_agent_handles_invalid_json():
    """Test ExtractionAgent handles invalid JSON from LLM."""
    from kg_extractor.agents.extraction import ExtractionAgent, ExtractionError
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    # Return invalid structure (missing entities field)
    mock_llm.extract_entities.return_value = {
        "invalid": "response",
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    with pytest.raises(ExtractionError, match="Missing 'entities' field"):
        await agent.extract(
            files=[Path("/test/file1.yaml")],
            schema_dir=None,
        )


@pytest.mark.asyncio
async def test_extraction_agent_handles_llm_error():
    """Test ExtractionAgent handles LLM errors."""
    from kg_extractor.agents.extraction import ExtractionAgent, ExtractionError
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.side_effect = Exception("LLM API error")

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    with pytest.raises(ExtractionError, match="LLM extraction failed"):
        await agent.extract(
            files=[Path("/test/file1.yaml")],
            schema_dir=None,
        )


@pytest.mark.asyncio
async def test_extraction_agent_empty_files_list():
    """Test ExtractionAgent with empty files list."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [],
        "metadata": {"entity_count": 0},
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    result = await agent.extract(
        files=[],
        schema_dir=None,
    )

    assert len(result.entities) == 0
    assert len(result.validation_errors) == 0


@pytest.mark.asyncio
async def test_extraction_agent_multiple_entities():
    """Test ExtractionAgent with multiple entities."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [
            {
                "@id": "urn:Service:api1",
                "@type": "Service",
                "name": "API 1",
            },
            {
                "@id": "urn:Service:api2",
                "@type": "Service",
                "name": "API 2",
            },
            {
                "@id": "urn:Team:platform",
                "@type": "Team",
                "name": "Platform Team",
            },
        ],
        "metadata": {
            "entity_count": 3,
            "types_discovered": ["Service", "Team"],
        },
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    result = await agent.extract(
        files=[Path("/test/file1.yaml"), Path("/test/file2.yaml")],
        schema_dir=None,
    )

    assert len(result.entities) == 3
    assert result.metadata["entity_count"] == 3
    assert set(result.metadata["types_discovered"]) == {"Service", "Team"}


@pytest.mark.asyncio
async def test_extraction_agent_preserves_entity_properties():
    """Test ExtractionAgent preserves all entity properties."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [
            {
                "@id": "urn:Service:api1",
                "@type": "Service",
                "name": "API 1",
                "description": "A test service",
                "port": 8080,
                "environment": "prod",
                "tags": ["api", "rest"],
            }
        ],
        "metadata": {"entity_count": 1},
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Extract",
        user_prompt="Extract",
    )
    prompt_loader = InMemoryPromptLoader(templates={"entity_extraction": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
    )

    result = await agent.extract(
        files=[Path("/test/file1.yaml")],
        schema_dir=None,
    )

    entity = result.entities[0]
    assert entity.description == "A test service"
    assert entity.properties["port"] == 8080
    assert entity.properties["environment"] == "prod"
    assert entity.properties["tags"] == ["api", "rest"]


@pytest.mark.asyncio
async def test_extraction_agent_uses_custom_prompt_template():
    """Test ExtractionAgent can use custom prompt template."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.config import ValidationConfig
    from kg_extractor.prompts.loader import InMemoryPromptLoader
    from kg_extractor.prompts.models import (
        PromptMetadata,
        PromptTemplate,
        PromptVariable,
    )
    from kg_extractor.validation.entity_validator import EntityValidator

    mock_llm = AsyncMock()
    mock_llm.extract_entities.return_value = {
        "entities": [],
        "metadata": {"entity_count": 0},
    }

    template = PromptTemplate(
        metadata=PromptMetadata(
            name="custom",
            version="1.0.0",
            description="Custom template",
            created="2025-01-23",
        ),
        variables={
            "file_paths": PromptVariable(
                type="list[Path]",
                required=True,
                description="Files",
            )
        },
        system_prompt="Custom extraction prompt",
        user_prompt="Custom user prompt",
    )
    prompt_loader = InMemoryPromptLoader(templates={"custom": template})
    validator = EntityValidator(config=ValidationConfig())

    agent = ExtractionAgent(
        llm_client=mock_llm,
        prompt_loader=prompt_loader,
        validator=validator,
        prompt_name="custom",
    )

    result = await agent.extract(
        files=[Path("/test/file1.yaml")],
        schema_dir=None,
    )

    # Verify custom template was used (LLM was called)
    mock_llm.extract_entities.assert_called_once()
