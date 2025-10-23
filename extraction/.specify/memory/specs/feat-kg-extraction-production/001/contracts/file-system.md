# Contract: File System Interface

## Purpose

Defines the boundary around file I/O operations to enable:

- **Testing without disk access** (in-memory filesystem)
- **Parallel tests** (no shared filesystem state)
- **Fast test execution** (no I/O overhead)
- **Consistent error handling** across different storage backends
- **Future extensibility** (cloud storage, virtual filesystems)

## Interface Definition

### Core Protocol

```python
from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class FileInfo:
    """Metadata about a file."""
    path: Path
    size_bytes: int
    modified_time: float  # Unix timestamp
    is_directory: bool

class FileSystem(Protocol):
    """
    Abstract interface for file operations.

    This protocol defines the boundary around all file I/O, enabling:
    - Testing with in-memory implementations
    - Swapping storage backends (disk, S3, etc.)
    - Consistent error handling
    """

    def read_file(self, path: Path) -> str:
        """
        Read file contents as text.

        Args:
            path: Path to file

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: File doesn't exist
            PermissionError: No read permission
            IsADirectoryError: Path is directory, not file
        """
        ...

    def read_bytes(self, path: Path) -> bytes:
        """
        Read file contents as bytes.

        Args:
            path: Path to file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: File doesn't exist
            PermissionError: No read permission
            IsADirectoryError: Path is directory, not file
        """
        ...

    def write_file(self, path: Path, content: str) -> None:
        """
        Write text to file (overwrites if exists).

        Args:
            path: Path to file
            content: Text content to write

        Raises:
            PermissionError: No write permission
            IsADirectoryError: Path is directory, not file
        """
        ...

    def write_bytes(self, path: Path, content: bytes) -> None:
        """
        Write bytes to file (overwrites if exists).

        Args:
            path: Path to file
            content: Bytes content to write

        Raises:
            PermissionError: No write permission
            IsADirectoryError: Path is directory, not file
        """
        ...

    def list_files(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
    ) -> list[Path]:
        """
        List files matching pattern.

        Args:
            directory: Directory to search
            pattern: Glob pattern (e.g., "*.yaml", "**/*.json")
            recursive: Whether to search subdirectories

        Returns:
            List of matching file paths (sorted alphabetically)

        Raises:
            FileNotFoundError: Directory doesn't exist
            NotADirectoryError: Path is file, not directory
        """
        ...

    def file_info(self, path: Path) -> FileInfo:
        """
        Get file metadata.

        Args:
            path: Path to file or directory

        Returns:
            File metadata

        Raises:
            FileNotFoundError: Path doesn't exist
        """
        ...

    def exists(self, path: Path) -> bool:
        """
        Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        ...

    def mkdir(self, path: Path, parents: bool = True) -> None:
        """
        Create directory.

        Args:
            path: Directory path
            parents: Create parent directories if needed

        Raises:
            FileExistsError: Directory already exists
            PermissionError: No write permission
        """
        ...
```

## Implementations

### Production Implementation (Disk-Based)

```python
import os
from pathlib import Path
from typing import Iterator

class DiskFileSystem:
    """Production filesystem that uses actual disk I/O."""

    def read_file(self, path: Path) -> str:
        """Read file from disk."""
        return path.read_text(encoding="utf-8")

    def read_bytes(self, path: Path) -> bytes:
        """Read file bytes from disk."""
        return path.read_bytes()

    def write_file(self, path: Path, content: str) -> None:
        """Write file to disk."""
        path.write_text(content, encoding="utf-8")

    def write_bytes(self, path: Path, content: bytes) -> None:
        """Write bytes to disk."""
        path.write_bytes(content)

    def list_files(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
    ) -> list[Path]:
        """List files using glob."""
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        if recursive:
            matches = directory.rglob(pattern)
        else:
            matches = directory.glob(pattern)

        # Filter out directories, return only files
        files = [p for p in matches if p.is_file()]
        return sorted(files)

    def file_info(self, path: Path) -> FileInfo:
        """Get file info from disk."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        stat = path.stat()
        return FileInfo(
            path=path,
            size_bytes=stat.st_size,
            modified_time=stat.st_mtime,
            is_directory=path.is_dir(),
        )

    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        return path.exists()

    def mkdir(self, path: Path, parents: bool = True) -> None:
        """Create directory."""
        path.mkdir(parents=parents, exist_ok=False)
```

### Test Implementation (In-Memory)

```python
from datetime import datetime
from typing import Dict

class InMemoryFileSystem:
    """
    In-memory filesystem for testing.

    Advantages:
    - No disk I/O (fast tests)
    - No cleanup needed (fresh instance per test)
    - Parallel tests (no shared state)
    - Predictable (no filesystem race conditions)
    """

    def __init__(self):
        # Map from path to content (str for text, bytes for binary)
        self._files: Dict[Path, str | bytes] = {}
        # Map from path to modified time
        self._mtimes: Dict[Path, float] = {}
        # Set of directory paths
        self._dirs: set[Path] = {Path("/")}

    def read_file(self, path: Path) -> str:
        """Read file from memory."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        if path in self._dirs:
            raise IsADirectoryError(f"Is a directory: {path}")

        content = self._files[path]
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return content

    def read_bytes(self, path: Path) -> bytes:
        """Read bytes from memory."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        if path in self._dirs:
            raise IsADirectoryError(f"Is a directory: {path}")

        content = self._files[path]
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    def write_file(self, path: Path, content: str) -> None:
        """Write file to memory."""
        if path in self._dirs:
            raise IsADirectoryError(f"Is a directory: {path}")

        # Ensure parent directories exist
        self._ensure_parent_dirs(path)

        self._files[path] = content
        self._mtimes[path] = datetime.now().timestamp()

    def write_bytes(self, path: Path, content: bytes) -> None:
        """Write bytes to memory."""
        if path in self._dirs:
            raise IsADirectoryError(f"Is a directory: {path}")

        self._ensure_parent_dirs(path)

        self._files[path] = content
        self._mtimes[path] = datetime.now().timestamp()

    def list_files(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
    ) -> list[Path]:
        """List files matching pattern."""
        if directory not in self._dirs:
            if directory in self._files:
                raise NotADirectoryError(f"Not a directory: {directory}")
            raise FileNotFoundError(f"Directory not found: {directory}")

        import fnmatch

        matches = []
        for path in self._files.keys():
            # Check if file is in directory
            try:
                relative = path.relative_to(directory)
            except ValueError:
                continue  # Not in directory

            # Check recursion
            if not recursive and len(relative.parts) > 1:
                continue  # In subdirectory

            # Check pattern
            if fnmatch.fnmatch(str(relative), pattern):
                matches.append(path)

        return sorted(matches)

    def file_info(self, path: Path) -> FileInfo:
        """Get file metadata."""
        if path in self._dirs:
            return FileInfo(
                path=path,
                size_bytes=0,
                modified_time=0,
                is_directory=True,
            )

        if path in self._files:
            content = self._files[path]
            size = len(content.encode("utf-8") if isinstance(content, str) else content)
            return FileInfo(
                path=path,
                size_bytes=size,
                modified_time=self._mtimes[path],
                is_directory=False,
            )

        raise FileNotFoundError(f"Path not found: {path}")

    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        return path in self._files or path in self._dirs

    def mkdir(self, path: Path, parents: bool = True) -> None:
        """Create directory."""
        if path in self._files:
            raise FileExistsError(f"File exists: {path}")
        if path in self._dirs:
            raise FileExistsError(f"Directory exists: {path}")

        if parents:
            # Create all parent directories
            for parent in [path] + list(path.parents):
                if parent not in self._dirs:
                    self._dirs.add(parent)
        else:
            # Only create if parent exists
            if path.parent not in self._dirs:
                raise FileNotFoundError(f"Parent directory not found: {path.parent}")
            self._dirs.add(path)

    def _ensure_parent_dirs(self, path: Path) -> None:
        """Ensure all parent directories exist."""
        for parent in path.parents:
            if parent not in self._dirs:
                self._dirs.add(parent)

    # Test helpers
    def add_file(self, path: Path | str, content: str) -> None:
        """Helper to add file during test setup."""
        self.write_file(Path(path), content)

    def add_directory(self, path: Path | str) -> None:
        """Helper to add directory during test setup."""
        self.mkdir(Path(path), parents=True)

    def clear(self) -> None:
        """Clear all files and directories."""
        self._files.clear()
        self._mtimes.clear()
        self._dirs = {Path("/")}
```

## Usage Examples

### Production Usage

```python
from kg_extractor.filesystem import DiskFileSystem

fs = DiskFileSystem()

# Read configuration file
config = fs.read_file(Path("/etc/app/config.yaml"))

# List all YAML files
yaml_files = fs.list_files(
    directory=Path("/data"),
    pattern="*.yaml",
    recursive=True,
)

# Get file metadata
for file in yaml_files:
    info = fs.file_info(file)
    print(f"{file}: {info.size_bytes} bytes")
```

### Testing Usage

```python
# tests/test_extraction.py
def test_extraction_from_files():
    # Arrange: Create in-memory filesystem
    fs = InMemoryFileSystem()
    fs.add_directory("/data/services")
    fs.add_file("/data/services/app.yaml", """
        name: myapp
        owner: alice@example.com
    """)
    fs.add_file("/data/services/db.yaml", """
        name: postgres
        owner: bob@example.com
    """)

    # Act: Run extraction with in-memory FS
    extractor = ExtractionOrchestrator(
        filesystem=fs,
        llm_client=mock_llm,
        ...
    )
    result = await extractor.extract(data_dir=Path("/data"))

    # Assert: Verify without disk I/O
    assert result.entity_count >= 2
```

### Dependency Injection

```python
class ExtractionOrchestrator:
    """Orchestrator with injected filesystem."""

    def __init__(
        self,
        filesystem: FileSystem,  # Injected dependency
        llm_client: LLMClient,
        ...
    ):
        self.fs = filesystem
        self.llm = llm_client

    async def extract(self, data_dir: Path) -> ExtractionResult:
        # Discover files using filesystem interface
        files = self.fs.list_files(data_dir, pattern="*.yaml")

        # Read files using filesystem interface
        for file in files:
            content = self.fs.read_file(file)
            # Extract entities from content...

        # Write output using filesystem interface
        self.fs.write_file(
            Path("output.jsonld"),
            json.dumps(entities, indent=2),
        )
```

## Design Rationale

### Why Separate read_file and read_bytes?

**Type Safety**: Explicit methods prevent mixing text/binary

- `read_file()` returns `str` (UTF-8 decoded)
- `read_bytes()` returns `bytes` (raw)
- No silent encoding errors

### Why list_files Instead of glob?

**Abstraction**: `list_files` hides filesystem details

- Different backends may not support glob
- Can optimize for specific storage (e.g., S3 prefix listing)
- Consistent sorting across implementations

### Why FileInfo Dataclass?

**Efficiency**: Batch metadata access

- Single stat call for multiple attributes
- Immutable (cacheable)
- Type-safe

## Testing Contract

All implementations of `FileSystem` MUST pass this test suite:

```python
# tests/contracts/test_filesystem_contract.py
import pytest
from typing import Type

@pytest.mark.parametrize("fs_class", [
    DiskFileSystem,
    InMemoryFileSystem,
])
def test_filesystem_contract(fs_class: Type[FileSystem], tmp_path: Path):
    """All FileSystem implementations must satisfy this contract."""
    fs = create_filesystem(fs_class, tmp_path)

    # Write and read
    test_path = tmp_path / "test.txt"
    fs.write_file(test_path, "Hello, World!")
    content = fs.read_file(test_path)
    assert content == "Hello, World!"

    # List files
    files = fs.list_files(tmp_path, pattern="*.txt")
    assert test_path in files

    # File info
    info = fs.file_info(test_path)
    assert info.path == test_path
    assert info.size_bytes > 0
    assert not info.is_directory

    # Exists
    assert fs.exists(test_path)
    assert not fs.exists(tmp_path / "nonexistent.txt")

    # Directories
    new_dir = tmp_path / "subdir"
    fs.mkdir(new_dir)
    assert fs.exists(new_dir)
    dir_info = fs.file_info(new_dir)
    assert dir_info.is_directory
```

## Migration Path

**Phase 1 (Skateboard)**: Basic interface

- DiskFileSystem (production)
- InMemoryFileSystem (testing)
- Core methods only

**Phase 2 (Scooter)**: Enhanced features

- Atomic writes (write to temp, then move)
- Checksums for integrity
- Compression support

**Phase 3 (Bicycle)**: Optimizations

- Caching layer for repeated reads
- Async I/O for large files
- Memory mapping for huge files

**Phase 4 (Car)**: Cloud storage

- S3FileSystem implementation
- GCSFileSystem implementation
- Automatic failover between backends

## References

- [pathlib Documentation](https://docs.python.org/3/library/pathlib.html)
- [os Module](https://docs.python.org/3/library/os.html)
- [Protocol Pattern (PEP 544)](https://peps.python.org/pep-0544/)
