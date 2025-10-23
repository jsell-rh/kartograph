"""Unit tests for deduplication."""

import pytest


def test_urn_deduplicator_no_duplicates():
    """Test URN deduplicator with no duplicate entities."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

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

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 2
    assert result.metrics.total_input_entities == 2
    assert result.metrics.total_output_entities == 2
    assert result.metrics.duplicates_found == 0
    assert result.metrics.duplicates_merged == 0
    assert result.metrics.merge_operations == 0


def test_urn_deduplicator_first_strategy():
    """Test URN deduplicator with 'first' merge strategy."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="first",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1 - First",
            description="First description",
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1 - Second",
            description="Second description",
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    assert result.entities[0].name == "API 1 - First"
    assert result.entities[0].description == "First description"
    assert result.metrics.total_input_entities == 2
    assert result.metrics.total_output_entities == 1
    assert result.metrics.duplicates_found == 1
    assert result.metrics.duplicates_merged == 1


def test_urn_deduplicator_last_strategy():
    """Test URN deduplicator with 'last' merge strategy."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="last",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1 - First",
            description="First description",
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1 - Second",
            description="Second description",
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    assert result.entities[0].name == "API 1 - Second"
    assert result.entities[0].description == "Second description"
    assert result.metrics.total_input_entities == 2
    assert result.metrics.total_output_entities == 1
    assert result.metrics.duplicates_found == 1
    assert result.metrics.duplicates_merged == 1


def test_urn_deduplicator_merge_predicates_strategy():
    """Test URN deduplicator with 'merge_predicates' strategy."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            description="Service description",
            properties={"owner": "team1", "port": 8080},
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            description="Service description",
            properties={"region": "us-west", "environment": "prod"},
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    # Should merge properties from both entities
    merged_entity = result.entities[0]
    assert merged_entity.properties["owner"] == "team1"
    assert merged_entity.properties["port"] == 8080
    assert merged_entity.properties["region"] == "us-west"
    assert merged_entity.properties["environment"] == "prod"
    assert result.metrics.total_input_entities == 2
    assert result.metrics.total_output_entities == 1
    assert result.metrics.duplicates_found == 1
    assert result.metrics.duplicates_merged == 1
    assert result.metrics.merge_operations == 1


def test_urn_deduplicator_merge_predicates_with_conflicts():
    """Test merge_predicates strategy handles property conflicts."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            properties={"owner": "team1", "shared": "value1"},
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            properties={"owner": "team2", "shared": "value2"},
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    # For conflicts, later values should override (or collect into list)
    # Implementation choice: we'll collect conflicts into lists
    merged_entity = result.entities[0]
    # Owner should be a list with both values
    assert isinstance(merged_entity.properties["owner"], list)
    assert set(merged_entity.properties["owner"]) == {"team1", "team2"}


def test_urn_deduplicator_multiple_duplicate_groups():
    """Test deduplicator with multiple groups of duplicates."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="first",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(id="urn:Service:api1", type="Service", name="API 1 First"),
        Entity(id="urn:Service:api1", type="Service", name="API 1 Second"),
        Entity(id="urn:Service:api2", type="Service", name="API 2 First"),
        Entity(id="urn:Service:api2", type="Service", name="API 2 Second"),
        Entity(id="urn:Service:api3", type="Service", name="API 3"),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 3
    assert result.metrics.total_input_entities == 5
    assert result.metrics.total_output_entities == 3
    assert result.metrics.duplicates_found == 2
    assert result.metrics.duplicates_merged == 2

    # Verify first strategy kept the first occurrence
    api1 = next(e for e in result.entities if e.id == "urn:Service:api1")
    assert api1.name == "API 1 First"


def test_urn_deduplicator_empty_list():
    """Test deduplicator with empty entity list."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    result = deduplicator.deduplicate([])

    assert len(result.entities) == 0
    assert result.metrics.total_input_entities == 0
    assert result.metrics.total_output_entities == 0
    assert result.metrics.duplicates_found == 0


def test_urn_deduplicator_single_entity():
    """Test deduplicator with single entity."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
        )
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    assert result.metrics.total_input_entities == 1
    assert result.metrics.total_output_entities == 1
    assert result.metrics.duplicates_found == 0


def test_urn_deduplicator_preserves_order():
    """Test that deduplicator preserves entity order (first occurrence)."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="first",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(id="urn:Service:api1", type="Service", name="API 1"),
        Entity(id="urn:Service:api2", type="Service", name="API 2"),
        Entity(id="urn:Service:api3", type="Service", name="API 3"),
        Entity(id="urn:Service:api2", type="Service", name="API 2 Duplicate"),
    ]

    result = deduplicator.deduplicate(entities)

    # Should preserve order of first occurrence
    assert result.entities[0].id == "urn:Service:api1"
    assert result.entities[1].id == "urn:Service:api2"
    assert result.entities[2].id == "urn:Service:api3"


def test_urn_deduplicator_merge_with_none_values():
    """Test merge_predicates handles None values correctly."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            description=None,
            properties={"key1": "value1"},
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            description="Added description",
            properties={"key2": "value2"},
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    merged = result.entities[0]
    # Description from second entity should be used
    assert merged.description == "Added description"
    # Properties should be merged
    assert merged.properties["key1"] == "value1"
    assert merged.properties["key2"] == "value2"


def test_urn_deduplicator_three_way_merge():
    """Test merge_predicates with three duplicate entities."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
    from kg_extractor.models import Entity

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="merge_predicates",
    )

    deduplicator = URNDeduplicator(config=config)

    entities = [
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            properties={"a": "1"},
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            properties={"b": "2"},
        ),
        Entity(
            id="urn:Service:api1",
            type="Service",
            name="API 1",
            properties={"c": "3"},
        ),
    ]

    result = deduplicator.deduplicate(entities)

    assert len(result.entities) == 1
    merged = result.entities[0]
    assert merged.properties["a"] == "1"
    assert merged.properties["b"] == "2"
    assert merged.properties["c"] == "3"
    assert result.metrics.duplicates_found == 2
    assert result.metrics.duplicates_merged == 2
    assert result.metrics.merge_operations == 2


def test_urn_deduplicator_respects_config():
    """Test that deduplicator respects the configuration."""
    from kg_extractor.config import DeduplicationConfig
    from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator

    config = DeduplicationConfig(
        strategy="urn",
        urn_merge_strategy="last",
    )

    deduplicator = URNDeduplicator(config=config)

    assert deduplicator.config.urn_merge_strategy == "last"
