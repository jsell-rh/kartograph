"""Hybrid chunking strategy implementation.

Combines multiple strategies to create optimal chunks:
- Respects directory boundaries (keeps related files together)
- Honors target size limits
- Respects max file count per chunk
"""

from pathlib import Path

from kg_extractor.chunking.models import Chunk
from kg_extractor.config import ChunkingConfig


class HybridChunker:
    """
    Hybrid chunking strategy.

    Implements: ChunkingStrategy protocol (via structural subtyping)

    Creates chunks by balancing multiple constraints:
    - Directory boundaries (if enabled)
    - Target size in MB
    - Maximum files per chunk
    """

    def __init__(self, config: ChunkingConfig):
        """
        Initialize hybrid chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config
        self.target_size_bytes = config.target_size_mb * 1024 * 1024

    def create_chunks(self, files: list[Path]) -> list[Chunk]:
        """
        Create chunks from files using hybrid strategy.

        Args:
            files: List of file paths to chunk

        Returns:
            List of chunks
        """
        # Filter to only existing files
        existing_files = [f for f in files if f.exists()]

        if not existing_files:
            return []

        # Group by directory if needed
        if self.config.respect_directory_boundaries:
            file_groups = self._group_by_directory(existing_files)
        else:
            file_groups = [existing_files]

        # Create chunks from each group
        chunks = []
        chunk_counter = 0

        for group in file_groups:
            group_chunks = self._chunk_group(group, chunk_counter)
            chunks.extend(group_chunks)
            chunk_counter += len(group_chunks)

        return chunks

    def _group_by_directory(self, files: list[Path]) -> list[list[Path]]:
        """
        Group files by their parent directory.

        Args:
            files: List of file paths

        Returns:
            List of file groups (one per directory)
        """
        directory_groups: dict[Path, list[Path]] = {}

        for file_path in files:
            parent = file_path.parent
            if parent not in directory_groups:
                directory_groups[parent] = []
            directory_groups[parent].append(file_path)

        return list(directory_groups.values())

    def _chunk_group(self, files: list[Path], start_counter: int) -> list[Chunk]:
        """
        Create chunks from a group of files.

        Args:
            files: List of files to chunk (from same directory if boundaries enabled)
            start_counter: Starting chunk counter for unique IDs

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk_files: list[Path] = []
        current_chunk_size = 0
        chunk_counter = start_counter

        for file_path in files:
            try:
                file_size = file_path.stat().st_size
            except OSError:
                # Skip files that can't be stat'd
                continue

            # Check if adding this file would exceed limits
            would_exceed_size = current_chunk_size + file_size > self.target_size_bytes
            would_exceed_count = (
                len(current_chunk_files) >= self.config.max_files_per_chunk
            )

            # Start new chunk if limits would be exceeded and current chunk is not empty
            if current_chunk_files and (would_exceed_size or would_exceed_count):
                # Save current chunk
                chunks.append(
                    self._create_chunk(
                        chunk_id=f"chunk-{chunk_counter:03d}",
                        files=current_chunk_files,
                        total_size=current_chunk_size,
                    )
                )
                chunk_counter += 1

                # Start new chunk
                current_chunk_files = []
                current_chunk_size = 0

            # Add file to current chunk
            current_chunk_files.append(file_path)
            current_chunk_size += file_size

        # Save final chunk if it has files
        if current_chunk_files:
            chunks.append(
                self._create_chunk(
                    chunk_id=f"chunk-{chunk_counter:03d}",
                    files=current_chunk_files,
                    total_size=current_chunk_size,
                )
            )

        return chunks

    def _create_chunk(self, chunk_id: str, files: list[Path], total_size: int) -> Chunk:
        """
        Create a Chunk object.

        Args:
            chunk_id: Unique chunk identifier
            files: List of files in chunk
            total_size: Total size in bytes

        Returns:
            Chunk object
        """
        return Chunk(
            chunk_id=chunk_id,
            files=files,
            total_size_bytes=total_size,
        )
