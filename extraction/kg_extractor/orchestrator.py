"""Main extraction orchestrator coordinating all components."""

import time
from pathlib import Path
from typing import Callable

from kg_extractor.agents.extraction import ExtractionAgent
from kg_extractor.chunking.hybrid_chunker import HybridChunker
from kg_extractor.config import ExtractionConfig
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
from kg_extractor.loaders.file_system import DiskFileSystem
from kg_extractor.models import Entity, ExtractionMetrics, ValidationError


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

        # 3. Process each chunk
        for chunk in chunks:
            # Extract entities from chunk
            if self.extraction_agent:
                # Use first context dir as schema dir if available
                schema_dir = (
                    self.config.context_dirs[0] if self.config.context_dirs else None
                )

                result = await self.extraction_agent.extract(
                    files=chunk.files,
                    chunk_id=chunk.chunk_id,
                    schema_dir=schema_dir,
                )

                # Collect entities and errors
                all_entities.extend(result.entities)
                all_validation_errors.extend(result.validation_errors)

            chunks_processed += 1

            # Report progress
            if self.progress_callback:
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
