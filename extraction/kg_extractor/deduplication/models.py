"""Models for deduplication results and metrics."""

from pydantic import BaseModel, Field

from kg_extractor.models import Entity


class DeduplicationMetrics(BaseModel):
    """
    Metrics about deduplication process.

    Attributes:
        total_input_entities: Number of entities before deduplication
        total_output_entities: Number of entities after deduplication
        duplicates_found: Number of duplicate entities identified
        duplicates_merged: Number of entities merged (may differ from duplicates_found)
        merge_operations: Number of merge operations performed
    """

    total_input_entities: int = Field(ge=0)
    total_output_entities: int = Field(ge=0)
    duplicates_found: int = Field(ge=0)
    duplicates_merged: int = Field(ge=0)
    merge_operations: int = Field(ge=0)


class DeduplicationResult(BaseModel):
    """
    Result of deduplication operation.

    Attributes:
        entities: Deduplicated list of entities
        metrics: Deduplication metrics
    """

    entities: list[Entity]
    metrics: DeduplicationMetrics
