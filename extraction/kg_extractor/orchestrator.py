"""Main extraction orchestrator coordinating all components."""

import asyncio
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
from kg_extractor.deduplication.agent_deduplicator import AgentBasedDeduplicator
from kg_extractor.deduplication.protocol import DeduplicationStrategy
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
from kg_extractor.exceptions import ExtractionError, PromptTooLongError
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

        # Show warning if estimates were way off
        if act_input > 0:
            token_error = abs(est_input - act_input) / act_input * 100
            if token_error > 20:
                print(
                    "\n⚠️  Token estimation was >20% off. Consider adjusting heuristics in "
                    "kg_extractor/cost_estimator.py (CHARS_PER_TOKEN, OUTPUT_RATIO, etc.)"
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
        deduplicator: DeduplicationStrategy | None = None,
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

        # Initialize deduplicator based on strategy
        if deduplicator is None:
            if config.deduplication.strategy == "agent":
                # Agent-based deduplication requires prompt loader
                from kg_extractor.prompts.loader import DiskPromptLoader

                prompt_loader = DiskPromptLoader(
                    template_dir=config.prompt_template_dir
                )
                self.deduplicator = AgentBasedDeduplicator(
                    config=config.deduplication,
                    auth_config=config.auth,
                    model=config.llm.model,
                    prompt_loader=prompt_loader,
                )
            elif config.deduplication.strategy == "hybrid":
                # Hybrid not yet implemented - warn and fall back to URN
                logger.warning(
                    "Hybrid deduplication strategy is not yet implemented. "
                    "Falling back to URN-based deduplication. "
                    "Use --dedup-strategy=agent for LLM-powered semantic deduplication."
                )
                self.deduplicator = URNDeduplicator(config=config.deduplication)
            else:
                # Default to URN-based deduplication
                self.deduplicator = URNDeduplicator(config=config.deduplication)
        else:
            self.deduplicator = deduplicator

        self.validator = EntityValidator(config=config.validation)
        self.progress_callback = progress_callback

        # Initialize checkpoint store if enabled
        if config.checkpoint.enabled and checkpoint_store is None:
            # Create data-dir-specific checkpoint directory to avoid conflicts
            # Each data directory gets its own checkpoint subdirectory
            data_dir_hash = config.compute_data_dir_hash()
            checkpoint_subdir = config.checkpoint.checkpoint_dir / data_dir_hash

            self.checkpoint_store: DiskCheckpointStore | None = DiskCheckpointStore(
                checkpoint_dir=checkpoint_subdir, data_dir=config.data_dir
            )
            logger.debug(
                f"Using checkpoint directory: {checkpoint_subdir} (hash: {data_dir_hash})"
            )
        else:
            self.checkpoint_store = checkpoint_store

        # Store dry-run estimate for cost comparison (set by dry_run() method)
        self._dry_run_estimate: CostEstimate | None = None

        # Thread-safe entity collection for parallel execution
        self._entities_lock = asyncio.Lock()

        # Worker state tracking for multi-worker progress display
        # Note: dict operations (assignment, clear) are atomic in CPython
        # so no lock needed for simple reads/writes
        self._worker_states: dict[int, dict[str, Any]] = {}

    def get_worker_states(self) -> dict[int, dict[str, Any]]:
        """
        Get current worker states for progress display.

        Returns:
            Dictionary mapping worker_id to worker state
        """
        return self._worker_states.copy()

    def _count_relationships(self, entities: list[Entity]) -> int:
        """
        Count relationships (edges) in entities.

        A relationship is a property whose value is:
        - A dict with "@id" key (entity reference)
        - A list of such dicts (multiple references)

        Args:
            entities: List of Entity objects

        Returns:
            Number of relationships found
        """
        total_relationships = 0

        for entity in entities:
            # Get properties dict
            properties = entity.properties

            for key, value in properties.items():
                # Skip reserved keys
                if key.startswith("@"):
                    continue

                # Check if value is an entity reference
                if isinstance(value, dict) and "@id" in value:
                    total_relationships += 1

                # Check if value is a list of entity references
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "@id" in item:
                            total_relationships += 1

        return total_relationships

    def _build_entity_context(
        self, entities: list[Entity], max_entities: int = 200
    ) -> list[dict]:
        """
        Build compact entity context for entity-aware extraction.

        Provides workers with knowledge of previously extracted entities
        to help them create consistent references and avoid duplicates.

        Args:
            entities: List of accumulated entities from previous chunks
            max_entities: Maximum number of entities to include (to avoid prompt bloat)

        Returns:
            List of entity dicts with id, type, name (compact format)
        """
        # Take most recent entities (assuming they're more relevant)
        entities_to_include = (
            entities[-max_entities:] if len(entities) > max_entities else entities
        )

        # Build compact format (just id, type, name)
        context = [
            {
                "id": entity.id,
                "type": entity.type,
                "name": entity.name,
            }
            for entity in entities_to_include
        ]

        return context

    async def _process_chunk(
        self,
        chunk: Chunk,
        chunk_index: int,
        schema_dir: Path | None,
        known_entities: list[dict] | None = None,
        worker_id: int | None = None,
        event_callback: Any = None,
    ) -> dict[str, Any]:
        """
        Process a single chunk (for parallel execution).

        Args:
            chunk: Chunk to process
            chunk_index: Index of the chunk in the list
            schema_dir: Optional schema directory
            known_entities: Optional list of known entities for entity-aware extraction
            worker_id: Optional worker ID for tracking (used in multi-worker mode)
            event_callback: Optional per-worker event callback (overrides global callback)

        Returns:
            Dictionary with extraction results:
            {
                "entities": [...],
                "validation_errors": [...],
                "chunk_cost": float,
                "chunk_input_tokens": int,
                "chunk_output_tokens": int,
            }

        Raises:
            PromptTooLongError: If chunk is too large (needs splitting)
            Exception: On other errors
        """
        # Report chunk update (for progress display)
        if hasattr(self, "chunk_callback") and self.chunk_callback:
            self.chunk_callback(
                chunk_num=chunk_index + 1,
                chunk_id=chunk.chunk_id,
                files=chunk.files,
                size_mb=chunk.total_size_bytes / (1024 * 1024),
            )

        # Prepare extraction kwargs
        extract_kwargs = {
            "files": chunk.files,
            "chunk_id": chunk.chunk_id,
            "schema_dir": schema_dir,
            "known_entities": known_entities or [],
        }

        # Use provided event_callback (per-worker), or fall back to global callback
        callback_to_use = (
            event_callback
            if event_callback
            else (self.event_callback if hasattr(self, "event_callback") else None)
        )
        if callback_to_use:
            extract_kwargs["event_callback"] = callback_to_use

        # Extract entities from chunk (may raise PromptTooLongError)
        result = await self.extraction_agent.extract(**extract_kwargs)

        # Collect usage stats
        chunk_cost = 0.0
        chunk_input_tokens = 0
        chunk_output_tokens = 0
        if (
            hasattr(self.extraction_agent, "llm_client")
            and hasattr(self.extraction_agent.llm_client, "last_usage")
            and self.extraction_agent.llm_client.last_usage
        ):
            usage = self.extraction_agent.llm_client.last_usage
            chunk_input_tokens = usage.get("input_tokens", 0)
            chunk_output_tokens = usage.get("output_tokens", 0)
            chunk_cost = usage.get("total_cost_usd", 0.0)

        # Report stats (for verbose mode progress display)
        if hasattr(self, "stats_callback") and self.stats_callback:
            self.stats_callback(
                entities=result.entities,
                validation_errors=len(result.validation_errors),
                cost_usd=chunk_cost,
                input_tokens=chunk_input_tokens,
                output_tokens=chunk_output_tokens,
            )

        return {
            "entities": result.entities,
            "validation_errors": result.validation_errors,
            "chunk_cost": chunk_cost,
            "chunk_input_tokens": chunk_input_tokens,
            "chunk_output_tokens": chunk_output_tokens,
        }

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

        # 3. Generate cost estimate for comparison
        # This runs automatically at the start of every extraction to provide a baseline
        logger.info("Generating cost estimate for comparison...")
        estimator = CostEstimator(self.config.llm)
        self._dry_run_estimate = estimator.estimate_chunks(chunks)
        logger.info(
            f"Estimated: {self._dry_run_estimate.estimated_input_tokens:,} input tokens, "
            f"{self._dry_run_estimate.estimated_output_tokens:,} output tokens, "
            f"${self._dry_run_estimate.estimated_cost_usd:.4f}, "
            f"{self._dry_run_estimate.estimated_duration_seconds / 60:.1f} minutes"
        )

        # Initialize tracking
        all_entities: list[Entity] = []
        all_validation_errors: list[ValidationError] = []

        # Progress tracking - separates successful, failed, and skipped chunks
        chunks_processed = 0  # Total attempted (successful + failed)
        chunks_successful = 0  # Successfully completed
        chunks_failed = 0  # Failed and skipped
        chunks_skipped = 0  # Skipped from checkpoint resume
        chunk_index = 0
        completed_chunk_ids: set[str] = (
            set()
        )  # Track which chunks are done (for parallel resume)

        # Failure detection (circuit breaker)
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 5
        FAILURE_RATE_THRESHOLD = 0.10
        MIN_CHUNKS_FOR_RATE_CHECK = 10

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
                    logger.info(
                        f"  Checkpoint contained {checkpoint.entities_extracted} entities"
                    )
                    chunks_processed = checkpoint.chunks_processed
                    completed_chunk_ids = checkpoint.completed_chunk_ids.copy()
                    all_entities = self._entities_from_checkpoint_data(checkpoint)
                    logger.info(
                        f"  Restored {len(all_entities)} entities from checkpoint"
                    )
                    logger.info(
                        f"  Completed chunks: {len(completed_chunk_ids)} ({', '.join(sorted(list(completed_chunk_ids))[:5])}{'...' if len(completed_chunk_ids) > 5 else ''})"
                    )

                    # Update progress display with checkpoint state
                    # This ensures stats (entities, relationships) reflect work already done
                    if hasattr(self, "stats_callback") and self.stats_callback:
                        # Pass all entities to initialize stats (entities + relationships)
                        self.stats_callback(
                            entities=all_entities,
                            validation_errors=0,  # Not tracked in checkpoint
                            cost_usd=0.0,  # Will be incremented from this point
                            input_tokens=0,  # Will be incremented from this point
                            output_tokens=0,  # Will be incremented from this point
                        )
                        logger.debug(
                            f"Initialized progress display with {len(all_entities)} entities from checkpoint"
                        )

                    # Update chunk progress counter to reflect checkpoint state
                    if (
                        hasattr(self, "init_progress_callback")
                        and self.init_progress_callback
                    ):
                        self.init_progress_callback(chunks_completed=chunks_processed)
                        logger.debug(
                            f"Set initial chunk progress to {chunks_processed}"
                        )

        # Convert to list for dynamic modification (chunk splitting on 413 errors)
        chunks_to_process = list(chunks)
        original_chunk_count = len(chunks)  # Track original count (before splits)

        # 3. Process chunks with streaming worker pool (no idle workers!)
        # Use schema dir for all chunks
        schema_dir = self.config.context_dirs[0] if self.config.context_dirs else None

        # Helper function to create worker callback (needs to be outside loop)
        def make_worker_callback(wid, c):
            def worker_callback(message, activity_type=None, detail=None):
                # Update worker state (dict assignment is atomic in CPython)
                self._worker_states[wid] = {
                    "status": "active",
                    "chunk_id": c.chunk_id,
                    "activity": message,
                    "activity_type": activity_type,
                    "detail": detail,
                    "files_count": len(c.files),
                    "size_mb": c.total_size_bytes / (1024 * 1024),
                }

                # Also call global event callback for overall stats
                if hasattr(self, "event_callback") and self.event_callback:
                    self.event_callback(message, activity_type, detail)

            return worker_callback

        # Streaming worker pool: Keep N workers busy at all times
        if self.extraction_agent:
            # Track pending tasks and their metadata
            pending = {}  # task -> (chunk_index_in_list, chunk, worker_id)
            available_workers = set(range(self.config.workers))

            # Build initial entity context for entity-aware extraction
            entity_context = self._build_entity_context(all_entities)
            logger.debug(
                f"Built entity context with {len(entity_context)} known entities"
            )

            logger.debug(
                f"Starting streaming worker pool with {self.config.workers} workers "
                f"for {len(chunks_to_process)} chunks"
            )

            # Main processing loop: keep workers busy until all chunks done
            while chunk_index < len(chunks_to_process) or pending:
                # Start new tasks for available workers
                while available_workers and chunk_index < len(chunks_to_process):
                    chunk = chunks_to_process[chunk_index]

                    # Skip chunks that are already completed (from checkpoint)
                    if chunk.chunk_id in completed_chunk_ids:
                        chunks_skipped += 1
                        logger.info(
                            f"Skipping chunk {chunk.chunk_id} (already completed in checkpoint) "
                            f"[{chunks_skipped} skipped so far]"
                        )
                        chunk_index += 1
                        continue

                    worker_id = available_workers.pop()
                    current_chunk_index = chunk_index

                    # Create and start task
                    task = asyncio.create_task(
                        self._process_chunk(
                            chunk,
                            current_chunk_index,
                            schema_dir,
                            known_entities=entity_context,
                            worker_id=worker_id,
                            event_callback=make_worker_callback(worker_id, chunk),
                        )
                    )
                    pending[task] = (current_chunk_index, chunk, worker_id)
                    chunk_index += 1

                    logger.debug(
                        f"Worker {worker_id} started chunk {current_chunk_index + 1}/{len(chunks_to_process)} "
                        f"({chunk.chunk_id})"
                    )

                if not pending:
                    # No more work to do
                    break

                # Wait for at least one task to complete
                done, still_pending = await asyncio.wait(
                    pending.keys(), return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed tasks
                for task in done:
                    current_chunk_index, chunk, worker_id = pending.pop(task)

                    # Get result or exception from task
                    try:
                        result = task.result()
                    except PromptTooLongError as e:
                        # Chunk is too large - split it and add back to queue
                        logger.warning(
                            f"Chunk {chunk.chunk_id} exceeded prompt length limit "
                            f"({len(chunk.files)} files, {chunk.total_size_bytes / 1024 / 1024:.2f} MB). "
                            f"Splitting into smaller chunks..."
                        )

                        try:
                            # Split the chunk
                            first_half, second_half = chunk.split()

                            # Replace current chunk with the two halves
                            chunks_to_process[current_chunk_index] = first_half
                            chunks_to_process.insert(
                                current_chunk_index + 1, second_half
                            )

                            logger.info(
                                f"Split {chunk.chunk_id} into {first_half.chunk_id} "
                                f"({len(first_half.files)} files) and {second_half.chunk_id} "
                                f"({len(second_half.files)} files)"
                            )

                            # Rewind chunk_index to retry split chunks
                            # The worker will pick up the first_half next
                            chunk_index = current_chunk_index

                        except ValueError as split_error:
                            # Can't split further (single file too large)
                            chunks_failed += 1
                            consecutive_failures += 1
                            chunks_processed += 1

                            logger.error(
                                f"Cannot split chunk {chunk.chunk_id} further: {split_error}. "
                                f"Skipping this chunk (single file too large). "
                                f"Progress: {chunks_successful} successful, {chunks_failed} failed, {chunks_skipped} skipped"
                            )

                            # Update progress display
                            if self.progress_callback:
                                self.progress_callback(
                                    chunks_processed,
                                    len(chunks_to_process),
                                    f"Skipped unsplittable chunk {chunk.chunk_id}",
                                )

                        # Worker is now available
                        available_workers.add(worker_id)
                        continue

                    except Exception as e:
                        # Track failure
                        chunks_failed += 1
                        consecutive_failures += 1
                        chunks_processed += 1

                        # Log with full context
                        logger.error(
                            f"Error processing chunk {chunk.chunk_id} (worker {worker_id}): {e}",
                            exc_info=True,
                        )

                        # Calculate failure metrics
                        failure_rate = chunks_failed / max(chunks_processed, 1)

                        # Circuit breaker: abort on consecutive failures
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            logger.error(
                                f"ABORTING: {consecutive_failures} consecutive chunk failures. "
                                f"Systematic issue detected. Last error: {e}"
                            )
                            raise ExtractionError(
                                f"Too many consecutive failures ({consecutive_failures}). "
                                f"Failed chunk: {chunk.chunk_id}"
                            ) from e

                        # Circuit breaker: abort on high failure rate
                        if (
                            chunks_processed >= MIN_CHUNKS_FOR_RATE_CHECK
                            and failure_rate > FAILURE_RATE_THRESHOLD
                        ):
                            logger.error(
                                f"ABORTING: Failure rate too high ({failure_rate:.1%} > {FAILURE_RATE_THRESHOLD:.0%}). "
                                f"Failed: {chunks_failed}/{chunks_processed} chunks."
                            )
                            raise ExtractionError(
                                f"Chunk failure rate ({failure_rate:.1%}) exceeds threshold. "
                                f"Failed {chunks_failed}/{chunks_processed} chunks."
                            ) from e

                        # Log current status
                        logger.warning(
                            f"Progress: {chunks_successful} successful, {chunks_failed} failed, {chunks_skipped} skipped | "
                            f"Failure rate: {failure_rate:.1%}, consecutive: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}"
                        )

                        # Update progress display with failure indication
                        if self.progress_callback:
                            self.progress_callback(
                                chunks_processed,
                                len(chunks_to_process),
                                f"Chunk {chunk.chunk_id} failed (continuing)",
                            )

                        # Worker is now available
                        available_workers.add(worker_id)
                        continue

                    # Success - collect results with thread-safe lock
                    async with self._entities_lock:
                        all_entities.extend(result["entities"])
                        all_validation_errors.extend(result["validation_errors"])
                        total_input_tokens += result["chunk_input_tokens"]
                        total_output_tokens += result["chunk_output_tokens"]
                        total_cost_usd += result["chunk_cost"]

                    # Success - track and reset failure counter
                    chunks_processed += 1
                    chunks_successful += 1
                    consecutive_failures = 0  # Reset on success
                    completed_chunk_ids.add(
                        chunk.chunk_id
                    )  # Track completion for checkpoint

                    logger.debug(
                        f"Worker {worker_id} completed chunk {chunk.chunk_id} "
                        f"({chunks_successful}/{len(chunks_to_process)} successful, "
                        f"{chunks_failed} failed, {chunks_skipped} skipped, "
                        f"{len(result['entities'])} entities extracted)"
                    )

                    # Mark worker as completed in worker states with entity/relationship counts
                    if worker_id in self._worker_states:
                        # Count relationships in extracted entities
                        relationship_count = self._count_relationships(
                            result["entities"]
                        )

                        self._worker_states[worker_id]["status"] = "completed"
                        self._worker_states[worker_id]["entity_count"] = len(
                            result["entities"]
                        )
                        self._worker_states[worker_id][
                            "relationship_count"
                        ] = relationship_count

                    # Report progress with detailed status
                    if self.progress_callback:
                        # Use total chunks done (successful + skipped from checkpoint)
                        self.progress_callback(
                            chunks_successful + chunks_skipped,
                            len(chunks_to_process),
                            f"Processed chunk {chunk.chunk_id}",
                        )

                    # Worker is now available for next chunk
                    available_workers.add(worker_id)

                # Monitor client pool health (every 10 chunks)
                if chunks_successful % 10 == 0 and chunks_successful > 0:
                    from kg_extractor.llm.agent_client import AgentClient

                    pool_stats = AgentClient.get_pool_stats()
                    if pool_stats.get("initialized"):
                        current_size = pool_stats["current_size"]
                        max_size = pool_stats["max_size"]
                        workers_busy = max_size - current_size

                        logger.debug(
                            f"Client pool health check: {workers_busy}/{max_size} workers active, "
                            f"{current_size} idle in pool"
                        )

                        # CRITICAL: Pool should NEVER exceed max_size
                        if current_size > max_size:
                            logger.error(
                                f"⚠️  CLIENT POOL SIZE ANOMALY DETECTED! "
                                f"Pool has {current_size} clients but max is {max_size}. "
                                f"This indicates a memory leak in client cleanup."
                            )

                # Save checkpoint based on configured strategy - can checkpoint anytime!
                # We now track completed_chunk_ids, so we can skip already-done chunks on resume
                # No need to wait for workers to be idle!
                should_checkpoint = False
                if self.checkpoint_store and self.config.checkpoint.enabled:
                    strategy = self.config.checkpoint.strategy
                    if strategy == "per_chunk":
                        should_checkpoint = True
                    elif strategy == "every_n":
                        if (
                            chunks_processed % self.config.checkpoint.every_n_chunks
                            == 0
                            and chunks_processed > 0
                        ):
                            should_checkpoint = True
                    # time_based would need additional tracking

                if should_checkpoint:
                    self._save_checkpoint_with_completed_ids(
                        chunk_index=chunk_index,
                        total_chunks=len(chunks_to_process),
                        chunks_processed=chunks_processed,
                        all_entities=all_entities,
                        completed_chunk_ids=completed_chunk_ids,
                    )
                    logger.info(
                        f"Checkpoint saved: {chunks_processed} chunks, {len(completed_chunk_ids)} chunk IDs tracked"
                    )

                # Run incremental deduplication every N chunks
                should_deduplicate = False
                if (
                    chunks_successful % self.config.deduplication.batch_size == 0
                    and chunks_successful > 0
                    and all_entities
                ):
                    should_deduplicate = True

                if should_deduplicate:
                    logger.info(
                        f"Running incremental deduplication on {len(all_entities)} entities "
                        f"(batch at {chunks_successful}/{len(chunks_to_process)} chunks)..."
                    )
                    dedup_result = self.deduplicator.deduplicate(all_entities)

                    # Replace entities with deduplicated version
                    entities_before = len(all_entities)
                    all_entities = dedup_result.entities
                    entities_after = len(all_entities)

                    logger.info(
                        f"Deduplication complete: {entities_before} → {entities_after} entities "
                        f"({entities_before - entities_after} duplicates removed)"
                    )

                    # Rebuild entity context with deduplicated entities for subsequent chunks
                    entity_context = self._build_entity_context(all_entities)
                    logger.debug(
                        f"Updated entity context with {len(entity_context)} deduplicated entities"
                    )

                    # Save checkpoint after deduplication to persist deduplicated state
                    if self.checkpoint_store and self.config.checkpoint.enabled:
                        self._save_checkpoint_with_completed_ids(
                            chunk_index=chunk_index,
                            total_chunks=len(chunks_to_process),
                            chunks_processed=chunks_processed,
                            all_entities=all_entities,
                            completed_chunk_ids=completed_chunk_ids,
                        )
                        logger.info(
                            f"Checkpoint updated after deduplication: {len(all_entities)} entities"
                        )

            # Clear worker states after all chunks complete
            self._worker_states.clear()

            # Final client pool health check
            from kg_extractor.llm.agent_client import AgentClient

            pool_stats = AgentClient.get_pool_stats()
            if pool_stats.get("initialized"):
                current_size = pool_stats["current_size"]
                max_size = pool_stats["max_size"]
                workers_busy = max_size - current_size

                logger.info(
                    f"Final client pool status: {workers_busy}/{max_size} workers still active, "
                    f"{current_size} idle in pool"
                )

                # All workers should have returned their clients
                if current_size != max_size:
                    logger.warning(
                        f"⚠️  Expected all {max_size} workers idle, "
                        f"but {workers_busy} still active. "
                        f"Some clients may have failed cleanup."
                    )

            # Save final checkpoint after all chunks complete
            if self.checkpoint_store and self.config.checkpoint.enabled:
                self._save_checkpoint_with_completed_ids(
                    chunk_index=chunk_index,
                    total_chunks=len(chunks_to_process),
                    chunks_processed=chunks_processed,
                    all_entities=all_entities,
                    completed_chunk_ids=completed_chunk_ids,
                )
                logger.info(
                    f"Final checkpoint saved: {chunks_processed}/{len(chunks_to_process)} chunks complete, "
                    f"{len(completed_chunk_ids)} chunk IDs tracked"
                )

        else:
            # No extraction agent - just skip all chunks
            chunks_processed = len(chunks_to_process)

        # Final processing summary
        total_attempted = chunks_successful + chunks_failed
        effective_total = (
            len(chunks_to_process) - chunks_skipped
        )  # What we actually needed to process

        logger.info("=" * 70)
        logger.info("EXTRACTION PROCESSING SUMMARY")
        logger.info("=" * 70)
        logger.info(
            f"  Total chunks:        {len(chunks_to_process)} (original: {original_chunk_count})"
        )
        logger.info(f"  Skipped (resumed):   {chunks_skipped}")
        logger.info(f"  Attempted:           {total_attempted}")
        logger.info(f"  Successful:          {chunks_successful}")
        logger.info(f"  Failed:              {chunks_failed}")

        if chunks_failed > 0:
            failure_rate = chunks_failed / total_attempted if total_attempted > 0 else 0
            logger.warning(
                f"  Failure rate:        {failure_rate:.1%}\n"
                f"\n"
                f"  ⚠️  {chunks_failed} chunks failed and will be retried on next resume.\n"
                f"  Failed chunks are NOT in checkpoint and will be re-attempted."
            )
            logger.info("=" * 70)
        elif chunks_successful > 0:
            logger.info(f"  ✓ All {chunks_successful} chunks processed successfully!")
            logger.info("=" * 70)

        # 4. Final deduplication (for any remaining entities not caught in batches)
        # Only run if we have entities that weren't just deduplicated
        chunks_since_last_dedup = (
            chunks_successful % self.config.deduplication.batch_size
        )
        if all_entities and chunks_since_last_dedup > 0:
            logger.info(
                f"Running final deduplication on {len(all_entities)} entities "
                f"({chunks_since_last_dedup} chunks since last batch dedup)..."
            )
            dedup_result = self.deduplicator.deduplicate(all_entities)
            final_entities = dedup_result.entities
            logger.info(
                f"Final deduplication complete: {len(all_entities)} → {len(final_entities)} entities"
            )
        elif all_entities:
            # Already deduplicated in last batch, no need to run again
            logger.info(
                f"Skipping final deduplication (already deduplicated in last batch)"
            )
            final_entities = all_entities
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
            chunks_processed=chunks_successful,
            chunks_failed=chunks_failed,
            chunks_skipped=chunks_skipped,
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

    def _save_checkpoint_with_completed_ids(
        self,
        chunk_index: int,
        total_chunks: int,
        chunks_processed: int,
        all_entities: list[Entity],
        completed_chunk_ids: set[str],
    ) -> None:
        """
        Save checkpoint with completed chunk IDs (for parallel-safe resume).

        Args:
            chunk_index: Current chunk index
            total_chunks: Total number of chunks
            chunks_processed: Number of chunks processed so far
            all_entities: All entities extracted so far
            completed_chunk_ids: Set of chunk IDs that have been completed
        """
        if not self.checkpoint_store or not self.config.checkpoint.enabled:
            return

        # Serialize entities to JSON-LD format
        serialized_entities = [entity.to_jsonld() for entity in all_entities]

        checkpoint = Checkpoint(
            checkpoint_id="latest",
            config_hash=self.config.compute_hash(),
            chunks_processed=chunks_processed,
            completed_chunk_ids=completed_chunk_ids,  # Track completed chunks
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
                f"{len(all_entities)} entities, {len(completed_chunk_ids)} chunk IDs"
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
