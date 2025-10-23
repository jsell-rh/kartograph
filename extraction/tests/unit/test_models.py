"""Unit tests for data models."""

from pathlib import Path

import pytest
from pydantic import ValidationError


def test_entity_minimal():
    """Test Entity with minimal required fields."""
    from kg_extractor.models import Entity

    entity = Entity(
        id="urn:service:payment-api",
        type="Service",
        name="Payment API",
    )

    assert entity.id == "urn:service:payment-api"
    assert entity.type == "Service"
    assert entity.name == "Payment API"
    assert entity.description is None
    assert entity.properties == {}


def test_entity_with_properties():
    """Test Entity with additional properties."""
    from kg_extractor.models import Entity

    entity = Entity(
        id="urn:service:payment-api",
        type="Service",
        name="Payment API",
        description="Handles payment processing",
        properties={
            "language": "Python",
            "framework": "FastAPI",
            "team": "payments",
        },
    )

    assert entity.description == "Handles payment processing"
    assert entity.properties["language"] == "Python"
    assert entity.properties["framework"] == "FastAPI"
    assert entity.properties["team"] == "payments"


def test_entity_validates_urn_format():
    """Test Entity validates URN format (urn:type:identifier)."""
    from kg_extractor.models import Entity

    # Valid URN
    entity = Entity(
        id="urn:service:payment-api",
        type="Service",
        name="Payment API",
    )
    assert entity.id == "urn:service:payment-api"

    # Invalid URN - missing urn: prefix
    with pytest.raises(ValidationError, match="URN must start with 'urn:'"):
        Entity(
            id="service:payment-api",
            type="Service",
            name="Payment API",
        )

    # Invalid URN - not enough parts
    with pytest.raises(ValidationError, match="URN must have format"):
        Entity(
            id="urn:service",
            type="Service",
            name="Payment API",
        )


def test_entity_validates_type_name():
    """Test Entity validates type name (alphanumeric, starts with capital)."""
    from kg_extractor.models import Entity

    # Valid type names
    for type_name in ["Service", "APIEndpoint", "Database", "Team123"]:
        entity = Entity(
            id=f"urn:test:{type_name.lower()}",
            type=type_name,
            name="Test",
        )
        assert entity.type == type_name

    # Invalid type names
    invalid_types = [
        ("service", "must start with capital letter"),  # lowercase
        ("Service-Name", "must be alphanumeric"),  # hyphen
        ("Service Name", "must be alphanumeric"),  # space
        ("123Service", "must start with capital letter"),  # starts with number
    ]

    for invalid_type, error_pattern in invalid_types:
        with pytest.raises(ValidationError, match=error_pattern):
            Entity(
                id="urn:test:foo",
                type=invalid_type,
                name="Test",
            )


def test_entity_to_jsonld():
    """Test Entity.to_jsonld() generates correct JSON-LD."""
    from kg_extractor.models import Entity

    entity = Entity(
        id="urn:service:payment-api",
        type="Service",
        name="Payment API",
        description="Handles payments",
        properties={"language": "Python", "owner": "payments-team"},
    )

    jsonld = entity.to_jsonld()

    assert jsonld["@id"] == "urn:service:payment-api"
    assert jsonld["@type"] == "Service"
    assert jsonld["name"] == "Payment API"
    assert jsonld["description"] == "Handles payments"
    assert jsonld["language"] == "Python"
    assert jsonld["owner"] == "payments-team"
    # Should not include empty/None fields
    assert "@context" not in jsonld or jsonld["@context"] is not None


def test_entity_from_dict():
    """Test Entity.from_dict() creates entity from dictionary."""
    from kg_extractor.models import Entity

    data = {
        "@id": "urn:service:payment-api",
        "@type": "Service",
        "name": "Payment API",
        "description": "Handles payments",
        "language": "Python",
    }

    entity = Entity.from_dict(data)

    assert entity.id == "urn:service:payment-api"
    assert entity.type == "Service"
    assert entity.name == "Payment API"
    assert entity.description == "Handles payments"
    assert entity.properties["language"] == "Python"


def test_validation_error_model():
    """Test ValidationError model."""
    from kg_extractor.models import ValidationError as VError

    error = VError(
        entity_id="urn:service:payment-api",
        field="name",
        message="Name is required",
        severity="error",
    )

    assert error.entity_id == "urn:service:payment-api"
    assert error.field == "name"
    assert error.message == "Name is required"
    assert error.severity == "error"


def test_validation_error_severity_validation():
    """Test ValidationError validates severity levels."""
    from kg_extractor.models import ValidationError as VError

    # Valid severities
    for severity in ["error", "warning", "info"]:
        error = VError(
            entity_id="urn:test:foo",
            field="test",
            message="Test message",
            severity=severity,
        )
        assert error.severity == severity

    # Invalid severity
    with pytest.raises(ValidationError):
        VError(
            entity_id="urn:test:foo",
            field="test",
            message="Test message",
            severity="critical",
        )


def test_extraction_result_minimal():
    """Test ExtractionResult with minimal data."""
    from kg_extractor.models import ExtractionResult

    result = ExtractionResult(
        entities=[],
        chunk_id="chunk-001",
    )

    assert result.entities == []
    assert result.chunk_id == "chunk-001"
    assert result.validation_errors == []
    assert result.metadata == {}


def test_extraction_result_with_entities():
    """Test ExtractionResult with entities and validation errors."""
    from kg_extractor.models import Entity, ExtractionResult
    from kg_extractor.models import ValidationError as VError

    entities = [
        Entity(id="urn:service:api1", type="Service", name="API 1"),
        Entity(id="urn:service:api2", type="Service", name="API 2"),
    ]

    errors = [
        VError(
            entity_id="urn:service:api1",
            field="description",
            message="Missing description",
            severity="warning",
        ),
    ]

    result = ExtractionResult(
        entities=entities,
        chunk_id="chunk-001",
        validation_errors=errors,
        metadata={"files_processed": 5, "duration_seconds": 12.5},
    )

    assert len(result.entities) == 2
    assert result.entities[0].name == "API 1"
    assert len(result.validation_errors) == 1
    assert result.validation_errors[0].severity == "warning"
    assert result.metadata["files_processed"] == 5


def test_extraction_result_to_jsonld():
    """Test ExtractionResult.to_jsonld() generates graph."""
    from kg_extractor.models import Entity, ExtractionResult

    entities = [
        Entity(id="urn:service:api1", type="Service", name="API 1"),
        Entity(id="urn:service:api2", type="Service", name="API 2"),
    ]

    result = ExtractionResult(
        entities=entities,
        chunk_id="chunk-001",
    )

    jsonld = result.to_jsonld()

    assert "@context" in jsonld
    assert "@graph" in jsonld
    assert len(jsonld["@graph"]) == 2
    assert jsonld["@graph"][0]["@id"] == "urn:service:api1"
    assert jsonld["@graph"][1]["@id"] == "urn:service:api2"


def test_extraction_metrics_model():
    """Test ExtractionMetrics model."""
    from kg_extractor.models import ExtractionMetrics

    metrics = ExtractionMetrics(
        total_chunks=10,
        chunks_processed=5,
        entities_extracted=150,
        validation_errors=3,
        duration_seconds=120.5,
    )

    assert metrics.total_chunks == 10
    assert metrics.chunks_processed == 5
    assert metrics.entities_extracted == 150
    assert metrics.validation_errors == 3
    assert metrics.duration_seconds == 120.5


def test_extraction_metrics_computed_properties():
    """Test ExtractionMetrics computed properties."""
    from kg_extractor.models import ExtractionMetrics

    metrics = ExtractionMetrics(
        total_chunks=10,
        chunks_processed=5,
        entities_extracted=150,
        validation_errors=3,
        duration_seconds=120.0,
    )

    assert metrics.progress_percentage == 50.0
    assert metrics.entities_per_second == 1.25  # 150 / 120


def test_extraction_metrics_zero_duration():
    """Test ExtractionMetrics handles zero duration."""
    from kg_extractor.models import ExtractionMetrics

    metrics = ExtractionMetrics(
        total_chunks=10,
        chunks_processed=0,
        entities_extracted=0,
        validation_errors=0,
        duration_seconds=0.0,
    )

    assert metrics.entities_per_second == 0.0
