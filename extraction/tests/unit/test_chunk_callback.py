"""Test chunk callback integration."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_orchestrator_calls_chunk_callback(tmp_path):
    """Test orchestrator calls chunk_callback before processing each chunk."""
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create test files
    file1 = data_dir / "file1.py"
    file2 = data_dir / "file2.py"
    file1.write_text("# test file 1\n" * 50)  # ~1KB
    file2.write_text("# test file 2\n" * 100)  # ~2KB

    config = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Mock extraction agent
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)
    # Add llm_client mock
    mock_agent.llm_client = MagicMock()
    mock_agent.llm_client.last_usage = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_cost_usd": 0.01,
    }

    # Mock file system
    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(return_value=[file1, file2])

    # Mock chunker
    mock_chunker = MagicMock()
    test_chunks = [
        Chunk(
            chunk_id="chunk-001",
            files=[file1],
            total_size_bytes=1024,
        ),
        Chunk(
            chunk_id="chunk-002",
            files=[file2],
            total_size_bytes=2048,
        ),
    ]
    mock_chunker.create_chunks = MagicMock(return_value=test_chunks)

    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
    )

    # Track chunk callback calls
    chunk_updates = []

    def chunk_callback(chunk_num, chunk_id, files, size_mb):
        chunk_updates.append(
            {
                "chunk_num": chunk_num,
                "chunk_id": chunk_id,
                "files": files,
                "size_mb": size_mb,
            }
        )

    orchestrator.chunk_callback = chunk_callback

    # Run extraction
    await orchestrator.extract()

    # Verify chunk_callback was called for each chunk
    assert len(chunk_updates) == 2

    # Check first chunk
    assert chunk_updates[0]["chunk_num"] == 1
    assert chunk_updates[0]["chunk_id"] == "chunk-001"
    assert chunk_updates[0]["files"] == [file1]
    assert chunk_updates[0]["size_mb"] == pytest.approx(1024 / (1024 * 1024))

    # Check second chunk
    assert chunk_updates[1]["chunk_num"] == 2
    assert chunk_updates[1]["chunk_id"] == "chunk-002"
    assert chunk_updates[1]["files"] == [file2]
    assert chunk_updates[1]["size_mb"] == pytest.approx(2048 / (1024 * 1024))


@pytest.mark.asyncio
async def test_orchestrator_chunk_callback_with_stats(tmp_path):
    """Test orchestrator works with both chunk_callback and stats_callback."""
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create test file
    file1 = data_dir / "file1.py"
    file1.write_text("# test file 1\n" * 50)  # ~1KB

    config = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Mock extraction agent with entities
    from kg_extractor.models import Entity

    mock_agent = MagicMock()
    mock_result = MagicMock()
    # Create real Entity objects for deduplication
    mock_result.entities = [
        Entity(id="urn:Test:1", type="Test", name="Test1", properties={}),
        Entity(id="urn:Test:2", type="Test", name="Test2", properties={}),
    ]
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)
    # Add llm_client mock
    mock_agent.llm_client = MagicMock()
    mock_agent.llm_client.last_usage = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_cost_usd": 0.01,
    }

    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(return_value=[file1])

    mock_chunker = MagicMock()
    mock_chunker.create_chunks = MagicMock(
        return_value=[
            Chunk(
                chunk_id="chunk-001",
                files=[file1],
                total_size_bytes=1024,
            )
        ]
    )

    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
    )

    # Track both callbacks
    chunk_calls = []
    stats_calls = []

    orchestrator.chunk_callback = lambda **kwargs: chunk_calls.append(kwargs)
    orchestrator.stats_callback = lambda **kwargs: stats_calls.append(kwargs)

    # Run extraction
    await orchestrator.extract()

    # Both callbacks should have been called
    assert len(chunk_calls) == 1
    assert len(stats_calls) == 1

    # Chunk callback should have chunk info
    assert chunk_calls[0]["chunk_id"] == "chunk-001"

    # Stats callback should have entities
    assert len(stats_calls[0]["entities"]) == 2
