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
from kg_extractor.cost_estimator import CostEstimate, CostEstimator
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
from kg_extractor.exceptions import PromptTooLongError
from kg_extractor.loaders.file_system import DiskFileSystem
from kg_extractor.models import Entity, ExtractionMetrics, ValidationError
from kg_extractor.output.metrics import MetricsExporter
from kg_extractor.validation.entity_validator import EntityValidator
from kg_extractor.validation.report import ValidationReport

logger = logging.getLogger(__name__)


class OrchestrationResult:
    """Result of orchestration extraction."""

    def __init__(
        self,
        entities: list[Entity],
        metrics: ExtractionMetrics,
        validation_errors: list[ValidationError] | None = None,
        cost_estimate: CostEstimate | None = None,
    ):
        """
        Initialize orchestration result.

        Args:
            entities: Final deduplicated entities
            metrics: Extraction metrics
            validation_errors: Optional validation errors from all chunks
            cost_estimate: Optional cost estimate (if dry-run was performed first)
        """
        self.entities = entities
        self.metrics = metrics
        self.validation_errors = validation_errors or []
        self.cost_estimate = cost_estimate

    def get_validation_report(self) -> ValidationReport:
        """
        Get validation report for errors.

        Returns:
            ValidationReport instance
        """
        return ValidationReport(self.validation_errors)

    def get_metrics_exporter(self) -> MetricsExporter:
        """
        Get metrics exporter for extraction metrics.

        Returns:
            MetricsExporter instance
        """
        return MetricsExporter(self.metrics, self.entities)

    def print_cost_comparison(self) -> None:
        """Print cost estimate vs actual comparison if estimate exists."""
        if not self.cost_estimate:
            # No estimate - just show actuals
            print("\n" + "=" * 70)
            print("ACTUAL COSTS")
            print("=" * 70)
            print(f"  Input Tokens: {self.metrics.actual_input_tokens:,}")
            print(f"  Output Tokens: {self.metrics.actual_output_tokens:,}")
            print(f"  Total Cost: ${self.metrics.actual_cost_usd:.4f}")
            print(f"  Duration: {self.metrics.duration_seconds / 60:.1f} minutes")
            print("=" * 70)
            return

        # We have an estimate - show comparison
        print("\n" + "=" * 70)
        print("COST ESTIMATION ACCURACY")
        print("=" * 70)

        print(f"\n{'Metric':<25} {'Estimated':>15} {'Actual':>15} {'Error':>10}")
        print("-" * 70)

        # Input tokens
        est_input = self.cost_estimate.estimated_input_tokens
        act_input = self.metrics.actual_input_tokens
        if act_input > 0:
            error = abs(est_input - act_input) / act_input * 100
            print(
                f"{'Input Tokens':<25} {est_input:>15,} {act_input:>15,} {error:>9.1f}%"
            )

        # Output tokens
        est_output = self.cost_estimate.estimated_output_tokens
        act_output = self.metrics.actual_output_tokens
        if act_output > 0:
            error = abs(est_output - act_output) / act_output * 100
            print(
                f"{'Output Tokens':<25} {est_output:>15,} {act_output:>15,} {error:>9.1f}%"
            )

        # Cost
        est_cost = self.cost_estimate.estimated_cost_usd
        act_cost = self.metrics.actual_cost_usd
        if act_cost > 0:
            error = abs(est_cost - act_cost) / act_cost * 100
            print(
                f"{'Cost (USD)':<25} ${est_cost:>14.4f} ${act_cost:>14.4f} {error:>9.1f}%"
            )

        # Duration
        est_duration = self.cost_estimate.estimated_duration_seconds / 60
        act_duration = self.metrics.duration_seconds / 60
        if act_duration > 0:
            error = (
                abs(
                    self.cost_estimate.estimated_duration_seconds
                    - self.metrics.duration_seconds
                )
                / self.metrics.duration_seconds
                * 100
            )
            print(
                f"{'Duration (minutes)':<25} {est_duration:>15.1f} {act_duration:>15.1f} {error:>9.1f}%"
            )

        print("=" * 70)

        # Show improvement suggestions
        if act_input > 0:
            token_error = abs(est_input - act_input) / act_input * 100
            if token_error > 20:
                print(
                    "\n⚠️  Token estimation was >20% off. Estimates will improve with more runs."
                )


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
        self.validator = EntityValidator(config=config.validation)
        self.progress_callback = progress_callback

        # Initialize checkpoint store if enabled
        if config.checkpoint.enabled and checkpoint_store is None:
            self.checkpoint_store: DiskCheckpointStore | None = DiskCheckpointStore(
                checkpoint_dir=config.checkpoint.checkpoint_dir
            )
        else:
            self.checkpoint_store = checkpoint_store

        # Store dry-run estimate for cost comparison (set by dry_run() method)
        self._dry_run_estimate: CostEstimate | None = None

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

        # Track actual usage across all chunks for cost comparison
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost_usd = 0.0

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

            # Report chunk update (for progress display)
            if hasattr(self, "chunk_callback") and self.chunk_callback:
                self.chunk_callback(
                    chunk_num=chunk_index + 1,
                    chunk_id=chunk.chunk_id,
                    files=chunk.files,
                    size_mb=chunk.total_size_bytes / (1024 * 1024),
                )

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

                    # Collect actual usage stats from agent client (if available)
                    chunk_cost = 0.0
                    if (
                        hasattr(self.extraction_agent, "llm_client")
                        and hasattr(self.extraction_agent.llm_client, "last_usage")
                        and self.extraction_agent.llm_client.last_usage
                    ):
                        usage = self.extraction_agent.llm_client.last_usage
                        total_input_tokens += usage.get("input_tokens", 0)
                        total_output_tokens += usage.get("output_tokens", 0)
                        chunk_cost = usage.get("total_cost_usd", 0.0)
                        total_cost_usd += chunk_cost

                    # Report stats (for verbose mode progress display)
                    if hasattr(self, "stats_callback") and self.stats_callback:
                        self.stats_callback(
                            entities=result.entities,  # Pass actual entities for relationship counting
                            validation_errors=len(result.validation_errors),
                            cost_usd=chunk_cost,  # Pass cost for this chunk
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

        # 5. Validate final graph (orphans, broken references)
        if final_entities:
            graph_validation_errors = self.validator.validate_graph(final_entities)
            all_validation_errors.extend(graph_validation_errors)

            if graph_validation_errors:
                logger.info(
                    f"Graph validation found {len(graph_validation_errors)} issues "
                    f"({sum(1 for e in graph_validation_errors if e.severity == 'error')} errors, "
                    f"{sum(1 for e in graph_validation_errors if e.severity == 'warning')} warnings)"
                )

        # 6. Calculate metrics
        duration = time.time() - start_time
        metrics = ExtractionMetrics(
            total_chunks=len(chunks),
            chunks_processed=chunks_processed,
            entities_extracted=len(final_entities),
            validation_errors=len(all_validation_errors),
            duration_seconds=duration,
            # Add actual usage stats from LLM API
            actual_input_tokens=total_input_tokens,
            actual_output_tokens=total_output_tokens,
            actual_cost_usd=total_cost_usd,
        )

        return OrchestrationResult(
            entities=final_entities,
            metrics=metrics,
            validation_errors=all_validation_errors,
            cost_estimate=self._dry_run_estimate,  # Include estimate if dry-run was performed
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
            # Serialize entities to JSON-LD format
            serialized_entities = [entity.to_jsonld() for entity in all_entities]

            checkpoint = Checkpoint(
                checkpoint_id="latest",
                config_hash=self.config.compute_hash(),
                chunks_processed=chunks_processed,
                entities_extracted=len(all_entities),
                entities=serialized_entities,
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
        """
        entities: list[Entity] = []

        for entity_dict in checkpoint.entities:
            try:
                entity = Entity.from_dict(entity_dict)
                entities.append(entity)
            except Exception as e:
                # Log but don't fail - we can continue with partial data
                logger.warning(
                    f"Failed to restore entity {entity_dict.get('@id', 'unknown')}: {e}"
                )
                continue

        logger.info(f"Restored {len(entities)} entities from checkpoint")
        return entities

    def dry_run(self) -> CostEstimate:
        """
        Perform dry run to estimate cost and preview extraction.

        Does not call LLM or create output files.

        Returns:
            CostEstimate with detailed breakdown

        Raises:
            Exception: If file discovery or chunking fails
        """
        logger.info("Starting dry run (no LLM calls will be made)")

        # 1. Discover files
        files = self.file_system.list_files(
            directory=self.config.data_dir,
            pattern="**/*",
        )
        logger.info(f"Discovered {len(files)} files")

        # 2. Create chunks
        chunks = self.chunker.create_chunks(files)
        logger.info(f"Would process {len(chunks)} chunks")

        # 3. Estimate cost
        estimator = CostEstimator(self.config.llm)
        estimate = estimator.estimate_chunks(chunks)

        # Store estimate for later comparison with actual costs
        self._dry_run_estimate = estimate

        logger.info("Dry run complete")
        logger.info(f"Estimated cost: ${estimate.estimated_cost_usd:.2f}")
        logger.info(
            f"Estimated duration: {estimate.estimated_duration_seconds / 60:.1f} minutes"
        )

        return estimate
