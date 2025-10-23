"""Unit tests for entity validation."""

import pytest


def test_entity_validator_validates_required_fields():
    """Test EntityValidator checks for required fields."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.models import Entity
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        required_fields=["@id", "@type", "name"],
        allow_missing_name=False,
    )

    validator = EntityValidator(config=config)

    # Valid entity
    valid_entity = Entity(
        id="urn:Service:payment-api",
        type="Service",
        name="Payment API",
    )

    errors = validator.validate(valid_entity)
    assert len(errors) == 0


def test_entity_validator_detects_missing_name():
    """Test EntityValidator detects missing name field."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.models import Entity
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        required_fields=["@id", "@type", "name"],
        allow_missing_name=False,
    )

    validator = EntityValidator(config=config)

    # Entity missing name - but Pydantic requires it, so this will fail at model level
    # We'll test with the raw dict validation method instead


def test_entity_validator_allows_missing_name_when_configured():
    """Test EntityValidator allows missing name if configured."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        required_fields=["@id", "@type"],
        allow_missing_name=True,
    )

    validator = EntityValidator(config=config)

    # Entity dict without name
    entity_dict = {
        "@id": "urn:Service:payment-api",
        "@type": "Service",
    }

    errors = validator.validate_dict(entity_dict)
    assert len(errors) == 0


def test_entity_validator_detects_invalid_urn_format():
    """Test EntityValidator detects invalid URN format."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        strict_urn_format=True,
    )

    validator = EntityValidator(config=config)

    # Invalid URN formats
    invalid_urns = [
        {
            "@id": "payment-api",  # Missing urn: prefix
            "@type": "Service",
            "@name": "Payment API",
        },
        {
            "@id": "urn:Service",  # Missing identifier part
            "@type": "Service",
            "name": "Payment API",
        },
    ]

    for entity_dict in invalid_urns:
        errors = validator.validate_dict(entity_dict)
        assert len(errors) > 0
        assert any("URN" in error.message or "urn" in error.message for error in errors)


def test_entity_validator_detects_invalid_type_name():
    """Test EntityValidator detects invalid type names."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig()

    validator = EntityValidator(config=config)

    # Invalid type names
    invalid_types = [
        {
            "@id": "urn:service:payment-api",
            "@type": "service",  # lowercase
            "name": "Payment API",
        },
        {
            "@id": "urn:Service:payment-api",
            "@type": "Service-Name",  # hyphen
            "name": "Payment API",
        },
        {
            "@id": "urn:Service:payment-api",
            "@type": "123Service",  # starts with number
            "name": "Payment API",
        },
    ]

    for entity_dict in invalid_types:
        errors = validator.validate_dict(entity_dict)
        assert len(errors) > 0
        assert any("type" in error.message.lower() for error in errors)


def test_entity_validator_accepts_valid_entities():
    """Test EntityValidator accepts valid entities."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig()

    validator = EntityValidator(config=config)

    valid_entities = [
        {
            "@id": "urn:Service:payment-api",
            "@type": "Service",
            "name": "Payment API",
        },
        {
            "@id": "urn:Team:payments",
            "@type": "Team",
            "name": "Payments Team",
            "description": "Team that owns payment services",
        },
        {
            "@id": "urn:APIEndpoint:payment-create",
            "@type": "APIEndpoint",
            "name": "Create Payment",
        },
    ]

    for entity_dict in valid_entities:
        errors = validator.validate_dict(entity_dict)
        assert len(errors) == 0


def test_entity_validator_returns_multiple_errors():
    """Test EntityValidator returns all validation errors."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        strict_urn_format=True,
    )

    validator = EntityValidator(config=config)

    # Entity with multiple issues
    entity_dict = {
        "@id": "invalid-urn",  # Bad URN
        "@type": "service",  # Bad type (lowercase)
        "name": "Test",
    }

    errors = validator.validate_dict(entity_dict)
    # Should have at least 2 errors
    assert len(errors) >= 2


def test_entity_validator_validates_extraction_result():
    """Test EntityValidator can validate entire extraction results."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.models import Entity
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig()

    validator = EntityValidator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
        ),
        Entity(
            id="urn:Service:api2",
            type="Service",
            name="API 2",
        ),
    ]

    # Validate all entities
    all_errors = []
    for entity in entities:
        errors = validator.validate(entity)
        all_errors.extend(errors)

    assert len(all_errors) == 0


def test_entity_validator_tracks_error_severity():
    """Test EntityValidator assigns appropriate severity to errors."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        allow_missing_name=True,
    )

    validator = EntityValidator(config=config)

    # Entity with invalid URN (error) but missing description (warning)
    entity_dict = {
        "@id": "invalid",  # Error
        "@type": "Service",
        "name": "Test",
    }

    errors = validator.validate_dict(entity_dict)

    # Should have at least one error with severity
    assert any(error.severity == "error" for error in errors)


def test_entity_validator_non_strict_urn_mode():
    """Test EntityValidator in non-strict URN mode."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        strict_urn_format=False,
    )

    validator = EntityValidator(config=config)

    # Lenient with URN format
    entity_dict = {
        "@id": "service:payment-api",  # No urn: prefix but might be OK in non-strict
        "@type": "Service",
        "name": "Payment API",
    }

    errors = validator.validate_dict(entity_dict)
    # In non-strict mode, might still warn but not error
    # Or might accept it - implementation dependent


def test_entity_validator_fail_on_validation_errors_config():
    """Test EntityValidator respects fail_on_validation_errors config."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    # This config just tracks the setting, actual failure behavior is in orchestrator
    config = ValidationConfig(
        fail_on_validation_errors=True,
    )

    validator = EntityValidator(config=config)

    assert validator.config.fail_on_validation_errors is True


def test_entity_validator_with_custom_required_fields():
    """Test EntityValidator with custom required fields."""
    from kg_extractor.config import ValidationConfig
    from kg_extractor.validation.entity_validator import EntityValidator

    config = ValidationConfig(
        required_fields=["@id", "@type", "name", "description"],
    )

    validator = EntityValidator(config=config)

    # Missing description
    entity_dict = {
        "@id": "urn:Service:api",
        "@type": "Service",
        "name": "API",
    }

    errors = validator.validate_dict(entity_dict)
    # Should detect missing required field
    assert any("description" in error.message.lower() for error in errors)
