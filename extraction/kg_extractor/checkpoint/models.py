"""Checkpoint data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """
    Checkpoint for resumable extraction.

    Stores the state of an extraction run at a specific point in time,
    allowing the extraction to be resumed if interrupted.
    """

    checkpoint_id: str = Field(
        description="Unique identifier for this checkpoint (e.g., chunk ID)",
    )
    config_hash: str = Field(
        description="Hash of extraction configuration for validation",
    )
    chunks_processed: int = Field(
        ge=0,
        description="Number of chunks processed so far",
    )
    completed_chunk_ids: set[str] = Field(
        default_factory=set,
        description="Set of chunk IDs that have been successfully processed (for parallel resume)",
    )
    entities_extracted: int = Field(
        ge=0,
        description="Total number of entities extracted so far",
    )
    entities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Serialized entities (JSON-LD format) extracted so far",
    )
    timestamp: datetime = Field(
        description="When this checkpoint was created",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional checkpoint metadata (duration, errors, etc.)",
    )
