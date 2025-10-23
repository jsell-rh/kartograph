"""Chunking data models."""

from pathlib import Path

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """
    A chunk of files to process together.

    Represents a group of files that should be processed in a single
    extraction operation.
    """

    chunk_id: str = Field(
        description="Unique identifier for this chunk",
    )
    files: list[Path] = Field(
        description="List of file paths in this chunk",
    )
    total_size_bytes: int = Field(
        ge=0,
        description="Total size of all files in bytes",
    )
