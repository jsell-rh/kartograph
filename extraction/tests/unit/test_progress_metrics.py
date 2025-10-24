"""Tests for progress display graph metrics."""

import tempfile
from pathlib import Path

import pytest

from kg_extractor.models import Entity
from kg_extractor.progress import ProgressDisplay


def test_relationship_counting_simple():
    """Test counting relationships in entities."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    # Create entities with relationships
    entities = [
        Entity(
            id="urn:service:api",
            type="Service",
            name="API Service",
            properties={
                "owner": {"@id": "urn:team:backend"},
                "dependsOn": {"@id": "urn:service:database"},
            },
        ),
        Entity(
            id="urn:team:backend",
            type="Team",
            name="Backend Team",
            properties={
                "manages": {"@id": "urn:service:api"},
            },
        ),
    ]

    display.update_stats(entities=entities)

    # Should count 3 relationships total (2 from first entity, 1 from second)
    assert display.stats["entities"] == 2
    assert display.stats["relationships"] == 3


def test_relationship_counting_with_lists():
    """Test counting relationships when properties contain lists."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    entities = [
        Entity(
            id="urn:service:frontend",
            type="Service",
            name="Frontend Service",
            properties={
                "dependsOn": [
                    {"@id": "urn:service:api"},
                    {"@id": "urn:service:auth"},
                    {"@id": "urn:service:cache"},
                ],
                "owner": {"@id": "urn:team:frontend"},
            },
        ),
    ]

    display.update_stats(entities=entities)

    # Should count 4 relationships (3 in list + 1 single)
    assert display.stats["entities"] == 1
    assert display.stats["relationships"] == 4


def test_relationship_counting_ignores_non_references():
    """Test that non-reference properties are not counted as relationships."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    entities = [
        Entity(
            id="urn:service:api",
            type="Service",
            name="API Service",
            properties={
                "version": "1.0.0",  # Not a reference
                "tags": ["python", "api"],  # List but not references
                "config": {"timeout": 30},  # Dict but no @id
                "owner": {"@id": "urn:team:backend"},  # This IS a reference
            },
        ),
    ]

    display.update_stats(entities=entities)

    # Should count only 1 relationship
    assert display.stats["entities"] == 1
    assert display.stats["relationships"] == 1


def test_average_degree_calculation():
    """Test average degree calculation."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    # Create entities with varying numbers of relationships
    entities = [
        Entity(
            id="urn:service:a",
            type="Service",
            name="Service A",
            properties={
                "dependsOn": [
                    {"@id": "urn:service:b"},
                    {"@id": "urn:service:c"},
                ]
            },
        ),
        Entity(
            id="urn:service:b",
            type="Service",
            name="Service B",
            properties={"dependsOn": {"@id": "urn:service:c"}},
        ),
        Entity(
            id="urn:service:c",
            type="Service",
            name="Service C",
            properties={},  # No relationships
        ),
    ]

    display.update_stats(entities=entities)

    # Total: 3 entities, 3 relationships
    # Average degree: 3 / 3 = 1.0
    assert display.stats["entities"] == 3
    assert display.stats["relationships"] == 3
    assert display.stats["average_degree"] == 1.0


def test_graph_density_calculation():
    """Test graph density calculation."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    # 3 entities with 2 relationships
    entities = [
        Entity(
            id="urn:service:a",
            type="Service",
            name="Service A",
            properties={"dependsOn": {"@id": "urn:service:b"}},
        ),
        Entity(
            id="urn:service:b",
            type="Service",
            name="Service B",
            properties={"dependsOn": {"@id": "urn:service:c"}},
        ),
        Entity(
            id="urn:service:c",
            type="Service",
            name="Service C",
            properties={},
        ),
    ]

    display.update_stats(entities=entities)

    # For directed graph: density = edges / (n * (n-1))
    # n = 3, edges = 2
    # Possible edges = 3 * 2 = 6
    # Density = 2 / 6 = 0.3333...
    assert display.stats["entities"] == 3
    assert display.stats["relationships"] == 2
    assert abs(display.stats["graph_density"] - 0.3333) < 0.0001


def test_graph_metrics_with_no_entities():
    """Test graph metrics when there are no entities."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    display.update_stats(entities=[])

    assert display.stats["entities"] == 0
    assert display.stats["relationships"] == 0
    assert display.stats["average_degree"] == 0.0
    assert display.stats["graph_density"] == 0.0


def test_graph_metrics_with_single_entity():
    """Test graph metrics with only one entity."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    entities = [
        Entity(
            id="urn:service:a",
            type="Service",
            name="Service A",
            properties={"external": {"@id": "urn:external:b"}},
        )
    ]

    display.update_stats(entities=entities)

    # With only 1 entity, density is 0 (can't compute n*(n-1))
    assert display.stats["entities"] == 1
    assert display.stats["relationships"] == 1
    assert display.stats["average_degree"] == 1.0
    assert display.stats["graph_density"] == 0.0


def test_incremental_stats_updates():
    """Test that stats accumulate correctly across multiple updates."""
    display = ProgressDisplay(total_chunks=2, verbose=True)

    # First batch
    batch1 = [
        Entity(
            id="urn:service:a",
            type="Service",
            name="Service A",
            properties={"owner": {"@id": "urn:team:a"}},
        )
    ]

    display.update_stats(entities=batch1)

    assert display.stats["entities"] == 1
    assert display.stats["relationships"] == 1

    # Second batch
    batch2 = [
        Entity(
            id="urn:service:b",
            type="Service",
            name="Service B",
            properties={
                "owner": {"@id": "urn:team:a"},
                "dependsOn": {"@id": "urn:service:a"},
            },
        )
    ]

    display.update_stats(entities=batch2)

    # Should accumulate
    assert display.stats["entities"] == 2
    assert display.stats["relationships"] == 3

    # Metrics should be recalculated
    # Average degree = 3 / 2 = 1.5
    assert display.stats["average_degree"] == 1.5

    # Density = 3 / (2 * 1) = 1.5 (can exceed 1 in directed graphs with self-loops or multiple edges)
    # Wait, actually for 2 nodes: possible edges = 2 * (2-1) = 2
    # Density = 3 / 2 = 1.5
    assert display.stats["graph_density"] == 1.5


def test_file_list_display_in_chunk_info():
    """Test that file list is properly stored in chunk info."""
    display = ProgressDisplay(total_chunks=1, verbose=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(3):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)

        display.update_chunk(
            chunk_num=1, chunk_id="chunk-000", files=files, size_mb=0.01
        )

        assert display.current_chunk_info["files"] == files
        assert len(display.current_chunk_info["files"]) == 3
