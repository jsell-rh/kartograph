"""Disk-based checkpoint store implementation."""

import json
from datetime import datetime
from pathlib import Path

from kg_extractor.checkpoint.models import Checkpoint


class DiskCheckpointStore:
    """
    Disk-based checkpoint storage.

    Implements: CheckpointStore protocol (via structural subtyping)

    Stores checkpoints as JSON files in a directory on disk.
    Each checkpoint is saved as {checkpoint_id}.json.

    Also maintains a metadata.json file for human readability.
    """

    def __init__(self, checkpoint_dir: Path, data_dir: Path | None = None):
        """
        Initialize disk checkpoint store.

        Args:
            checkpoint_dir: Directory to store checkpoint files
            data_dir: Optional data directory path for metadata tracking
        """
        self.checkpoint_dir = checkpoint_dir
        self.data_dir = data_dir

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint to disk.

        Creates the checkpoint directory if it doesn't exist.
        Also updates metadata file for human readability.

        Args:
            checkpoint: Checkpoint to save
        """
        # Create directory if it doesn't exist
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Save checkpoint as JSON
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        checkpoint_data = checkpoint.model_dump(mode="json")

        with checkpoint_file.open("w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        # Update metadata file
        self._update_metadata()

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Load a checkpoint from disk.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            Checkpoint if found, None otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        with checkpoint_file.open("r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)

        return Checkpoint.model_validate(checkpoint_data)

    def list_checkpoints(self) -> list[str]:
        """
        List all checkpoint IDs on disk.

        Returns:
            List of checkpoint IDs (sorted)
        """
        if not self.checkpoint_dir.exists():
            return []

        checkpoint_files = self.checkpoint_dir.glob("*.json")
        checkpoint_ids = [f.stem for f in checkpoint_files]

        return sorted(checkpoint_ids)

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """
        Delete a checkpoint from disk.

        Args:
            checkpoint_id: ID of checkpoint to delete
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()

    def _update_metadata(self) -> None:
        """
        Update metadata file for human readability.

        Stores information about when the checkpoint was created/updated
        and what data directory it corresponds to.
        """
        metadata_file = self.checkpoint_dir / "metadata.json"

        # Load existing metadata if present
        if metadata_file.exists():
            with metadata_file.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {
                "created_at": datetime.now().isoformat(),
            }

        # Update metadata
        metadata["last_updated"] = datetime.now().isoformat()
        if self.data_dir:
            metadata["data_dir"] = str(self.data_dir.absolute())

        # Save metadata
        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
