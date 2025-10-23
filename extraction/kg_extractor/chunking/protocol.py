"""Chunking strategy protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy testing with mock chunkers
- Swappable chunking strategies (hybrid, directory, size, count, etc.)
"""

from pathlib import Path
from typing import Protocol

from kg_extractor.chunking.models import Chunk


class ChunkingStrategy(Protocol):
    """
    Protocol for chunking strategy implementations.

    Implementations must be able to divide a list of files into chunks
    based on the configured strategy.
    """

    def create_chunks(self, files: list[Path]) -> list[Chunk]:
        """
        Create chunks from a list of files.

        Args:
            files: List of file paths to chunk

        Returns:
            List of chunks, each containing a subset of files
        """
        ...
