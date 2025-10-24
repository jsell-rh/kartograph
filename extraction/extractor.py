#!/usr/bin/env python3
"""CLI entry point for knowledge graph extraction."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from kg_extractor.agents.extraction import ExtractionAgent
from kg_extractor.chunking.hybrid_chunker import HybridChunker
from kg_extractor.config import (
    AuthConfig,
    ChunkingConfig,
    DeduplicationConfig,
    ExtractionConfig,
    LoggingConfig,
    ValidationConfig,
)
from kg_extractor.deduplication.urn_deduplicator import URNDeduplicator
from kg_extractor.llm.agent_client import AgentClient
from kg_extractor.loaders.file_system import DiskFileSystem
from kg_extractor.orchestrator import ExtractionOrchestrator
from kg_extractor.output import JSONLDGraph
from kg_extractor.prompts.loader import DiskPromptLoader
from kg_extractor.validation.entity_validator import EntityValidator

logger = logging.getLogger("kg_extractor")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract knowledge graph from structured data files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing data files to extract from",
    )

    # Output arguments
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("knowledge_graph.jsonld"),
        help="Output JSON-LD file path",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from latest checkpoint",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        help="Export metrics to file (JSON/CSV/Markdown based on extension)",
    )
    parser.add_argument(
        "--validation-report",
        type=Path,
        help="Export validation report (JSON/Markdown based on extension)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate cost and preview extraction without calling LLM",
    )

    # Authentication
    auth_group = parser.add_argument_group("authentication")
    auth_group.add_argument(
        "--auth-method",
        choices=["vertex_ai", "api_key"],
        default="vertex_ai",
        help="Authentication method",
    )
    auth_group.add_argument(
        "--api-key",
        help="Anthropic API key (for api_key auth)",
    )
    auth_group.add_argument(
        "--vertex-project-id",
        help="Google Cloud project ID (for vertex_ai auth)",
    )
    auth_group.add_argument(
        "--vertex-region",
        default="us-central1",
        help="Google Cloud region (for vertex_ai auth)",
    )
    auth_group.add_argument(
        "--vertex-credentials-file",
        type=Path,
        help="Path to Google Cloud credentials file (for vertex_ai auth)",
    )

    # Chunking
    chunk_group = parser.add_argument_group("chunking")
    chunk_group.add_argument(
        "--chunking-strategy",
        choices=["hybrid", "directory", "size", "count"],
        default="hybrid",
        help="Chunking strategy to use",
    )
    chunk_group.add_argument(
        "--chunk-size-mb",
        type=int,
        default=10,
        help="Target chunk size in MB",
    )
    chunk_group.add_argument(
        "--max-files-per-chunk",
        type=int,
        default=100,
        help="Maximum files per chunk",
    )

    # Deduplication
    dedup_group = parser.add_argument_group("deduplication")
    dedup_group.add_argument(
        "--dedup-strategy",
        choices=["urn", "agent", "hybrid"],
        default="urn",
        help="Deduplication strategy",
    )
    dedup_group.add_argument(
        "--urn-merge-strategy",
        choices=["first", "last", "merge_predicates"],
        default="merge_predicates",
        help="How to merge duplicate URNs",
    )

    # Logging
    log_group = parser.add_argument_group("logging")
    log_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    log_group.add_argument(
        "--log-file",
        type=Path,
        help="Log file path (logs to stdout if not specified)",
    )
    log_group.add_argument(
        "--json-logging",
        action="store_true",
        help="Use JSON-formatted logs",
    )
    log_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose mode with beautiful progress display and agent activity",
    )
    log_group.add_argument(
        "--log-prompts",
        action="store_true",
        help="Log full LLM prompts and responses (for debugging)",
    )

    return parser.parse_args(argv)


def build_config_from_args(
    args: argparse.Namespace, cwd: Path | None = None
) -> ExtractionConfig:
    """
    Build ExtractionConfig from parsed arguments.

    Configuration priority (highest to lowest):
    1. CLI flags
    2. Environment variables
    3. .env file (automatically loaded by pydantic-settings from current directory)
    4. Defaults

    Args:
        args: Parsed command-line arguments
        cwd: Working directory (unused, kept for compatibility)

    Returns:
        ExtractionConfig instance
    """
    # Build config dict with CLI args to override env/file settings
    config_dict = {"data_dir": args.data_dir}

    # Auth overrides - only include if there are CLI overrides
    auth_dict = {}
    if args.auth_method:
        auth_dict["auth_method"] = args.auth_method
    if args.api_key:
        auth_dict["api_key"] = args.api_key
    if args.vertex_project_id:
        auth_dict["vertex_project_id"] = args.vertex_project_id
    if args.vertex_region != "us-central1":  # Only override if not default
        auth_dict["vertex_region"] = args.vertex_region
    if args.vertex_credentials_file:
        auth_dict["vertex_credentials_file"] = args.vertex_credentials_file

    # Only include auth if we have CLI overrides, otherwise let pydantic load from env
    if auth_dict:
        config_dict["auth"] = auth_dict

    # Chunking overrides - only include if there are CLI overrides
    chunking_dict = {}
    if args.chunking_strategy != "hybrid":  # Only override if not default
        chunking_dict["strategy"] = args.chunking_strategy
    if args.chunk_size_mb != 10:  # Only override if not default
        chunking_dict["target_size_mb"] = args.chunk_size_mb
    if args.max_files_per_chunk != 100:  # Only override if not default
        chunking_dict["max_files_per_chunk"] = args.max_files_per_chunk

    if chunking_dict:
        config_dict["chunking"] = chunking_dict

    # Deduplication overrides - only include if there are CLI overrides
    dedup_dict = {}
    if args.dedup_strategy != "urn":  # Only override if not default
        dedup_dict["strategy"] = args.dedup_strategy
    if args.urn_merge_strategy != "merge_predicates":  # Only override if not default
        dedup_dict["urn_merge_strategy"] = args.urn_merge_strategy

    if dedup_dict:
        config_dict["deduplication"] = dedup_dict

    # Logging overrides - only include if there are CLI overrides
    logging_dict = {}
    if args.log_level != "INFO":  # Only override if not default
        logging_dict["log_level"] = args.log_level
    if args.log_file:
        logging_dict["log_file"] = args.log_file
    if args.json_logging:
        logging_dict["json_logging"] = args.json_logging
    if args.verbose:
        logging_dict["verbose"] = args.verbose
    if args.log_prompts:
        logging_dict["log_llm_prompts"] = args.log_prompts

    if logging_dict:
        config_dict["logging"] = logging_dict

    # Top-level overrides
    if args.output_file != Path(
        "knowledge_graph.jsonld"
    ):  # Only override if not default
        config_dict["output_file"] = args.output_file
    if args.resume:
        config_dict["resume"] = args.resume

    # Create config - pydantic-settings will load from .env (in current dir) and env vars, then override with our dict
    config = ExtractionConfig(**config_dict)

    return config


def setup_logging(config: LoggingConfig) -> None:
    """
    Configure logging based on LoggingConfig.

    Args:
        config: Logging configuration
    """
    # Convert log level string to logging constant
    level = getattr(logging, config.log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if config.json_logging:
        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Human-readable formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set kg_extractor logger level
    kg_logger = logging.getLogger("kg_extractor")
    kg_logger.setLevel(level)


def write_jsonld(entities: list, output_file: Path) -> None:
    """
    Write entities to JSON-LD file.

    Args:
        entities: List of entities to write
        output_file: Output file path
    """
    # Build JSON-LD graph
    graph = JSONLDGraph()
    graph.add_entities(entities)

    # Save to file
    graph.save(output_file)

    logger.info(f"Wrote {len(entities)} entities to {output_file}")


async def main(argv: list[str] | None = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse arguments
        args = parse_args(argv)

        # Build configuration
        config = build_config_from_args(args)

        # Set up logging
        setup_logging(config.logging)

        logger.info("Starting knowledge graph extraction")
        logger.info(f"Data directory: {config.data_dir}")
        logger.info(f"Output file: {config.output_file}")

        # Create components
        file_system = DiskFileSystem()
        chunker = HybridChunker(config=config.chunking)
        deduplicator = URNDeduplicator(config=config.deduplication)

        # Create LLM client
        llm_client = AgentClient(
            auth_config=config.auth,
            model=config.llm.model,
            log_prompts=config.logging.log_llm_prompts,
        )

        # Create prompt loader
        prompt_loader = DiskPromptLoader(template_dir=config.prompt_template_dir)

        # Create validator
        validator = EntityValidator(config=config.validation)

        # Create extraction agent
        extraction_agent = ExtractionAgent(
            llm_client=llm_client,
            prompt_loader=prompt_loader,
            validator=validator,
        )

        # Set up progress display (only in verbose mode AND not in JSON logging mode)
        # Rich terminal UI doesn't work well in CI/JSON mode
        progress_display = None
        if config.logging.verbose and not config.logging.json_logging:
            from kg_extractor.progress import ProgressDisplay

            # Count chunks first for progress bar
            files = file_system.list_files(
                directory=config.data_dir,
                pattern="**/*",
            )
            chunks = chunker.create_chunks(files)
            total_chunks = len(chunks)

            progress_display = ProgressDisplay(
                total_chunks=total_chunks, verbose=config.logging.verbose
            )

        # Create progress callback
        def progress_callback(current: int, total: int, msg: str) -> None:
            if progress_display:
                # Update progress display
                if "Processed chunk" in msg:
                    chunk_id = msg.split()[-1]
                    progress_display.advance_chunk()
            else:
                # Fall back to logger
                logger.info(f"Progress: {current}/{total} - {msg}")

        # Create orchestrator
        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=file_system,
            chunker=chunker,
            extraction_agent=extraction_agent,
            deduplicator=deduplicator,
            progress_callback=progress_callback,
        )

        # Set event callback for verbose mode (streaming agent activity)
        if progress_display:
            # Rich terminal display
            orchestrator.event_callback = lambda activity, activity_type="info": progress_display.log_agent_activity(
                activity, activity_type
            )
            # Set chunk callback to update chunk details
            orchestrator.chunk_callback = lambda chunk_num, chunk_id, files, size_mb: progress_display.update_chunk(
                chunk_num=chunk_num,
                chunk_id=chunk_id,
                files=files,
                size_mb=size_mb,
            )
            # Set stats callback to update entity/error counts
            orchestrator.stats_callback = (
                lambda entities=0, validation_errors=0: progress_display.update_stats(
                    entities=entities, validation_errors=validation_errors
                )
            )
        elif config.logging.verbose:
            # Verbose mode with JSON logging - log to logger instead
            orchestrator.event_callback = (
                lambda activity, activity_type="info": logger.debug(
                    f"Agent activity: {activity}",
                    extra={"activity_type": activity_type},
                )
            )

        # Run dry-run or extraction
        if args.dry_run:
            # Dry run mode - estimate cost without calling LLM
            logger.info("Running in dry-run mode (no LLM calls will be made)")
            estimate = orchestrator.dry_run()

            # Print estimate
            print("\n" + "=" * 60)
            print("DRY RUN - COST ESTIMATE")
            print("=" * 60)
            print(estimate)
            print("=" * 60)
            print("\nNo extraction performed. Run without --dry-run to execute.")
            return 0

        # Run extraction
        if progress_display:
            progress_display.start()
        else:
            logger.info("Beginning extraction...")

        try:
            result = await orchestrator.extract()

            if progress_display:
                progress_display.stop()
                progress_display.print_success(
                    total_entities=result.metrics.entities_extracted,
                    total_chunks=result.metrics.chunks_processed,
                    duration=result.metrics.duration_seconds,
                )
            else:
                # Log metrics
                logger.info(f"Extraction complete!")
                logger.info(f"  Total chunks: {result.metrics.total_chunks}")
                logger.info(f"  Chunks processed: {result.metrics.chunks_processed}")
                logger.info(
                    f"  Entities extracted: {result.metrics.entities_extracted}"
                )
                logger.info(f"  Validation errors: {result.metrics.validation_errors}")
                logger.info(f"  Duration: {result.metrics.duration_seconds:.2f}s")

            # Write output
            write_jsonld(result.entities, config.output_file)

            # Export metrics if requested
            if args.metrics_output:
                # Determine format from extension
                suffix = args.metrics_output.suffix.lower()
                if suffix == ".json":
                    format = "json"
                elif suffix == ".csv":
                    format = "csv"
                elif suffix in [".md", ".markdown"]:
                    format = "markdown"
                else:
                    format = "json"  # Default

                metrics_exporter = result.get_metrics_exporter()
                metrics_exporter.save(args.metrics_output, format=format)
                logger.info(f"Metrics exported to {args.metrics_output}")

            # Export validation report if requested
            if args.validation_report:
                # Determine format from extension
                suffix = args.validation_report.suffix.lower()
                if suffix in [".md", ".markdown"]:
                    format = "markdown"
                else:
                    format = "json"  # Default

                validation_report = result.get_validation_report()
                validation_report.save(args.validation_report, format=format)
                logger.info(f"Validation report exported to {args.validation_report}")

            if not progress_display:
                logger.info("Extraction pipeline complete!")

            return 0

        except Exception as e:
            if progress_display:
                progress_display.stop()
                progress_display.print_error(str(e))
            raise

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
