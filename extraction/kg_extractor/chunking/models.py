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

    def split(self) -> tuple["Chunk", "Chunk"]:
        """
        Split this chunk into two smaller chunks.

        Returns:
            Tuple of (first_half, second_half) chunks

        Raises:
            ValueError: If chunk has only one file (cannot split further)
        """
        if len(self.files) <= 1:
            raise ValueError(
                f"Cannot split chunk {self.chunk_id} - it has only {len(self.files)} file(s)"
            )

        # Split files in half
        mid = len(self.files) // 2
        first_files = self.files[:mid]
        second_files = self.files[mid:]

        # Calculate sizes for each half
        first_size = sum(f.stat().st_size for f in first_files if f.exists())
        second_size = sum(f.stat().st_size for f in second_files if f.exists())

        # Create two new chunks
        first_chunk = Chunk(
            chunk_id=f"{self.chunk_id}-a",
            files=first_files,
            total_size_bytes=first_size,
        )
        second_chunk = Chunk(
            chunk_id=f"{self.chunk_id}-b",
            files=second_files,
            total_size_bytes=second_size,
        )

        return first_chunk, second_chunk
