"""URN-based deduplication implementation."""

from typing import Any

from kg_extractor.config import DeduplicationConfig
from kg_extractor.deduplication.models import DeduplicationMetrics, DeduplicationResult
from kg_extractor.models import Entity


class URNDeduplicator:
    """
    URN-based deduplication strategy.

    Implements: DeduplicationStrategy protocol (via structural subtyping)

    Identifies duplicate entities by URN (@id) and merges them according
    to the configured strategy:
    - first: Keep the first occurrence
    - last: Keep the last occurrence
    - merge_predicates: Combine properties from all occurrences
    """

    def __init__(self, config: DeduplicationConfig):
        """
        Initialize URN deduplicator.

        Args:
            config: Deduplication configuration
        """
        self.config = config

    def deduplicate(self, entities: list[Entity]) -> DeduplicationResult:
        """
        Deduplicate entities by URN.

        Args:
            entities: List of entities to deduplicate

        Returns:
            DeduplicationResult with deduplicated entities and metrics
        """
        if not entities:
            return DeduplicationResult(
                entities=[],
                metrics=DeduplicationMetrics(
                    total_input_entities=0,
                    total_output_entities=0,
                    duplicates_found=0,
                    duplicates_merged=0,
                    merge_operations=0,
                ),
            )

        # Group entities by URN
        urn_groups: dict[str, list[Entity]] = {}
        urn_order: list[str] = []  # Track order of first occurrence

        for entity in entities:
            if entity.id not in urn_groups:
                urn_groups[entity.id] = []
                urn_order.append(entity.id)
            urn_groups[entity.id].append(entity)

        # Deduplicate each group according to strategy
        deduplicated_entities: list[Entity] = []
        duplicates_found = 0
        duplicates_merged = 0
        merge_operations = 0

        for urn in urn_order:
            group = urn_groups[urn]

            if len(group) == 1:
                # No duplicates
                deduplicated_entities.append(group[0])
            else:
                # Duplicates found
                duplicates_found += len(group) - 1

                if self.config.urn_merge_strategy == "first":
                    deduplicated_entities.append(group[0])
                    duplicates_merged += len(group) - 1
                elif self.config.urn_merge_strategy == "last":
                    deduplicated_entities.append(group[-1])
                    duplicates_merged += len(group) - 1
                elif self.config.urn_merge_strategy == "merge_predicates":
                    merged_entity = self._merge_entities(group)
                    deduplicated_entities.append(merged_entity)
                    duplicates_merged += len(group) - 1
                    merge_operations += len(group) - 1

        metrics = DeduplicationMetrics(
            total_input_entities=len(entities),
            total_output_entities=len(deduplicated_entities),
            duplicates_found=duplicates_found,
            duplicates_merged=duplicates_merged,
            merge_operations=merge_operations,
        )

        return DeduplicationResult(entities=deduplicated_entities, metrics=metrics)

    def _merge_entities(self, entities: list[Entity]) -> Entity:
        """
        Merge multiple entities with the same URN.

        Combines properties from all entities. When properties conflict,
        collects values into a list.

        Args:
            entities: List of entities with same URN to merge

        Returns:
            Merged entity
        """
        if len(entities) == 1:
            return entities[0]

        # Start with the first entity as base
        base = entities[0]
        merged_properties = dict(base.properties)
        merged_description = base.description

        # Merge properties from subsequent entities
        for entity in entities[1:]:
            # Use non-None description if available
            if entity.description is not None:
                merged_description = entity.description

            # Merge properties
            for key, value in entity.properties.items():
                if key in merged_properties:
                    # Property exists - handle conflict
                    existing_value = merged_properties[key]

                    if existing_value == value:
                        # Same value, no conflict
                        continue
                    elif isinstance(existing_value, list):
                        # Already a list, append if not present
                        if value not in existing_value:
                            existing_value.append(value)
                    else:
                        # Convert to list to handle conflict
                        merged_properties[key] = [existing_value, value]
                else:
                    # New property, add it
                    merged_properties[key] = value

        # Create merged entity
        return Entity(
            id=base.id,
            type=base.type,
            name=base.name,
            description=merged_description,
            properties=merged_properties,
        )
