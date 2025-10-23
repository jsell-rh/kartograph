"""In-memory checkpoint store implementation for testing."""

from kg_extractor.checkpoint.models import Checkpoint


class InMemoryCheckpointStore:
    """
    In-memory checkpoint storage for testing.

    Implements: CheckpointStore protocol (via structural subtyping)

    Stores checkpoints in a dictionary without touching the disk.
    Useful for unit testing without I/O overhead.
    """

    def __init__(self):
        """Initialize in-memory checkpoint store."""
        self.checkpoints: dict[str, Checkpoint] = {}

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint in memory.

        Args:
            checkpoint: Checkpoint to save
        """
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Load a checkpoint from memory.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            Checkpoint if found, None otherwise
        """
        return self.checkpoints.get(checkpoint_id)

    def list_checkpoints(self) -> list[str]:
        """
        List all checkpoint IDs in memory.

        Returns:
            List of checkpoint IDs (sorted)
        """
        return sorted(self.checkpoints.keys())

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """
        Delete a checkpoint from memory.

        Args:
            checkpoint_id: ID of checkpoint to delete
        """
        self.checkpoints.pop(checkpoint_id, None)
