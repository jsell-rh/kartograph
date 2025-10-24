"""Tests for enhanced validation (orphans, broken references)."""

import pytest

from kg_extractor.config import ValidationConfig
from kg_extractor.models import Entity
from kg_extractor.validation.entity_validator import (
    EntityValidator,
    extract_urn_references,
)
from kg_extractor.validation.report import ValidationReport


def test_extract_urn_references():
    """Test URN extraction from nested structures."""
    # Simple reference
    urns = extract_urn_references({"@id": "urn:Service:api-1"})
    assert "urn:Service:api-1" in urns

    # Nested in properties
    urns = extract_urn_references(
        {"owner": {"@id": "urn:User:alice"}, "dependsOn": {"@id": "urn:Service:db"}}
    )
    assert "urn:User:alice" in urns
    assert "urn:Service:db" in urns

    # Array of references
    urns = extract_urn_references(
        {"tags": ["tag1", "urn:Tag:important"], "refs": [{"@id": "urn:Other:ref"}]}
    )
    assert "urn:Tag:important" in urns
    assert "urn:Other:ref" in urns


def test_detect_orphaned_entities():
    """Test detection of orphaned entities (no relationships)."""
    config = ValidationConfig(detect_orphans=True)
    validator = EntityValidator(config)

    # Create entities
    orphan = Entity(
        id="urn:Service:orphan",
        type="Service",
        name="Orphan Service",
        properties={},  # No relationships
    )

    connected = Entity(
        id="urn:Service:connected",
        type="Service",
        name="Connected Service",
        properties={"dependsOn": {"@id": "urn:Service:db"}},
    )

    db = Entity(
        id="urn:Service:db",
        type="Service",
        name="Database",
        properties={},
    )

    entities = [orphan, connected, db]
    errors = validator.validate_graph(entities)

    # Should detect 2 orphans (orphan has no refs, db has no outgoing refs)
    orphan_errors = [e for e in errors if "orphaned" in e.message.lower()]
    assert len(orphan_errors) == 2
    orphaned_ids = {e.entity_id for e in orphan_errors}
    assert "urn:Service:orphan" in orphaned_ids
    assert "urn:Service:db" in orphaned_ids


def test_detect_broken_references():
    """Test detection of broken references."""
    config = ValidationConfig(detect_broken_refs=True)
    validator = EntityValidator(config)

    # Entity referencing non-existent entities
    broken = Entity(
        id="urn:Service:broken",
        type="Service",
        name="Broken Service",
        properties={
            "owner": {"@id": "urn:User:nonexistent"},
            "dependsOn": {"@id": "urn:Service:missing"},
        },
    )

    entities = [broken]
    errors = validator.validate_graph(entities)

    # Should detect 2 broken references
    broken_errors = [e for e in errors if "non-existent" in e.message.lower()]
    assert len(broken_errors) == 2
    assert any("urn:User:nonexistent" in e.message for e in broken_errors)
    assert any("urn:Service:missing" in e.message for e in broken_errors)


def test_validation_report_summary():
    """Test validation report generation."""
    from kg_extractor.models import ValidationError

    errors = [
        ValidationError(
            entity_id="urn:Service:api-1",
            field="@type",
            message="Type name must start with capital letter",
            severity="error",
        ),
        ValidationError(
            entity_id="urn:Service:api-2",
            field="relationships",
            message="Entity has no relationships to other entities (orphaned)",
            severity="warning",
        ),
        ValidationError(
            entity_id="urn:Service:api-3",
            field="reference",
            message="References non-existent entity: urn:User:missing",
            severity="error",
        ),
    ]

    report = ValidationReport(errors)

    # Check summary stats
    assert report.total_errors == 3
    assert report.total_error_severity == 2
    assert report.total_warning_severity == 1
    assert report.total_entities_with_errors == 3

    # Check exports work
    json_str = report.to_json()
    assert "summary" in json_str
    assert "total_issues" in json_str

    markdown = report.to_markdown()
    assert "# Validation Report" in markdown
    assert "Summary" in markdown

    text = report.to_text()
    assert "VALIDATION REPORT" in text
    assert "Errors: 2" in text
    assert "Warnings: 1" in text


def test_validation_config_flags():
    """Test validation config flags control behavior."""
    # With orphan detection disabled
    config_no_orphans = ValidationConfig(detect_orphans=False, detect_broken_refs=True)
    validator = EntityValidator(config_no_orphans)

    orphan = Entity(
        id="urn:Service:orphan",
        type="Service",
        name="Orphan",
        properties={},
    )

    errors = validator.validate_graph([orphan])
    assert len([e for e in errors if "orphaned" in e.message.lower()]) == 0

    # With broken ref detection disabled
    config_no_broken = ValidationConfig(detect_orphans=False, detect_broken_refs=False)
    validator = EntityValidator(config_no_broken)

    broken = Entity(
        id="urn:Service:broken",
        type="Service",
        name="Broken",
        properties={"ref": {"@id": "urn:Missing:entity"}},
    )

    errors = validator.validate_graph([broken])
    assert len([e for e in errors if "non-existent" in e.message.lower()]) == 0
