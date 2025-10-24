# Contract: Checkpoint Store Interface

## Purpose

Defines the boundary around checkpoint persistence to enable:

- **Testing without disk access** (in-memory checkpoints)
- **Swappable storage backends** (disk, S3, database)
- **Consistent error handling** across storage types
- **Resumable extraction** after failures
- **Progress tracking** across long-running operations

## Interface Definition

### Core Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
from pathlib import Path

class Checkpoint(BaseModel):
    """
    Checkpoint state for resumable extraction.

    Immutable snapshot of extraction progress.
    """
    # Metadata
    version: str = "1.0.0"
    checkpoint_id: str  # Unique identifier (e.g., timestamp-based)
    created_at: datetime = Field(default_factory=datetime.now)

    # Progress
    chunk_index: int
    total_chunks: int
    files_processed: int
    entities_extracted: int

    # State
    entities: list[dict]  # All entities extracted so far
    metrics: dict[str, Any]  # Accumulated metrics

    # Configuration hash (detect config changes)
    config_hash: str

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.chunk_index / self.total_chunks) * 100

    def is_complete(self) -> bool:
        """Check if extraction is complete."""
        return self.chunk_index >= self.total_chunks

    def is_compatible_with_config(self, current_config_hash: str) -> bool:
        """Check if checkpoint is compatible with current config."""
        return self.config_hash == current_config_hash

class CheckpointMetadata(BaseModel):
    """Lightweight checkpoint metadata (without full state)."""
    checkpoint_id: str
    created_at: datetime
    chunk_index: int
    total_chunks: int
    entities_extracted: int
    config_hash: str
```

### Core Protocol

```python
from typing import Protocol

class CheckpointStore(Protocol):
    """
    Abstract interface for checkpoint persistence.

    This protocol defines the boundary around checkpoint storage, enabling:
    - Testing with in-memory implementations
    - Swapping storage backends (disk, cloud, database)
    - Consistent error handling
    """

    def save(self, checkpoint: Checkpoint) -> None:
        """
        Save checkpoint to storage.

        Args:
            checkpoint: The checkpoint to save

        Raises:
            CheckpointSaveError: Failed to save checkpoint
            PermissionError: No write permission
        """
        ...

    def load(self, checkpoint_id: str) -> Checkpoint:
        """
        Load checkpoint by ID.

        Args:
            checkpoint_id: Unique checkpoint identifier

        Returns:
            The loaded checkpoint

        Raises:
            CheckpointNotFoundError: Checkpoint doesn't exist
            CheckpointLoadError: Failed to load/parse checkpoint
        """
        ...

    def find_latest(self) -> Checkpoint | None:
        """
        Find and load the most recent checkpoint.

        Returns:
            Latest checkpoint, or None if no checkpoints exist

        Raises:
            CheckpointLoadError: Failed to load checkpoint
        """
        ...

    def list_checkpoints(self) -> list[CheckpointMetadata]:
        """
        List all available checkpoints (sorted by creation time, newest first).

        Returns:
            List of checkpoint metadata (without full state)

        Raises:
            CheckpointStoreError: Failed to list checkpoints
        """
        ...

    def delete(self, checkpoint_id: str) -> None:
        """
        Delete checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint to delete

        Raises:
            CheckpointNotFoundError: Checkpoint doesn't exist
            CheckpointDeleteError: Failed to delete checkpoint
        """
        ...

    def clear_all(self) -> int:
        """
        Delete all checkpoints.

        Returns:
            Number of checkpoints deleted

        Raises:
            CheckpointStoreError: Failed to clear checkpoints
        """
        ...

    def exists(self, checkpoint_id: str) -> bool:
        """
        Check if checkpoint exists.

        Args:
            checkpoint_id: Checkpoint to check

        Returns:
            True if checkpoint exists, False otherwise
        """
        ...
```

### Exception Hierarchy

```python
class CheckpointStoreError(Exception):
    """Base class for checkpoint store errors."""
    pass

class CheckpointNotFoundError(CheckpointStoreError):
    """Checkpoint not found."""

    def __init__(self, checkpoint_id: str):
        self.checkpoint_id = checkpoint_id
        super().__init__(f"Checkpoint not found: {checkpoint_id}")

class CheckpointSaveError(CheckpointStoreError):
    """Failed to save checkpoint."""
    pass

class CheckpointLoadError(CheckpointStoreError):
    """Failed to load checkpoint."""
    pass

class CheckpointDeleteError(CheckpointStoreError):
    """Failed to delete checkpoint."""
    pass

class CheckpointVersionMismatchError(CheckpointStoreError):
    """Checkpoint version incompatible."""

    def __init__(self, found: str, expected: str):
        self.found = found
        self.expected = expected
        super().__init__(
            f"Checkpoint version mismatch: found {found}, expected {expected}"
        )

class CheckpointConfigMismatchError(CheckpointStoreError):
    """Checkpoint config hash doesn't match current config."""

    def __init__(self, message: str = "Configuration changed since checkpoint"):
        super().__init__(message)
```

## Implementations

### Production Implementation (Disk-Based)

```python
import json
from pathlib import Path
from datetime import datetime

class DiskCheckpointStore:
    """Disk-based checkpoint storage."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to disk."""
        try:
            # Save as numbered checkpoint
            checkpoint_file = self._get_checkpoint_path(checkpoint.checkpoint_id)
            with open(checkpoint_file, "w") as f:
                f.write(checkpoint.model_dump_json(indent=2))

            # Also save as "latest" for easy resume
            latest_file = self.checkpoint_dir / "checkpoint_latest.json"
            with open(latest_file, "w") as f:
                f.write(checkpoint.model_dump_json(indent=2))

        except Exception as e:
            raise CheckpointSaveError(f"Failed to save checkpoint: {e}") from e

    def load(self, checkpoint_id: str) -> Checkpoint:
        """Load checkpoint from disk."""
        checkpoint_file = self._get_checkpoint_path(checkpoint_id)

        if not checkpoint_file.exists():
            raise CheckpointNotFoundError(checkpoint_id)

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)
                return Checkpoint.model_validate(data)
        except Exception as e:
            raise CheckpointLoadError(f"Failed to load checkpoint: {e}") from e

    def find_latest(self) -> Checkpoint | None:
        """Find most recent checkpoint."""
        latest_file = self.checkpoint_dir / "checkpoint_latest.json"

        if not latest_file.exists():
            return None

        try:
            with open(latest_file) as f:
                data = json.load(f)
                return Checkpoint.model_validate(data)
        except Exception as e:
            raise CheckpointLoadError(f"Failed to load latest checkpoint: {e}") from e

    def list_checkpoints(self) -> list[CheckpointMetadata]:
        """List all checkpoints."""
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            # Skip "latest" symlink/copy
            if checkpoint_file.name == "checkpoint_latest.json":
                continue

            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                    # Load only metadata (don't load full entities)
                    metadata = CheckpointMetadata(
                        checkpoint_id=data["checkpoint_id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        chunk_index=data["chunk_index"],
                        total_chunks=data["total_chunks"],
                        entities_extracted=data["entities_extracted"],
                        config_hash=data["config_hash"],
                    )
                    checkpoints.append(metadata)
            except Exception:
                # Skip corrupted checkpoints
                continue

        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    def delete(self, checkpoint_id: str) -> None:
        """Delete checkpoint."""
        checkpoint_file = self._get_checkpoint_path(checkpoint_id)

        if not checkpoint_file.exists():
            raise CheckpointNotFoundError(checkpoint_id)

        try:
            checkpoint_file.unlink()
        except Exception as e:
            raise CheckpointDeleteError(f"Failed to delete checkpoint: {e}") from e

    def clear_all(self) -> int:
        """Delete all checkpoints."""
        count = 0
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                checkpoint_file.unlink()
                count += 1
            except Exception:
                pass  # Continue deleting others
        return count

    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists."""
        return self._get_checkpoint_path(checkpoint_id).exists()

    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """Get path for checkpoint file."""
        return self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
```

### Test Implementation (In-Memory)

```python
from typing import Dict

class InMemoryCheckpointStore:
    """In-memory checkpoint storage for testing."""

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._latest_id: str | None = None

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to memory."""
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        self._latest_id = checkpoint.checkpoint_id

    def load(self, checkpoint_id: str) -> Checkpoint:
        """Load checkpoint from memory."""
        if checkpoint_id not in self._checkpoints:
            raise CheckpointNotFoundError(checkpoint_id)
        return self._checkpoints[checkpoint_id]

    def find_latest(self) -> Checkpoint | None:
        """Find most recent checkpoint."""
        if self._latest_id is None:
            return None
        return self._checkpoints.get(self._latest_id)

    def list_checkpoints(self) -> list[CheckpointMetadata]:
        """List all checkpoints."""
        checkpoints = [
            CheckpointMetadata(
                checkpoint_id=cp.checkpoint_id,
                created_at=cp.created_at,
                chunk_index=cp.chunk_index,
                total_chunks=cp.total_chunks,
                entities_extracted=cp.entities_extracted,
                config_hash=cp.config_hash,
            )
            for cp in self._checkpoints.values()
        ]
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    def delete(self, checkpoint_id: str) -> None:
        """Delete checkpoint."""
        if checkpoint_id not in self._checkpoints:
            raise CheckpointNotFoundError(checkpoint_id)
        del self._checkpoints[checkpoint_id]
        if self._latest_id == checkpoint_id:
            self._latest_id = None

    def clear_all(self) -> int:
        """Clear all checkpoints."""
        count = len(self._checkpoints)
        self._checkpoints.clear()
        self._latest_id = None
        return count

    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists."""
        return checkpoint_id in self._checkpoints

    # Test helpers
    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Helper to add checkpoint during test setup."""
        self.save(checkpoint)

    def checkpoint_count(self) -> int:
        """Get number of checkpoints (for testing)."""
        return len(self._checkpoints)
```

## Usage Examples

### Production Usage

```python
from kg_extractor.progress import DiskCheckpointStore, Checkpoint
from pathlib import Path

# Create store
store = DiskCheckpointStore(checkpoint_dir=Path(".checkpoints"))

# Save checkpoint during extraction
checkpoint = Checkpoint(
    checkpoint_id=f"chunk_{chunk_index:04d}",
    chunk_index=chunk_index,
    total_chunks=total_chunks,
    files_processed=len(processed_files),
    entities_extracted=len(all_entities),
    entities=all_entities,
    metrics=current_metrics,
    config_hash=compute_hash(config),
)
store.save(checkpoint)

# Resume from latest checkpoint
latest = store.find_latest()
if latest:
    print(f"Resuming from checkpoint: {latest.progress_percent:.1f}% complete")
    all_entities = latest.entities
    start_chunk = latest.chunk_index + 1
else:
    print("No checkpoint found, starting from beginning")
    all_entities = []
    start_chunk = 0
```

### Testing Usage

```python
# tests/test_resumption.py
async def test_extraction_resumes_from_checkpoint():
    # Arrange: Create in-memory checkpoint store
    checkpoint_store = InMemoryCheckpointStore()

    # Simulate previous run that stopped at chunk 5
    previous_checkpoint = Checkpoint(
        checkpoint_id="chunk_0005",
        chunk_index=5,
        total_chunks=10,
        files_processed=50,
        entities_extracted=100,
        entities=[{"@id": "urn:service:foo", ...}],
        metrics={"entity_count": 100},
        config_hash="abc123",
    )
    checkpoint_store.add_checkpoint(previous_checkpoint)

    # Act: Resume extraction
    orchestrator = ExtractionOrchestrator(
        checkpoint_store=checkpoint_store,
        config=config_with_hash("abc123"),
        ...
    )
    result = await orchestrator.extract(resume=True)

    # Assert: Only processed remaining chunks
    assert result.chunks_processed == 5  # Chunks 6-10
    assert result.entity_count >= 100  # Previous + new entities
```

### Configuration Validation

```python
def resume_extraction(config: ExtractionConfig) -> ExtractionResult:
    """Resume extraction with config validation."""
    store = DiskCheckpointStore(config.checkpoint.checkpoint_dir)

    latest = store.find_latest()
    if not latest:
        raise ValueError("No checkpoint found to resume from")

    # Validate config compatibility
    current_hash = compute_config_hash(config)
    if not latest.is_compatible_with_config(current_hash):
        raise CheckpointConfigMismatchError(
            "Configuration changed since checkpoint. "
            "Clear checkpoints or revert config changes."
        )

    # Resume from checkpoint
    return extract_from_checkpoint(latest, config)
```

### Checkpoint Management CLI

```python
# extractor checkpoint list
def list_checkpoints_cli(checkpoint_dir: Path) -> None:
    """List available checkpoints."""
    store = DiskCheckpointStore(checkpoint_dir)
    checkpoints = store.list_checkpoints()

    if not checkpoints:
        print("No checkpoints found")
        return

    print(f"Found {len(checkpoints)} checkpoint(s):\n")
    for cp in checkpoints:
        print(f"ID: {cp.checkpoint_id}")
        print(f"  Created: {cp.created_at}")
        print(f"  Progress: {cp.chunk_index}/{cp.total_chunks} chunks")
        print(f"  Entities: {cp.entities_extracted}")
        print()

# extractor checkpoint clear
def clear_checkpoints_cli(checkpoint_dir: Path) -> None:
    """Clear all checkpoints."""
    store = DiskCheckpointStore(checkpoint_dir)
    count = store.clear_all()
    print(f"Deleted {count} checkpoint(s)")
```

## Design Rationale

### Why Separate Checkpoint and CheckpointMetadata?

**Performance**: Listing checkpoints shouldn't load full state

- Metadata is lightweight (KB)
- Full checkpoint may be large (GB with all entities)
- Can list many checkpoints quickly

### Why Immutable Checkpoint Model?

**Safety**: Prevent accidental modification

- Checkpoints are historical snapshots
- Modifying a checkpoint is a bug
- Immutability enforced by Pydantic

### Why config_hash Field?

**Validation**: Detect incompatible config changes

- Different chunking strategy → can't resume
- Different deduplication → inconsistent results
- Fail fast instead of producing bad data

### Why checkpoint_id Separate from Index?

**Flexibility**: Different checkpoint strategies

- Per-chunk: `chunk_0042`
- Time-based: `2025-01-23T14:30:00`
- Event-based: `after_validation_errors`
- ID is opaque to clients

## Testing Contract

All implementations of `CheckpointStore` MUST pass this test suite:

```python
# tests/contracts/test_checkpoint_store_contract.py
import pytest
from typing import Type

@pytest.mark.parametrize("store_class", [
    DiskCheckpointStore,
    InMemoryCheckpointStore,
])
def test_checkpoint_store_contract(store_class: Type[CheckpointStore], tmp_path: Path):
    """All CheckpointStore implementations must satisfy this contract."""
    store = create_store(store_class, tmp_path)

    # Create checkpoint
    checkpoint = Checkpoint(
        checkpoint_id="test_001",
        chunk_index=5,
        total_chunks=10,
        files_processed=50,
        entities_extracted=100,
        entities=[],
        metrics={},
        config_hash="abc123",
    )

    # Save and load
    store.save(checkpoint)
    loaded = store.load("test_001")
    assert loaded.checkpoint_id == "test_001"
    assert loaded.chunk_index == 5

    # Find latest
    latest = store.find_latest()
    assert latest is not None
    assert latest.checkpoint_id == "test_001"

    # List checkpoints
    checkpoints = store.list_checkpoints()
    assert len(checkpoints) == 1
    assert checkpoints[0].checkpoint_id == "test_001"

    # Exists
    assert store.exists("test_001")
    assert not store.exists("nonexistent")

    # Delete
    store.delete("test_001")
    assert not store.exists("test_001")

    # Clear all
    store.save(checkpoint)
    count = store.clear_all()
    assert count > 0
    assert len(store.list_checkpoints()) == 0
```

## Migration Path

**Phase 1 (Skateboard)**: Basic interface

- DiskCheckpointStore (production)
- InMemoryCheckpointStore (testing)
- Per-chunk checkpoints only

**Phase 2 (Scooter)**: Enhanced features

- Checkpoint compression (gzip)
- Automatic cleanup (keep last N)
- Checkpoint validation on load

**Phase 3 (Bicycle)**: Optimizations

- Incremental checkpoints (only store delta)
- Async I/O for large checkpoints
- Checkpoint streaming

**Phase 4 (Car)**: Cloud storage

- S3CheckpointStore
- GCSCheckpointStore
- Distributed locking for multi-worker

## References

- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
- [JSON Serialization](https://docs.python.org/3/library/json.html)
- [Checkpoint/Restart Pattern](https://en.wikipedia.org/wiki/Application_checkpointing)
