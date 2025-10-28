"""Models for deduplication results and metrics."""

from pydantic import BaseModel, Field

from kg_extractor.models import Entity


class TypeNormalization(BaseModel):
    """Mapping of type variations to canonical names."""

    original_type: str = Field(description="Original type name from extraction")
    canonical_type: str = Field(description="Canonical type name to use")
    reason: str = Field(description="Why this normalization was chosen")


class DuplicateGroup(BaseModel):
    """Group of duplicate entities that should be merged."""

    primary_urn: str = Field(description="URN to keep as primary")
    duplicate_urns: list[str] = Field(description="URNs to merge into primary")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence this is a duplicate"
    )
    reason: str = Field(description="Why these are duplicates")


class URNCorrection(BaseModel):
    """Relationship reference correction."""

    entity_urn: str = Field(description="Entity containing the reference")
    predicate: str = Field(description="Predicate name")
    old_reference: str = Field(description="Incorrect URN reference")
    new_reference: str = Field(description="Corrected URN reference")
    reason: str = Field(description="Why this correction is needed")


class DeduplicationAnalysis(BaseModel):
    """Complete deduplication analysis from LLM."""

    type_normalizations: list[TypeNormalization] = Field(
        description="Type name normalizations to apply"
    )
    duplicate_groups: list[DuplicateGroup] = Field(
        description="Groups of duplicate entities to merge"
    )
    urn_corrections: list[URNCorrection] = Field(
        description="Relationship reference corrections"
    )
    summary: str = Field(description="Summary of changes made")


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
