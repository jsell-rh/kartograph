"""Deduplication strategies for entity merging."""

from kg_extractor.deduplication.models import DeduplicationMetrics, DeduplicationResult
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator

__all__ = ["DeduplicationMetrics", "DeduplicationResult", "URNDeduplicator"]
