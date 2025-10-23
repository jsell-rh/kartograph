"""Unit tests for extraction orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_orchestrator_basic_workflow():
    """Test ExtractionOrchestrator basic extraction workflow."""
    from kg_extractor.config import (
        AuthConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
        ValidationConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temp directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        # Create test file
        (data_dir / "test.yaml").write_text("test: data")

        # Create mock components
        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = [data_dir / "test.yaml"]

        mock_chunker = MagicMock()
        from kg_extractor.chunking.models import Chunk

        mock_chunker.create_chunks.return_value = [
            Chunk(
                chunk_id="chunk-000",
                files=[data_dir / "test.yaml"],
                total_size_bytes=100,
            )
        ]

        mock_agent = AsyncMock()
        from kg_extractor.models import Entity, ExtractionResult

        mock_agent.extract.return_value = ExtractionResult(
            entities=[
                Entity(
                    id="urn:Service:api1",
                    type="Service",
                    name="API 1",
                )
            ],
            chunk_id="chunk-000",
            validation_errors=[],
            metadata={"entity_count": 1},
        )

        mock_deduplicator = MagicMock()
        from kg_extractor.deduplication.models import (
            DeduplicationMetrics,
            DeduplicationResult,
        )

        mock_deduplicator.deduplicate.return_value = DeduplicationResult(
            entities=[
                Entity(
                    id="urn:Service:api1",
                    type="Service",
                    name="API 1",
                )
            ],
            metrics=DeduplicationMetrics(
                total_input_entities=1,
                total_output_entities=1,
                duplicates_found=0,
                duplicates_merged=0,
                merge_operations=0,
            ),
        )

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
            chunking=ChunkingConfig(),
            deduplication=DeduplicationConfig(),
            validation=ValidationConfig(),
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        # Run extraction
        result = await orchestrator.extract()

        # Verify workflow
        assert len(result.entities) == 1
        assert result.entities[0].id == "urn:Service:api1"
        assert result.metrics.total_chunks == 1
        assert result.metrics.chunks_processed == 1
        assert result.metrics.entities_extracted == 1


@pytest.mark.asyncio
async def test_orchestrator_multiple_chunks():
    """Test ExtractionOrchestrator with multiple chunks."""
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

        # Create mock components
        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = [
            data_dir / "file1.yaml",
            data_dir / "file2.yaml",
        ]

        mock_chunker = MagicMock()
        mock_chunker.create_chunks.return_value = [
            Chunk(
                chunk_id="chunk-000",
                files=[data_dir / "file1.yaml"],
                total_size_bytes=100,
            ),
            Chunk(
                chunk_id="chunk-001",
                files=[data_dir / "file2.yaml"],
                total_size_bytes=100,
            ),
        ]

        mock_agent = AsyncMock()
        # Return different entities for each chunk
        mock_agent.extract.side_effect = [
            ExtractionResult(
                entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
                chunk_id="chunk-000",
                validation_errors=[],
                metadata={},
            ),
            ExtractionResult(
                entities=[Entity(id="urn:Service:api2", type="Service", name="API 2")],
                chunk_id="chunk-001",
                validation_errors=[],
                metadata={},
            ),
        ]

        mock_deduplicator = MagicMock()
        mock_deduplicator.deduplicate.return_value = DeduplicationResult(
            entities=[
                Entity(id="urn:Service:api1", type="Service", name="API 1"),
                Entity(id="urn:Service:api2", type="Service", name="API 2"),
            ],
            metrics=DeduplicationMetrics(
                total_input_entities=2,
                total_output_entities=2,
                duplicates_found=0,
                duplicates_merged=0,
                merge_operations=0,
            ),
        )

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        result = await orchestrator.extract()

        # Verify both chunks were processed
        assert len(result.entities) == 2
        assert result.metrics.total_chunks == 2
        assert result.metrics.chunks_processed == 2
        assert result.metrics.entities_extracted == 2


@pytest.mark.asyncio
async def test_orchestrator_deduplication():
    """Test ExtractionOrchestrator deduplicates entities."""
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

        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = [data_dir / "test.yaml"]

        mock_chunker = MagicMock()
        mock_chunker.create_chunks.return_value = [
            Chunk(
                chunk_id="chunk-000",
                files=[data_dir / "test.yaml"],
                total_size_bytes=100,
            )
        ]

        mock_agent = AsyncMock()
        # Return duplicate entities
        mock_agent.extract.return_value = ExtractionResult(
            entities=[
                Entity(id="urn:Service:api1", type="Service", name="API 1"),
                Entity(id="urn:Service:api1", type="Service", name="API 1 Duplicate"),
            ],
            chunk_id="chunk-000",
            validation_errors=[],
            metadata={},
        )

        mock_deduplicator = MagicMock()
        # Deduplicator returns only 1 entity
        mock_deduplicator.deduplicate.return_value = DeduplicationResult(
            entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
            metrics=DeduplicationMetrics(
                total_input_entities=2,
                total_output_entities=1,
                duplicates_found=1,
                duplicates_merged=1,
                merge_operations=1,
            ),
        )

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        result = await orchestrator.extract()

        # Verify deduplication happened
        assert len(result.entities) == 1
        mock_deduplicator.deduplicate.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_empty_directory():
    """Test ExtractionOrchestrator with empty directory."""
    from kg_extractor.config import AuthConfig, ExtractionConfig
    from kg_extractor.orchestrator import ExtractionOrchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = []

        mock_chunker = MagicMock()
        mock_chunker.create_chunks.return_value = []

        mock_agent = AsyncMock()
        mock_deduplicator = MagicMock()

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        result = await orchestrator.extract()

        # Verify no processing happened
        assert len(result.entities) == 0
        assert result.metrics.total_chunks == 0
        assert result.metrics.chunks_processed == 0
        mock_agent.extract.assert_not_called()
        mock_deduplicator.deduplicate.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_tracks_validation_errors():
    """Test ExtractionOrchestrator tracks validation errors."""
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import AuthConfig, ExtractionConfig
    from kg_extractor.deduplication.models import (
        DeduplicationMetrics,
        DeduplicationResult,
    )
    from kg_extractor.models import Entity, ExtractionResult, ValidationError
    from kg_extractor.orchestrator import ExtractionOrchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = [data_dir / "test.yaml"]

        mock_chunker = MagicMock()
        mock_chunker.create_chunks.return_value = [
            Chunk(
                chunk_id="chunk-000",
                files=[data_dir / "test.yaml"],
                total_size_bytes=100,
            )
        ]

        mock_agent = AsyncMock()
        mock_agent.extract.return_value = ExtractionResult(
            entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
            chunk_id="chunk-000",
            validation_errors=[
                ValidationError(
                    entity_id="urn:Service:api1",
                    field="description",
                    message="Missing description",
                    severity="warning",
                )
            ],
            metadata={},
        )

        mock_deduplicator = MagicMock()
        mock_deduplicator.deduplicate.return_value = DeduplicationResult(
            entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
            metrics=DeduplicationMetrics(
                total_input_entities=1,
                total_output_entities=1,
                duplicates_found=0,
                duplicates_merged=0,
                merge_operations=0,
            ),
        )

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
        )

        result = await orchestrator.extract()

        # Verify validation errors are tracked
        assert result.metrics.validation_errors == 1


@pytest.mark.asyncio
async def test_orchestrator_progress_callback():
    """Test ExtractionOrchestrator calls progress callback."""
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

        mock_file_system = MagicMock()
        mock_file_system.list_files.return_value = [
            data_dir / "file1.yaml",
            data_dir / "file2.yaml",
        ]

        mock_chunker = MagicMock()
        mock_chunker.create_chunks.return_value = [
            Chunk(
                chunk_id="chunk-000",
                files=[data_dir / "file1.yaml"],
                total_size_bytes=100,
            ),
            Chunk(
                chunk_id="chunk-001",
                files=[data_dir / "file2.yaml"],
                total_size_bytes=100,
            ),
        ]

        mock_agent = AsyncMock()
        mock_agent.extract.return_value = ExtractionResult(
            entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
            chunk_id="chunk-000",
            validation_errors=[],
            metadata={},
        )

        mock_deduplicator = MagicMock()
        mock_deduplicator.deduplicate.return_value = DeduplicationResult(
            entities=[Entity(id="urn:Service:api1", type="Service", name="API 1")],
            metrics=DeduplicationMetrics(
                total_input_entities=1,
                total_output_entities=1,
                duplicates_found=0,
                duplicates_merged=0,
                merge_operations=0,
            ),
        )

        config = ExtractionConfig(
            data_dir=data_dir,
            output_file=Path(tmpdir) / "output.jsonld",
            auth=AuthConfig(
                auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
            ),
        )

        # Track progress callbacks
        progress_calls = []

        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))

        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_file_system,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            deduplicator=mock_deduplicator,
            progress_callback=progress_callback,
        )

        await orchestrator.extract()

        # Verify progress was reported
        assert len(progress_calls) >= 2
        assert progress_calls[0][0] == 1  # First chunk
        assert progress_calls[1][0] == 2  # Second chunk
        assert all(call[1] == 2 for call in progress_calls)  # Total = 2
