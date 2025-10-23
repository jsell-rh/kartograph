#!/usr/bin/env python3
"""CLI entry point for knowledge graph extraction."""

import argparse
import asyncio
import json
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

    return parser.parse_args(argv)


def build_config_from_args(args: argparse.Namespace) -> ExtractionConfig:
    """
    Build ExtractionConfig from parsed arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        ExtractionConfig instance
    """
    # Build auth config
    auth_config = AuthConfig(
        auth_method=args.auth_method,
        api_key=args.api_key,
        vertex_project_id=args.vertex_project_id,
        vertex_region=args.vertex_region,
        vertex_credentials_file=args.vertex_credentials_file,
    )

    # Build chunking config
    chunking_config = ChunkingConfig(
        strategy=args.chunking_strategy,
        target_size_mb=args.chunk_size_mb,
        max_files_per_chunk=args.max_files_per_chunk,
    )

    # Build deduplication config
    dedup_config = DeduplicationConfig(
        strategy=args.dedup_strategy,
        urn_merge_strategy=args.urn_merge_strategy,
    )

    # Build logging config
    logging_config = LoggingConfig(
        log_level=args.log_level,
        log_file=args.log_file,
        json_logging=args.json_logging,
    )

    # Build main config
    config = ExtractionConfig(
        data_dir=args.data_dir,
        output_file=args.output_file,
        resume=args.resume,
        auth=auth_config,
        chunking=chunking_config,
        deduplication=dedup_config,
        logging=logging_config,
        validation=ValidationConfig(),
    )

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
    graph = {
        "@context": {
            "@vocab": "http://schema.org/",
            "urn": "@id",
        },
        "@graph": [entity.model_dump(by_alias=True) for entity in entities],
    }

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(graph, f, indent=2)

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
        llm_client = AgentClient(auth_config=config.auth, model=config.llm.model)

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

        # Create orchestrator
        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=file_system,
            chunker=chunker,
            extraction_agent=extraction_agent,
            deduplicator=deduplicator,
            progress_callback=lambda current, total, msg: logger.info(
                f"Progress: {current}/{total} - {msg}"
            ),
        )

        # Run extraction
        logger.info("Beginning extraction...")
        result = await orchestrator.extract()

        # Log metrics
        logger.info(f"Extraction complete!")
        logger.info(f"  Total chunks: {result.metrics.total_chunks}")
        logger.info(f"  Chunks processed: {result.metrics.chunks_processed}")
        logger.info(f"  Entities extracted: {result.metrics.entities_extracted}")
        logger.info(f"  Validation errors: {result.metrics.validation_errors}")
        logger.info(f"  Duration: {result.metrics.duration_seconds:.2f}s")

        # Write output
        write_jsonld(result.entities, config.output_file)

        logger.info("Extraction pipeline complete!")
        return 0

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
