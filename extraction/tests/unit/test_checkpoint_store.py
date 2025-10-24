"""Unit tests for checkpoint store interface."""

from datetime import datetime
from pathlib import Path

import pytest


def test_checkpoint_store_protocol():
    """Test CheckpointStore protocol defines required methods."""
    from kg_extractor.checkpoint.protocol import CheckpointStore

    # Protocol should define required methods
    assert hasattr(CheckpointStore, "save_checkpoint")
    assert hasattr(CheckpointStore, "load_checkpoint")
    assert hasattr(CheckpointStore, "list_checkpoints")
    assert hasattr(CheckpointStore, "delete_checkpoint")


def test_checkpoint_model():
    """Test Checkpoint model structure."""
    from kg_extractor.checkpoint.models import Checkpoint

    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123def456",  # pragma: allowlist secret
        chunks_processed=5,
        entities_extracted=150,
        timestamp=datetime.now(),
        metadata={"duration": 120.5},
    )

    assert checkpoint.checkpoint_id == "chunk-001"
    assert checkpoint.config_hash == "abc123def456"  # pragma: allowlist secret
    assert checkpoint.chunks_processed == 5
    assert checkpoint.entities_extracted == 150
    assert checkpoint.metadata["duration"] == 120.5


def test_disk_checkpoint_store_save_and_load(tmp_path: Path):
    """Test DiskCheckpointStore saves and loads checkpoints."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    checkpoint_dir = tmp_path / ".checkpoints"
    store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)

    # Create checkpoint
    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=5,
        entities_extracted=150,
        timestamp=datetime.now(),
    )

    # Save checkpoint
    store.save_checkpoint(checkpoint)

    # Load checkpoint
    loaded = store.load_checkpoint("chunk-001")

    assert loaded is not None
    assert loaded.checkpoint_id == "chunk-001"
    assert loaded.config_hash == "abc123"
    assert loaded.chunks_processed == 5
    assert loaded.entities_extracted == 150


def test_disk_checkpoint_store_load_nonexistent(tmp_path: Path):
    """Test DiskCheckpointStore returns None for missing checkpoint."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore

    checkpoint_dir = tmp_path / ".checkpoints"
    store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)

    loaded = store.load_checkpoint("nonexistent")
    assert loaded is None


def test_disk_checkpoint_store_list_checkpoints(tmp_path: Path):
    """Test DiskCheckpointStore lists all checkpoints."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    checkpoint_dir = tmp_path / ".checkpoints"
    store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)

    # Save multiple checkpoints
    for i in range(3):
        checkpoint = Checkpoint(
            checkpoint_id=f"chunk-{i:03d}",
            config_hash="abc123",
            chunks_processed=i + 1,
            entities_extracted=(i + 1) * 30,
            timestamp=datetime.now(),
        )
        store.save_checkpoint(checkpoint)

    # List checkpoints
    checkpoints = store.list_checkpoints()

    # 3 chunk checkpoints + 1 metadata file
    assert len(checkpoints) == 4
    assert "chunk-000" in checkpoints
    assert "chunk-001" in checkpoints
    assert "chunk-002" in checkpoints


def test_disk_checkpoint_store_delete_checkpoint(tmp_path: Path):
    """Test DiskCheckpointStore deletes checkpoints."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    checkpoint_dir = tmp_path / ".checkpoints"
    store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)

    # Save checkpoint
    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=1,
        entities_extracted=30,
        timestamp=datetime.now(),
    )
    store.save_checkpoint(checkpoint)

    # Delete checkpoint
    store.delete_checkpoint("chunk-001")

    # Verify deleted
    loaded = store.load_checkpoint("chunk-001")
    assert loaded is None


def test_disk_checkpoint_store_creates_directory(tmp_path: Path):
    """Test DiskCheckpointStore creates checkpoint directory if missing."""
    from kg_extractor.checkpoint.disk_store import DiskCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    checkpoint_dir = tmp_path / ".checkpoints"
    assert not checkpoint_dir.exists()

    store = DiskCheckpointStore(checkpoint_dir=checkpoint_dir)

    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=1,
        entities_extracted=30,
        timestamp=datetime.now(),
    )
    store.save_checkpoint(checkpoint)

    # Directory should be created
    assert checkpoint_dir.exists()
    assert checkpoint_dir.is_dir()


def test_in_memory_checkpoint_store_save_and_load():
    """Test InMemoryCheckpointStore saves and loads checkpoints."""
    from kg_extractor.checkpoint.memory_store import InMemoryCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    store = InMemoryCheckpointStore()

    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=5,
        entities_extracted=150,
        timestamp=datetime.now(),
    )

    store.save_checkpoint(checkpoint)
    loaded = store.load_checkpoint("chunk-001")

    assert loaded is not None
    assert loaded.checkpoint_id == "chunk-001"
    assert loaded.config_hash == "abc123"


def test_in_memory_checkpoint_store_load_nonexistent():
    """Test InMemoryCheckpointStore returns None for missing checkpoint."""
    from kg_extractor.checkpoint.memory_store import InMemoryCheckpointStore

    store = InMemoryCheckpointStore()
    loaded = store.load_checkpoint("nonexistent")
    assert loaded is None


def test_in_memory_checkpoint_store_list_checkpoints():
    """Test InMemoryCheckpointStore lists all checkpoints."""
    from kg_extractor.checkpoint.memory_store import InMemoryCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    store = InMemoryCheckpointStore()

    for i in range(3):
        checkpoint = Checkpoint(
            checkpoint_id=f"chunk-{i:03d}",
            config_hash="abc123",
            chunks_processed=i + 1,
            entities_extracted=(i + 1) * 30,
            timestamp=datetime.now(),
        )
        store.save_checkpoint(checkpoint)

    checkpoints = store.list_checkpoints()
    # In-memory store has 3 checkpoints (no metadata file like disk store)
    assert len(checkpoints) == 3
    assert "chunk-000" in checkpoints


def test_in_memory_checkpoint_store_delete_checkpoint():
    """Test InMemoryCheckpointStore deletes checkpoints."""
    from kg_extractor.checkpoint.memory_store import InMemoryCheckpointStore
    from kg_extractor.checkpoint.models import Checkpoint

    store = InMemoryCheckpointStore()

    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=1,
        entities_extracted=30,
        timestamp=datetime.now(),
    )
    store.save_checkpoint(checkpoint)
    store.delete_checkpoint("chunk-001")

    loaded = store.load_checkpoint("chunk-001")
    assert loaded is None


def test_checkpoint_metadata_optional():
    """Test Checkpoint allows optional metadata."""
    from kg_extractor.checkpoint.models import Checkpoint

    # Without metadata
    checkpoint1 = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=1,
        entities_extracted=30,
        timestamp=datetime.now(),
    )
    assert checkpoint1.metadata == {}

    # With metadata
    checkpoint2 = Checkpoint(
        checkpoint_id="chunk-002",
        config_hash="abc123",
        chunks_processed=2,
        entities_extracted=60,
        timestamp=datetime.now(),
        metadata={"duration": 45.2, "errors": 0},
    )
    assert checkpoint2.metadata["duration"] == 45.2
    assert checkpoint2.metadata["errors"] == 0


def test_checkpoint_serialization():
    """Test Checkpoint can serialize to/from dict."""
    from kg_extractor.checkpoint.models import Checkpoint

    timestamp = datetime.now()
    checkpoint = Checkpoint(
        checkpoint_id="chunk-001",
        config_hash="abc123",
        chunks_processed=5,
        entities_extracted=150,
        timestamp=timestamp,
        metadata={"duration": 120.5},
    )

    # Serialize to dict
    data = checkpoint.model_dump()

    assert data["checkpoint_id"] == "chunk-001"
    assert data["config_hash"] == "abc123"
    assert data["chunks_processed"] == 5
    assert data["entities_extracted"] == 150
    assert data["metadata"]["duration"] == 120.5

    # Deserialize from dict
    loaded = Checkpoint.model_validate(data)
    assert loaded.checkpoint_id == checkpoint.checkpoint_id
    assert loaded.config_hash == checkpoint.config_hash
    assert loaded.chunks_processed == checkpoint.chunks_processed
