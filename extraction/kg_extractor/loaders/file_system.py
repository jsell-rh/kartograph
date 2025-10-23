"""File system implementations.

Provides both disk-based and in-memory implementations of the FileSystem protocol.
"""

from pathlib import Path


class DiskFileSystem:
    """
    Disk-based file system implementation.

    Reads files from the actual file system.
    """

    def read_file(self, path: Path) -> str:
        """
        Read a file's contents from disk.

        Args:
            path: Path to the file to read

        Returns:
            File contents as a string

        Raises:
            FileNotFoundError: If the file does not exist
        """
        return path.read_text(encoding="utf-8")

    def list_files(self, directory: Path, pattern: str = "**/*") -> list[Path]:
        """
        List all files in a directory matching a pattern.

        Args:
            directory: Directory to list files from
            pattern: Glob pattern to filter files (default: all files)

        Returns:
            List of file paths matching the pattern
        """
        paths = list(directory.glob(pattern))
        # Filter to only files (not directories)
        return [p for p in paths if p.is_file()]

    def exists(self, path: Path) -> bool:
        """
        Check if a file or directory exists on disk.

        Args:
            path: Path to check

        Returns:
            True if the path exists, False otherwise
        """
        return path.exists()


class InMemoryFileSystem:
    """
    In-memory file system implementation for testing.

    Stores files in a dictionary without touching the disk.
    """

    def __init__(self, files: dict[Path, str] | None = None):
        """
        Initialize in-memory file system.

        Args:
            files: Optional dictionary mapping paths to file contents
        """
        self.files = files or {}

    def read_file(self, path: Path) -> str:
        """
        Read a file's contents from memory.

        Args:
            path: Path to the file to read

        Returns:
            File contents as a string

        Raises:
            FileNotFoundError: If the file does not exist in memory
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def list_files(self, directory: Path, pattern: str = "**/*") -> list[Path]:
        """
        List all files in memory matching a pattern.

        Args:
            directory: Directory to list files from
            pattern: Glob pattern to filter files (default: all files)

        Returns:
            List of file paths matching the pattern
        """
        # Get all files under the directory
        matching_files = []
        for file_path in self.files.keys():
            # Check if file is under the directory
            try:
                relative_path = file_path.relative_to(directory)
            except ValueError:
                # Not under this directory
                continue

            # Check if file matches the pattern using PurePath.match()
            # For patterns like **/*.py, we need to check the full relative path
            if pattern == "**/*" or file_path.match(pattern):
                matching_files.append(file_path)

        return matching_files

    def exists(self, path: Path) -> bool:
        """
        Check if a file exists in memory.

        Args:
            path: Path to check

        Returns:
            True if the path exists in memory, False otherwise
        """
        return path in self.files
