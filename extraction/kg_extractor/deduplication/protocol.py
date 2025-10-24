"""Deduplication strategy protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy testing with mock deduplicators
- Swappable deduplication strategies (urn, agent, hybrid)
"""

from typing import Protocol

from kg_extractor.deduplication.models import DeduplicationResult
from kg_extractor.models import Entity


class DeduplicationStrategy(Protocol):
    """
    Protocol for deduplication strategy implementations.

    Implementations must be able to identify and merge duplicate entities
    based on the configured strategy.
    """

    def deduplicate(self, entities: list[Entity]) -> DeduplicationResult:
        """
        Deduplicate a list of entities.

        Args:
            entities: List of entities to deduplicate

        Returns:
            DeduplicationResult with deduplicated entities and metrics
        """
        ...
