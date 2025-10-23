"""Main extraction orchestrator coordinating all components."""

import logging
import time
from pathlib import Path
from typing import Callable

from kg_extractor.agents.extraction import ExtractionAgent
from kg_extractor.chunking.hybrid_chunker import HybridChunker
from kg_extractor.chunking.models import Chunk
from kg_extractor.config import ExtractionConfig
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
from kg_extractor.exceptions import PromptTooLongError
from kg_extractor.loaders.file_system import DiskFileSystem
from kg_extractor.models import Entity, ExtractionMetrics, ValidationError

logger = logging.getLogger(__name__)


class OrchestrationResult:
    """Result of orchestration extraction."""

    def __init__(
        self,
        entities: list[Entity],
        metrics: ExtractionMetrics,
        validation_errors: list[ValidationError] | None = None,
    ):
        """
        Initialize orchestration result.

        Args:
            entities: Final deduplicated entities
            metrics: Extraction metrics
            validation_errors: Optional validation errors from all chunks
        """
        self.entities = entities
        self.metrics = metrics
        self.validation_errors = validation_errors or []


class ExtractionOrchestrator:
    """
    Main orchestrator coordinating the extraction workflow.

    Coordinates:
    1. File discovery
    2. Chunking
    3. Extraction (per chunk)
    4. Deduplication (across chunks)
    5. Metrics tracking
    6. Progress reporting
    """

    def __init__(
        self,
        config: ExtractionConfig,
        file_system: DiskFileSystem | None = None,
        chunker: HybridChunker | None = None,
        extraction_agent: ExtractionAgent | None = None,
        deduplicator: URNDeduplicator | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ):
        """
        Initialize extraction orchestrator.

        Args:
            config: Extraction configuration
            file_system: File system interface (optional, defaults to DiskFileSystem)
            chunker: Chunking strategy (optional, defaults to HybridChunker)
            extraction_agent: Extraction agent (optional, must be provided or created)
            deduplicator: Deduplication strategy (optional, defaults to URNDeduplicator)
            progress_callback: Optional callback(current, total, message) for progress
        """
        self.config = config
        self.file_system = file_system or DiskFileSystem()
        self.chunker = chunker or HybridChunker(config=config.chunking)
        self.extraction_agent = extraction_agent
        self.deduplicator = deduplicator or URNDeduplicator(config=config.deduplication)
        self.progress_callback = progress_callback

    async def extract(self) -> OrchestrationResult:
        """
        Execute the full extraction workflow.

        Returns:
            OrchestrationResult with deduplicated entities and metrics

        Raises:
            Exception: If extraction fails
        """
        start_time = time.time()

        # 1. Discover files
        files = self.file_system.list_files(
            directory=self.config.data_dir,
            pattern="**/*",
        )

        # 2. Create chunks
        chunks = self.chunker.create_chunks(files)

        # Initialize tracking
        all_entities: list[Entity] = []
        all_validation_errors: list[ValidationError] = []
        chunks_processed = 0

        # Convert to list for dynamic modification (chunk splitting on 413 errors)
        chunks_to_process = list(chunks)
        chunk_index = 0

        # 3. Process each chunk (with retry on prompt-too-long errors)
        while chunk_index < len(chunks_to_process):
            chunk = chunks_to_process[chunk_index]
            # Extract entities from chunk
            if self.extraction_agent:
                # Use first context dir as schema dir if available
                schema_dir = (
                    self.config.context_dirs[0] if self.config.context_dirs else None
                )

                # Prepare extraction kwargs (may include event_callback for verbose mode)
                extract_kwargs = {
                    "files": chunk.files,
                    "chunk_id": chunk.chunk_id,
                    "schema_dir": schema_dir,
                }

                # Add event_callback if configured (for verbose mode)
                if hasattr(self, "event_callback") and self.event_callback:
                    extract_kwargs["event_callback"] = self.event_callback

                try:
                    result = await self.extraction_agent.extract(**extract_kwargs)

                    # Collect entities and errors
                    all_entities.extend(result.entities)
                    all_validation_errors.extend(result.validation_errors)

                    # Report stats (for verbose mode progress display)
                    if hasattr(self, "stats_callback") and self.stats_callback:
                        self.stats_callback(
                            entities=result.entities,  # Pass actual entities for relationship counting
                            validation_errors=len(result.validation_errors),
                        )

                    chunks_processed += 1
                    chunk_index += 1

                except PromptTooLongError as e:
                    # Chunk is too large - split it and retry
                    logger.warning(
                        f"Chunk {chunk.chunk_id} exceeded prompt length limit "
                        f"({len(chunk.files)} files, {chunk.total_size_bytes / 1024 / 1024:.2f} MB). "
                        f"Splitting into smaller chunks..."
                    )

                    try:
                        # Split the chunk
                        first_half, second_half = chunk.split()

                        # Replace current chunk with the two halves
                        chunks_to_process[chunk_index] = first_half
                        chunks_to_process.insert(chunk_index + 1, second_half)

                        logger.info(
                            f"Split {chunk.chunk_id} into {first_half.chunk_id} "
                            f"({len(first_half.files)} files) and {second_half.chunk_id} "
                            f"({len(second_half.files)} files)"
                        )

                        # Don't increment chunk_index - retry with the first half
                        continue

                    except ValueError as split_error:
                        # Can't split further (single file too large)
                        logger.error(
                            f"Cannot split chunk {chunk.chunk_id} further: {split_error}. "
                            f"Skipping this chunk."
                        )
                        chunk_index += 1
                        continue

            else:
                # No extraction agent - just skip
                chunks_processed += 1
                chunk_index += 1

            # Report progress
            if self.progress_callback and chunks_processed > 0:
                self.progress_callback(
                    chunks_processed,
                    len(chunks),
                    f"Processed chunk {chunk.chunk_id}",
                )

        # 4. Deduplicate entities
        if all_entities:
            dedup_result = self.deduplicator.deduplicate(all_entities)
            final_entities = dedup_result.entities
        else:
            final_entities = []

        # 5. Calculate metrics
        duration = time.time() - start_time
        metrics = ExtractionMetrics(
            total_chunks=len(chunks),
            chunks_processed=chunks_processed,
            entities_extracted=len(final_entities),
            validation_errors=len(all_validation_errors),
            duration_seconds=duration,
        )

        return OrchestrationResult(
            entities=final_entities,
            metrics=metrics,
            validation_errors=all_validation_errors,
        )
