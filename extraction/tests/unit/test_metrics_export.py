"""Tests for metrics export functionality."""

from pathlib import Path

import pytest

from kg_extractor.models import Entity, ExtractionMetrics
from kg_extractor.output.metrics import MetricsExporter


def test_metrics_export_basic():
    """Test basic metrics export to dict."""
    metrics = ExtractionMetrics(
        total_chunks=10,
        chunks_processed=10,
        entities_extracted=100,
        validation_errors=5,
        duration_seconds=120.0,
    )

    exporter = MetricsExporter(metrics)
    data = exporter.to_dict()

    # Check extraction data
    assert data["extraction"]["total_chunks"] == 10
    assert data["extraction"]["chunks_processed"] == 10
    assert data["extraction"]["entities_extracted"] == 100
    assert data["extraction"]["validation_errors"] == 5
    assert data["extraction"]["duration_seconds"] == 120.0

    # Check performance metrics
    assert data["performance"]["chunks_per_second"] == pytest.approx(10 / 120)
    assert data["performance"]["entities_per_second"] == pytest.approx(100 / 120)

    # Check quality metrics
    assert data["quality"]["validation_pass_rate"] == pytest.approx(0.95)


def test_metrics_export_with_entities():
    """Test metrics export with entity analysis."""
    metrics = ExtractionMetrics(
        total_chunks=5,
        chunks_processed=5,
        entities_extracted=20,
        validation_errors=0,
        duration_seconds=60.0,
    )

    entities = [
        Entity(
            id="urn:Service:api-1",
            type="Service",
            name="API 1",
            properties={"owner": {"@id": "urn:User:alice"}},
        ),
        Entity(
            id="urn:Service:api-2",
            type="Service",
            name="API 2",
            properties={"owner": {"@id": "urn:User:bob"}},
        ),
        Entity(id="urn:User:alice", type="User", name="Alice", properties={}),
        Entity(id="urn:User:bob", type="User", name="Bob", properties={}),
    ]

    exporter = MetricsExporter(metrics, entities)
    data = exporter.to_dict()

    # Check entity type counts
    assert data["entities_by_type"]["Service"] == 2
    assert data["entities_by_type"]["User"] == 2

    # Check relationship count (2 services have owner relationships)
    assert data["quality"]["relationships_per_entity"] == pytest.approx(2 / 4)


def test_metrics_export_json():
    """Test JSON export."""
    metrics = ExtractionMetrics(
        total_chunks=2,
        chunks_processed=2,
        entities_extracted=10,
        validation_errors=0,
        duration_seconds=30.0,
    )

    exporter = MetricsExporter(metrics)
    json_str = exporter.to_json()

    # Verify it's valid JSON
    import json

    data = json.loads(json_str)
    assert data["extraction"]["entities_extracted"] == 10


def test_metrics_export_csv():
    """Test CSV export."""
    metrics = ExtractionMetrics(
        total_chunks=3,
        chunks_processed=3,
        entities_extracted=15,
        validation_errors=1,
        duration_seconds=45.0,
    )

    entities = [
        Entity(
            id=f"urn:Service:api-{i}", type="Service", name=f"API {i}", properties={}
        )
        for i in range(15)
    ]

    exporter = MetricsExporter(metrics, entities)
    csv_str = exporter.to_csv()

    # Verify CSV format
    lines = csv_str.strip().split("\n")
    assert lines[0] == "Metric,Value"
    assert "Total Chunks,3" in csv_str
    assert "Entities Extracted,15" in csv_str

    # Should have entity type counts
    assert "Entity Type,Count" in csv_str
    assert "Service,15" in csv_str


def test_metrics_export_markdown():
    """Test Markdown export."""
    metrics = ExtractionMetrics(
        total_chunks=4,
        chunks_processed=4,
        entities_extracted=25,
        validation_errors=2,
        duration_seconds=90.0,
    )

    entities = [
        Entity(
            id=f"urn:Service:api-{i}",
            type="Service" if i < 15 else "Database",
            name=f"Entity {i}",
            properties={},
        )
        for i in range(25)
    ]

    exporter = MetricsExporter(metrics, entities)
    markdown = exporter.to_markdown()

    # Verify Markdown format
    assert "# Extraction Metrics" in markdown
    assert "## Extraction Summary" in markdown
    assert "**Entities Extracted**: 25" in markdown
    assert "## Entities by Type" in markdown
    assert "`Service`" in markdown
    assert "`Database`" in markdown


def test_metrics_export_save_formats(tmp_path):
    """Test saving metrics to different file formats."""
    metrics = ExtractionMetrics(
        total_chunks=1,
        chunks_processed=1,
        entities_extracted=5,
        validation_errors=0,
        duration_seconds=10.0,
    )

    exporter = MetricsExporter(metrics)

    # Save as JSON
    json_path = tmp_path / "metrics.json"
    exporter.save(json_path, format="json")
    assert json_path.exists()
    assert "entities_extracted" in json_path.read_text()

    # Save as CSV
    csv_path = tmp_path / "metrics.csv"
    exporter.save(csv_path, format="csv")
    assert csv_path.exists()
    assert "Metric,Value" in csv_path.read_text()

    # Save as Markdown
    md_path = tmp_path / "metrics.md"
    exporter.save(md_path, format="markdown")
    assert md_path.exists()
    assert "# Extraction Metrics" in md_path.read_text()


def test_metrics_export_zero_duration():
    """Test metrics with zero duration (edge case)."""
    metrics = ExtractionMetrics(
        total_chunks=0,
        chunks_processed=0,
        entities_extracted=0,
        validation_errors=0,
        duration_seconds=0.0,
    )

    exporter = MetricsExporter(metrics)
    data = exporter.to_dict()

    # Should not crash with division by zero
    assert data["performance"]["chunks_per_second"] == 0
    assert data["performance"]["entities_per_second"] == 0
    assert data["quality"]["validation_pass_rate"] == 1.0
