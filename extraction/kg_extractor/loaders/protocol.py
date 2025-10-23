"""File system protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy testing without disk I/O (using InMemoryFileSystem)
- Swappable implementations (local disk, cloud storage, etc.)
"""

from pathlib import Path
from typing import Protocol


class FileSystem(Protocol):
    """
    Protocol for file system implementations.

    Implementations must support reading files, listing directories,
    and checking file existence.
    """

    def read_file(self, path: Path) -> str:
        """
        Read a file's contents as a string.

        Args:
            path: Path to the file to read

        Returns:
            File contents as a string

        Raises:
            FileNotFoundError: If the file does not exist
        """
        ...

    def list_files(self, directory: Path, pattern: str = "**/*") -> list[Path]:
        """
        List all files in a directory matching a pattern.

        Args:
            directory: Directory to list files from
            pattern: Glob pattern to filter files (default: all files)

        Returns:
            List of file paths matching the pattern
        """
        ...

    def exists(self, path: Path) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Path to check

        Returns:
            True if the path exists, False otherwise
        """
        ...
