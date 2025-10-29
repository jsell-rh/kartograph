"""Tests for parallel execution safety (token/cost tracking)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_parallel_token_cost_tracking():
    """Test that token and cost tracking is correct with parallel workers."""
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import AuthConfig, ExtractionConfig
    from kg_extractor.deduplication.models import (
        DeduplicationMetrics,
        DeduplicationResult,
    )
    from kg_extractor.models import Entity, ExtractionResult
    from kg_extractor.orchestrator import ExtractionOrchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        # Create 10 test files
        test_files = []
        for i in range(10):
            test_file = data_dir / f"file{i}.yaml"
            test_file.write_text(f"test: data{i}")
            test_files.append(test_file)

        # Mock components
        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = test_files

        mock_chunker = MagicMock()
        # Create 10 chunks (one per file)
        chunks = [
            Chunk(
                chunk_id=f"chunk-{i:03d}",
                files=[test_files[i]],
                total_size_bytes=100,
            )
            for i in range(10)
        ]
        mock_chunker.create_chunks.return_value = chunks

        # Track how many times extract is called
        extract_call_count = 0

        async def mock_extract(**kwargs):
            nonlocal extract_call_count
            extract_call_count += 1
            # Each chunk extracts 1 entity
            return ExtractionResult(
                entities=[
                    Entity(
                        id=f"urn:Service:api{extract_call_count}",
                        type="Service",
                        name=f"API {extract_call_count}",
                    )
                ],
                chunk_id=kwargs["chunk_id"],
                validation_errors=[],
                metadata={},
            )

        mock_agent = AsyncMock()
        mock_agent.extract = AsyncMock(side_effect=mock_extract)

        # Mock llm_client with usage stats - each call returns different usage
        mock_agent.llm_client = MagicMock()
        mock_agent.llm_client.last_usage = {
            "input_tokens": 100,  # Each chunk uses 100 input tokens
            "output_tokens": 50,  # Each chunk uses 50 output tokens
            "total_cost_usd": 0.01,  # Each chunk costs $0.01
        }

        mock_deduplicator = MagicMock()

        def mock_deduplicate(entities):
            # Just pass through (no actual deduplication)
            return DeduplicationResult(
                entities=entities,
                metrics=DeduplicationMetrics(
                    total_input_entities=len(entities),
                    total_output_entities=len(entities),
                    duplicates_found=0,
                    duplicates_merged=0,
                    merge_operations=0,
                ),
            )

        mock_deduplicator.deduplicate.side_effect = mock_deduplicate

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(auth_method="api_key", api_key="test-key"),
            workers=3,  # Use 3 parallel workers
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        # Run extraction with parallel workers
        result = await orchestrator.extract()

        # Verify all chunks were processed
        assert result.metrics.chunks_processed == 10
        assert len(result.entities) == 10

        # Verify token and cost tracking is correct (no race conditions)
        # Each of 10 chunks contributes: 100 input tokens, 50 output tokens, $0.01
        expected_input_tokens = 10 * 100  # 1000
        expected_output_tokens = 10 * 50  # 500
        expected_cost = 10 * 0.01  # 0.10

        assert result.metrics.actual_input_tokens == expected_input_tokens, (
            f"Input tokens mismatch: expected {expected_input_tokens}, "
            f"got {result.metrics.actual_input_tokens}"
        )
        assert result.metrics.actual_output_tokens == expected_output_tokens, (
            f"Output tokens mismatch: expected {expected_output_tokens}, "
            f"got {result.metrics.actual_output_tokens}"
        )
        assert abs(result.metrics.actual_cost_usd - expected_cost) < 0.001, (
            f"Cost mismatch: expected {expected_cost}, "
            f"got {result.metrics.actual_cost_usd}"
        )
