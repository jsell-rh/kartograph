"""Checkpoint store protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy testing without disk I/O (using InMemoryCheckpointStore)
- Swappable implementations (local disk, cloud storage, database, etc.)
"""

from typing import Protocol

from kg_extractor.checkpoint.models import Checkpoint


class CheckpointStore(Protocol):
    """
    Protocol for checkpoint storage implementations.

    Implementations must support saving, loading, listing, and deleting checkpoints.
    """

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint.

        Args:
            checkpoint: Checkpoint to save
        """
        ...

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Load a checkpoint by ID.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            Checkpoint if found, None otherwise
        """
        ...

    def list_checkpoints(self) -> list[str]:
        """
        List all checkpoint IDs.

        Returns:
            List of checkpoint IDs (sorted by checkpoint_id)
        """
        ...

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to delete
        """
        ...
