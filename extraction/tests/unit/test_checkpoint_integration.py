"""Unit tests for checkpoint integration in ExtractionOrchestrator."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_checkpoint_saves_and_restores_entities(tmp_path):
    """Test that checkpoint saves entities and restores them correctly."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.models import Entity
    from kg_extractor.orchestrator import ExtractionOrchestrator

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create config with checkpoint enabled
    config = ExtractionConfig(
        data_dir=data_dir,
        checkpoint=CheckpointConfig(
            enabled=True,
            strategy="per_chunk",
            checkpoint_dir=checkpoint_dir,
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Create test entities
    test_entities = [
        Entity(
            id="urn:Service:api-1",
            type="Service",
            name="API Service 1",
            description="Test service",
            properties={"language": "Python"},
        ),
        Entity(
            id="urn:Service:api-2",
            type="Service",
            name="API Service 2",
            properties={"language": "Go"},
        ),
    ]

    # Mock extraction agent to return test entities
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = test_entities
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    # Mock file system and chunker
    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(return_value=[Path("/test/file1.py")])

    mock_chunker = MagicMock()
    mock_chunker.create_chunks = MagicMock(
        return_value=[
            Chunk(
                chunk_id="chunk-001",
                files=[Path("/test/file1.py")],
                total_size_bytes=1024,
            )
        ]
    )

    # Create orchestrator and run extraction
    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
    )

    result = await orchestrator.extract()

    # Verify entities were extracted
    assert len(result.entities) == 2
    assert result.entities[0].id == "urn:Service:api-1"
    assert result.entities[1].id == "urn:Service:api-2"

    # Verify checkpoint was saved with entities
    checkpoint_store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)
    checkpoint = checkpoint_store.load_checkpoint("latest")

    assert checkpoint is not None
    assert len(checkpoint.entities) == 2
    assert checkpoint.entities[0]["@id"] == "urn:Service:api-1"
    assert checkpoint.entities[0]["@type"] == "Service"
    assert checkpoint.entities[0]["name"] == "API Service 1"
    assert checkpoint.entities[0]["language"] == "Python"
    assert checkpoint.entities[1]["@id"] == "urn:Service:api-2"

    # Test restoration
    restored_entities = orchestrator._entities_from_checkpoint_data(checkpoint)
    assert len(restored_entities) == 2
    assert restored_entities[0].id == "urn:Service:api-1"
    assert restored_entities[0].name == "API Service 1"
    assert restored_entities[0].properties["language"] == "Python"
    assert restored_entities[1].id == "urn:Service:api-2"


@pytest.mark.asyncio
async def test_orchestrator_saves_checkpoint_per_chunk(tmp_path):
    """Test orchestrator saves checkpoint after each chunk when strategy is per_chunk."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()

    # Create config with checkpoint enabled
    config = ExtractionConfig(
        data_dir=data_dir,
        checkpoint=CheckpointConfig(
            enabled=True,
            strategy="per_chunk",
            checkpoint_dir=checkpoint_dir,
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count", max_files_per_chunk=2),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Mock checkpoint store
    mock_store = MagicMock(spec=DiskCheckpointStore)
    mock_store.load_checkpoint = MagicMock(side_effect=FileNotFoundError)

    # Mock extraction agent
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    # Mock file system
    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(
        return_value=[Path(f"/test/file{i}.py") for i in range(4)]
    )

    # Mock chunker
    from kg_extractor.chunking.models import Chunk

    mock_chunker = MagicMock()
    mock_chunker.create_chunks = MagicMock(
        return_value=[
            Chunk(
                chunk_id="chunk-001",
                files=[Path("/test/file0.py"), Path("/test/file1.py")],
            ),
            Chunk(
                chunk_id="chunk-002",
                files=[Path("/test/file2.py"), Path("/test/file3.py")],
            ),
        ]
    )

    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
        checkpoint_store=mock_store,
    )

    result = await orchestrator.extract()

    # Should have saved checkpoint after each chunk (2 chunks = 2 saves)
    assert mock_store.save_checkpoint.call_count == 2

    # Verify checkpoint structure
    saved_checkpoints = [
        call[0][0] for call in mock_store.save_checkpoint.call_args_list
    ]
    assert all(isinstance(cp, Checkpoint) for cp in saved_checkpoints)
    assert saved_checkpoints[0].chunks_processed == 1
    assert saved_checkpoints[1].chunks_processed == 2


@pytest.mark.asyncio
async def test_orchestrator_saves_checkpoint_every_n(tmp_path):
    """Test orchestrator saves checkpoint every N chunks."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "checkpoints").mkdir(exist_ok=True)
    (tmp_path / "test").mkdir(exist_ok=True)

    config = ExtractionConfig(
        data_dir=tmp_path / "data",
        checkpoint=CheckpointConfig(
            enabled=True,
            strategy="every_n",
            every_n_chunks=2,  # Save every 2 chunks
            checkpoint_dir=tmp_path / "checkpoints",
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    mock_store = MagicMock(spec=DiskCheckpointStore)
    mock_store.load_checkpoint = MagicMock(side_effect=FileNotFoundError)

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(
        return_value=[Path(f"/test/file{i}.py") for i in range(5)]
    )

    mock_chunker = MagicMock()
    mock_chunker.create_chunks = MagicMock(
        return_value=[
            Chunk(chunk_id=f"chunk-{i:03d}", files=[Path(f"/test/file{i}.py")])
            for i in range(5)
        ]
    )

    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
        checkpoint_store=mock_store,
    )

    await orchestrator.extract()

    # Should save at chunks 2 and 4 (every 2 chunks), not 1, 3, or 5
    # Total: 2 saves for 5 chunks
    assert mock_store.save_checkpoint.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_resumes_from_checkpoint(tmp_path):
    """Test orchestrator resumes extraction from checkpoint."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "checkpoints").mkdir(exist_ok=True)
    (tmp_path / "test").mkdir(exist_ok=True)

    config_hash = "test_hash_12345"

    config = ExtractionConfig(
        data_dir=tmp_path / "data",
        resume=True,  # Request resume
        checkpoint=CheckpointConfig(
            enabled=True,
            strategy="per_chunk",
            checkpoint_dir=tmp_path / "checkpoints",
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Mock existing checkpoint (2 chunks already processed)
    existing_checkpoint = Checkpoint(
        checkpoint_id="latest",
        config_hash=config_hash,
        chunks_processed=2,
        entities_extracted=50,
        timestamp=datetime.now(),
        metadata={"total_chunks": 4},
    )

    mock_store = MagicMock(spec=DiskCheckpointStore)
    mock_store.load_checkpoint = MagicMock(return_value=existing_checkpoint)

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(
        return_value=[Path(f"/test/file{i}.py") for i in range(4)]
    )

    mock_chunker = MagicMock()
    chunks = [
        Chunk(chunk_id=f"chunk-{i:03d}", files=[Path(f"/test/file{i}.py")])
        for i in range(4)
    ]
    mock_chunker.create_chunks = MagicMock(return_value=chunks)

    # Patch compute_hash to return matching hash
    with patch.object(config, "compute_hash", return_value=config_hash):
        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_fs,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            checkpoint_store=mock_store,
        )

        await orchestrator.extract()

    # Should have attempted to load checkpoint
    mock_store.load_checkpoint.assert_called_once_with("latest")

    # Should only process remaining chunks (chunks 2 and 3, indices 2 and 3)
    # Not chunks 0 and 1 (already processed)
    assert mock_agent.extract.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_ignores_checkpoint_with_mismatched_config(tmp_path):
    """Test orchestrator ignores checkpoint when config hash doesn't match."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "checkpoints").mkdir(exist_ok=True)
    (tmp_path / "test").mkdir(exist_ok=True)

    config = ExtractionConfig(
        data_dir=tmp_path / "data",
        resume=True,
        checkpoint=CheckpointConfig(
            enabled=True,
            strategy="per_chunk",
            checkpoint_dir=tmp_path / "checkpoints",
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    # Checkpoint has different config hash
    existing_checkpoint = Checkpoint(
        checkpoint_id="latest",
        config_hash="old_hash_different",  # Different from current
        chunks_processed=2,
        entities_extracted=50,
        timestamp=datetime.now(),
        metadata={},
    )

    mock_store = MagicMock(spec=DiskCheckpointStore)
    mock_store.load_checkpoint = MagicMock(return_value=existing_checkpoint)

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(
        return_value=[Path(f"/test/file{i}.py") for i in range(4)]
    )

    mock_chunker = MagicMock()
    chunks = [
        Chunk(chunk_id=f"chunk-{i:03d}", files=[Path(f"/test/file{i}.py")])
        for i in range(4)
    ]
    mock_chunker.create_chunks = MagicMock(return_value=chunks)

    # Current hash is different
    with patch.object(config, "compute_hash", return_value="new_hash_current"):
        orchestrator = ExtractionOrchestrator(
            config=config,
            file_system=mock_fs,
            chunker=mock_chunker,
            extraction_agent=mock_agent,
            checkpoint_store=mock_store,
        )

        await orchestrator.extract()

    # Should process ALL chunks (not resume) because hash mismatch
    assert mock_agent.extract.call_count == 4


@pytest.mark.asyncio
async def test_orchestrator_checkpoint_disabled(tmp_path):
    """Test orchestrator doesn't save checkpoints when disabled."""
    from kg_extractor.chunking.models import Chunk
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        DeduplicationConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "checkpoints").mkdir(exist_ok=True)
    (tmp_path / "test").mkdir(exist_ok=True)

    config = ExtractionConfig(
        data_dir=tmp_path / "data",
        checkpoint=CheckpointConfig(
            enabled=False,  # Disabled
            strategy="per_chunk",
            checkpoint_dir=tmp_path / "checkpoints",
        ),
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="count"),
        deduplication=DeduplicationConfig(strategy="urn"),
    )

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.entities = []
    mock_result.validation_errors = []
    mock_agent.extract = AsyncMock(return_value=mock_result)

    mock_fs = MagicMock()
    mock_fs.list_files = MagicMock(return_value=[Path("/test/file.py")])

    mock_chunker = MagicMock()
    mock_chunker.create_chunks = MagicMock(
        return_value=[Chunk(chunk_id="chunk-001", files=[Path("/test/file.py")])]
    )

    orchestrator = ExtractionOrchestrator(
        config=config,
        file_system=mock_fs,
        chunker=mock_chunker,
        extraction_agent=mock_agent,
    )

    await orchestrator.extract()

    # Checkpoint store should not be created
    assert orchestrator.checkpoint_store is None


@pytest.mark.asyncio
async def test_orchestrator_checkpoint_validates_config_hash(tmp_path):
    """Test orchestrator validates config hash on checkpoint load."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint
    from kg_extractor.config import (
        AuthConfig,
        CheckpointConfig,
        ChunkingConfig,
        ExtractionConfig,
    )
    from kg_extractor.orchestrator import ExtractionOrchestrator

    # Create temporary directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "checkpoints").mkdir(exist_ok=True)
    (tmp_path / "test").mkdir(exist_ok=True)

    # Test config hash computation
    config1 = ExtractionConfig(
        data_dir=tmp_path / "test",
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="hybrid", target_size_mb=10),
        checkpoint=CheckpointConfig(enabled=True),
    )

    config2 = ExtractionConfig(
        data_dir=tmp_path / "test",
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="hybrid", target_size_mb=20),  # Different!
        checkpoint=CheckpointConfig(enabled=True),
    )

    # Different chunking configs should produce different hashes
    hash1 = config1.compute_hash()
    hash2 = config2.compute_hash()

    assert hash1 != hash2

    # Same config should produce same hash
    config1_copy = ExtractionConfig(
        data_dir=tmp_path / "test",
        auth=AuthConfig(auth_method="api_key", api_key="test"),
        chunking=ChunkingConfig(strategy="hybrid", target_size_mb=10),
        checkpoint=CheckpointConfig(enabled=True),
    )

    assert config1.compute_hash() == config1_copy.compute_hash()
