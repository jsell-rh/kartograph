"""Main extraction orchestrator coordinating all components."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from kg_extractor.agents.extraction import ExtractionAgent
from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
from kg_extractor.checkpoint.models import Checkpoint
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
        checkpoint_store: DiskCheckpointStore | None = None,
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
            checkpoint_store: Checkpoint store (optional, created from config if enabled)
            progress_callback: Optional callback(current, total, message) for progress
        """
        self.config = config
        self.file_system = file_system or DiskFileSystem()
        self.chunker = chunker or HybridChunker(config=config.chunking)
        self.extraction_agent = extraction_agent
        self.deduplicator = deduplicator or URNDeduplicator(config=config.deduplication)
        self.progress_callback = progress_callback

        # Initialize checkpoint store if enabled
        if config.checkpoint.enabled and checkpoint_store is None:
            self.checkpoint_store: DiskCheckpointStore | None = DiskCheckpointStore(
                checkpoint_dir=config.checkpoint.checkpoint_dir
            )
        else:
            self.checkpoint_store = checkpoint_store

    async def extract(self) -> OrchestrationResult:
        """
        Execute the full extraction workflow.

        Supports resumption from checkpoints if enabled.

        Returns:
            OrchestrationResult with deduplicated entities and metrics

        Raises:
            Exception: If extraction fails
            ValueError: If checkpoint config doesn't match current config
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
        chunk_index = 0

        # Attempt to resume from checkpoint if requested
        if self.config.resume and self.checkpoint_store:
            checkpoint = self._load_checkpoint()
            if checkpoint:
                # Validate config compatibility
                current_hash = self.config.compute_hash()
                if checkpoint.config_hash != current_hash:
                    logger.warning(
                        f"Checkpoint config hash mismatch. "
                        f"Checkpoint: {checkpoint.config_hash}, Current: {current_hash}. "
                        f"Starting fresh extraction."
                    )
                else:
                    # Resume from checkpoint
                    logger.info(
                        f"Resuming from checkpoint: {checkpoint.chunks_processed}/{len(chunks)} chunks processed"
                    )
                    chunks_processed = checkpoint.chunks_processed
                    chunk_index = checkpoint.chunks_processed
                    all_entities = self._entities_from_checkpoint_data(checkpoint)
                    logger.info(f"Loaded {len(all_entities)} entities from checkpoint")

        # Convert to list for dynamic modification (chunk splitting on 413 errors)
        chunks_to_process = list(chunks)
        total_chunks = len(chunks_to_process)

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

                    # Save checkpoint if enabled and strategy allows
                    self._save_checkpoint_if_needed(
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        chunks_processed=chunks_processed,
                        all_entities=all_entities,
                    )

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

    def _load_checkpoint(self) -> Checkpoint | None:
        """
        Load the latest checkpoint if available.

        Returns:
            Latest checkpoint or None if no checkpoint exists
        """
        if not self.checkpoint_store:
            return None

        try:
            checkpoint = self.checkpoint_store.load_checkpoint("latest")
            if checkpoint:
                logger.info(
                    f"Found checkpoint with {checkpoint.entities_extracted} entities"
                )
            return checkpoint
        except FileNotFoundError:
            logger.info("No checkpoint found, starting from beginning")
            return None
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}. Starting from beginning.")
            return None

    def _save_checkpoint_if_needed(
        self,
        chunk_index: int,
        total_chunks: int,
        chunks_processed: int,
        all_entities: list[Entity],
    ) -> None:
        """
        Save checkpoint based on configured strategy.

        Args:
            chunk_index: Current chunk index
            total_chunks: Total number of chunks
            chunks_processed: Number of chunks processed so far
            all_entities: All entities extracted so far
        """
        if not self.checkpoint_store or not self.config.checkpoint.enabled:
            return

        should_save = False
        strategy = self.config.checkpoint.strategy

        if strategy == "per_chunk":
            # Save after every chunk
            should_save = True
        elif strategy == "every_n":
            # Save every N chunks
            if chunks_processed % self.config.checkpoint.every_n_chunks == 0:
                should_save = True
        # time_based strategy would need additional tracking

        if should_save:
            checkpoint = Checkpoint(
                checkpoint_id="latest",
                config_hash=self.config.compute_hash(),
                chunks_processed=chunks_processed,
                entities_extracted=len(all_entities),
                timestamp=datetime.now(),
                metadata={
                    "total_chunks": total_chunks,
                    "chunk_index": chunk_index,
                },
            )

            try:
                self.checkpoint_store.save_checkpoint(checkpoint)
                logger.debug(
                    f"Saved checkpoint: {chunks_processed}/{total_chunks} chunks, "
                    f"{len(all_entities)} entities"
                )
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")

    def _entities_from_checkpoint_data(self, checkpoint: Checkpoint) -> list[Entity]:
        """
        Convert checkpoint data back to Entity objects.

        Args:
            checkpoint: Checkpoint containing entity data

        Returns:
            List of Entity objects reconstructed from checkpoint

        Note:
            Currently checkpoints don't store entities, so this returns empty list.
            In future, we could serialize entities to checkpoint metadata.
        """
        # TODO: Implement entity serialization/deserialization in checkpoints
        # For now, return empty list - this means resumption will re-extract all entities
        # but skip already-processed chunks
        logger.warning(
            "Checkpoint entity restoration not yet implemented. "
            "Entities will be re-extracted on resume."
        )
        return []
