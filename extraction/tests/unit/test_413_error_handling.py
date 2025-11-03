"""Tests for 413 error handling (prompt too long)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kg_extractor.exceptions import PromptTooLongError


def test_prompt_too_long_error_basic():
    """Test PromptTooLongError exception creation."""
    error = PromptTooLongError("Test message")
    assert str(error) == "Test message"
    assert error.chunk_size is None

    error_with_size = PromptTooLongError("Test message", chunk_size=100)
    assert error_with_size.chunk_size == 100


def test_agent_client_detects_413_error():
    """Test that AgentClient detects and raises PromptTooLongError on 413 response."""
    from kg_extractor.llm.agent_client import AgentClient

    client = AgentClient(
        auth_config=MagicMock(),
        model="claude-sonnet-4-5@20250929",
    )

    # Test with API Error: 413 pattern
    response_413 = 'API Error: 413 {"type":"error","error":{"type":"invalid_request_error","message":"Prompt is too long"}}'

    with pytest.raises(PromptTooLongError, match="Prompt exceeds model context window"):
        client._parse_extraction_result(response_413)


def test_agent_client_detects_413_json_error():
    """Test that AgentClient detects 413 error in JSON error response."""
    from kg_extractor.llm.agent_client import AgentClient

    client = AgentClient(
        auth_config=MagicMock(),
        model="claude-sonnet-4-5@20250929",
    )

    # Test with embedded JSON error
    response_json = (
        '"error":{"type":"invalid_request_error","message":"Prompt is too long"}'
    )

    with pytest.raises(PromptTooLongError):
        client._parse_extraction_result(response_json)


def test_agent_client_parses_valid_json():
    """Test that AgentClient still parses valid JSON responses correctly."""
    from kg_extractor.llm.agent_client import AgentClient

    client = AgentClient(
        auth_config=MagicMock(),
        model="claude-sonnet-4-5@20250929",
    )

    # Valid response
    response = '{"entities": [{"@id": "urn:test:1", "@type": "Test", "name": "Test"}], "metadata": {}}'

    result = client._parse_extraction_result(response)

    assert "entities" in result
    assert len(result["entities"]) == 1
    assert result["entities"][0]["@id"] == "urn:test:1"


def test_agent_client_parses_json_in_code_block():
    """Test that AgentClient extracts JSON from markdown code blocks."""
    from kg_extractor.llm.agent_client import AgentClient

    client = AgentClient(
        auth_config=MagicMock(),
        model="claude-sonnet-4-5@20250929",
    )

    # Response with JSON in code block
    response = """Here are the entities:

```json
{"entities": [{"@id": "urn:test:1", "@type": "Test", "name": "Test"}], "metadata": {}}
```

That's all!"""

    result = client._parse_extraction_result(response)

    assert "entities" in result
    assert len(result["entities"]) == 1


@pytest.mark.asyncio
async def test_orchestrator_splits_chunk_on_413():
    """Test that orchestrator splits chunks when encountering 413 errors."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import ExtractionConfig
    from kg_extractor.models import ExtractionResult, Entity
    from kg_extractor.orchestrator import ExtractionOrchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        files = []
        for i in range(4):
            file_path = data_dir / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)

        # Create config
        from kg_extractor.config import AuthConfig

        config = ExtractionConfig(
            data_dir=data_dir,
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        # Create mock agent that raises PromptTooLongError on first call, then succeeds
        mock_agent = AsyncMock(spec=ExtractionAgent)
        call_count = 0

        async def extract_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # First call with all 4 files - raise 413
            files_arg = kwargs.get("files", [])
            if len(files_arg) == 4:
                raise PromptTooLongError(
                    "Prompt exceeds model context window",
                    chunk_size=None,
                )

            # Subsequent calls with split chunks - succeed
            chunk_id = kwargs.get("chunk_id", "unknown")
            # Make unique entities by using chunk_id + file path
            entities = [
                Entity(
                    id=f"urn:test:{chunk_id}:{f.name}",
                    type="Test",
                    name=f"Test {f.name}",
                )
                for f in files_arg
            ]
            return ExtractionResult(
                chunk_id=chunk_id,
                entities=entities,
                validation_errors=[],
            )

        mock_agent.extract.side_effect = extract_side_effect
        # Add llm_client mock for parallel execution
        mock_agent.llm_client = MagicMock()
        mock_agent.llm_client.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost_usd": 0.01,
        }

        # Create orchestrator
        with patch("kg_extractor.orchestrator.DiskFileSystem") as mock_fs_class:
            with patch("kg_extractor.orchestrator.HybridChunker") as mock_chunker_class:
                # Mock file system
                mock_fs = MagicMock()
                mock_fs.list_files.return_value = files
                mock_fs_class.return_value = mock_fs

                # Mock chunker to return one chunk with all files
                mock_chunker = MagicMock()
                total_size = sum(f.stat().st_size for f in files)
                initial_chunk = Chunk(
                    chunk_id="chunk-000",
                    files=files,
                    total_size_bytes=total_size,
                )
                mock_chunker.create_chunks.return_value = [initial_chunk]
                mock_chunker_class.return_value = mock_chunker

                # Create orchestrator with mock agent
                orchestrator = ExtractionOrchestrator(
                    config=config,
                    file_system=mock_fs,
                    chunker=mock_chunker,
                    extraction_agent=mock_agent,
                )

                # Run extraction
                result = await orchestrator.extract()

                # Verify chunk was split and retried
                # Should have been called 3 times:
                # 1. Initial chunk with 4 files (fails with 413)
                # 2. First half with 2 files (succeeds)
                # 3. Second half with 2 files (succeeds)
                assert call_count == 3

                # Verify entities extracted from both split chunks
                # 2 entities from first half + 2 from second half = 4 total
                assert len(result.entities) == 4


@pytest.mark.asyncio
async def test_orchestrator_skips_unsplittable_chunk():
    """Test that orchestrator skips chunk that cannot be split (single file)."""
    from kg_extractor.agents.extraction import ExtractionAgent
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import ExtractionConfig
    from kg_extractor.orchestrator import ExtractionOrchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create single test file
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        file_path = data_dir / "file.txt"
        file_path.write_text("content" * 1000)  # Large file
        files = [file_path]

        # Create config
        from kg_extractor.config import AuthConfig

        config = ExtractionConfig(
            data_dir=data_dir,
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        # Create mock agent that always raises PromptTooLongError
        mock_agent = AsyncMock(spec=ExtractionAgent)
        mock_agent.extract.side_effect = PromptTooLongError(
            "Prompt exceeds model context window"
        )
        # Add llm_client mock for parallel execution
        mock_agent.llm_client = MagicMock()
        mock_agent.llm_client.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost_usd": 0.01,
        }

        # Create orchestrator
        with patch("kg_extractor.orchestrator.DiskFileSystem") as mock_fs_class:
            with patch("kg_extractor.orchestrator.HybridChunker") as mock_chunker_class:
                # Mock file system
                mock_fs = MagicMock()
                mock_fs.list_files.return_value = files
                mock_fs_class.return_value = mock_fs

                # Mock chunker to return one chunk with single file
                mock_chunker = MagicMock()
                chunk = Chunk(
                    chunk_id="chunk-000",
                    files=files,
                    total_size_bytes=file_path.stat().st_size,
                )
                mock_chunker.create_chunks.return_value = [chunk]
                mock_chunker_class.return_value = mock_chunker

                # Create orchestrator with mock agent
                orchestrator = ExtractionOrchestrator(
                    config=config,
                    file_system=mock_fs,
                    chunker=mock_chunker,
                    extraction_agent=mock_agent,
                )

                # Run extraction - should complete without error (skips chunk)
                result = await orchestrator.extract()

                # Should have 0 entities (chunk was skipped)
                assert len(result.entities) == 0
                assert mock_agent.extract.call_count == 1  # Tried once, then skipped
