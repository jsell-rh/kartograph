"""Unit tests for file system interface."""

from pathlib import Path

import pytest


def test_file_system_protocol():
    """Test FileSystem protocol defines required methods."""
    from kg_extractor.loaders.protocol import FileSystem

    # Protocol should define required methods
    assert hasattr(FileSystem, "read_file")
    assert hasattr(FileSystem, "list_files")
    assert hasattr(FileSystem, "exists")


def test_disk_file_system_read_file(tmp_path: Path):
    """Test DiskFileSystem.read_file() reads actual files."""
    from kg_extractor.loaders.file_system import DiskFileSystem

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!")

    fs = DiskFileSystem()
    content = fs.read_file(test_file)

    assert content == "Hello, world!"


def test_disk_file_system_read_file_not_found(tmp_path: Path):
    """Test DiskFileSystem.read_file() raises on missing file."""
    from kg_extractor.loaders.file_system import DiskFileSystem

    fs = DiskFileSystem()

    with pytest.raises(FileNotFoundError):
        fs.read_file(tmp_path / "nonexistent.txt")


def test_disk_file_system_list_files(tmp_path: Path):
    """Test DiskFileSystem.list_files() lists directory contents."""
    from kg_extractor.loaders.file_system import DiskFileSystem

    # Create test files
    (tmp_path / "file1.py").write_text("# Python file")
    (tmp_path / "file2.md").write_text("# Markdown file")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.py").write_text("# Nested Python file")

    fs = DiskFileSystem()

    # List all files
    all_files = fs.list_files(tmp_path)
    assert len(all_files) == 3
    assert tmp_path / "file1.py" in all_files
    assert tmp_path / "file2.md" in all_files
    assert tmp_path / "subdir" / "file3.py" in all_files

    # List with pattern (Python files only)
    py_files = fs.list_files(tmp_path, pattern="**/*.py")
    assert len(py_files) == 2
    assert tmp_path / "file1.py" in py_files
    assert tmp_path / "subdir" / "file3.py" in py_files


def test_disk_file_system_exists(tmp_path: Path):
    """Test DiskFileSystem.exists() checks file existence."""
    from kg_extractor.loaders.file_system import DiskFileSystem

    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    fs = DiskFileSystem()

    assert fs.exists(test_file) is True
    assert fs.exists(tmp_path / "nonexistent.txt") is False


def test_in_memory_file_system_read_file():
    """Test InMemoryFileSystem.read_file() reads from memory."""
    from kg_extractor.loaders.file_system import InMemoryFileSystem

    fs = InMemoryFileSystem(
        files={
            Path("/test/file1.txt"): "Content 1",
            Path("/test/file2.txt"): "Content 2",
        }
    )

    assert fs.read_file(Path("/test/file1.txt")) == "Content 1"
    assert fs.read_file(Path("/test/file2.txt")) == "Content 2"


def test_in_memory_file_system_read_file_not_found():
    """Test InMemoryFileSystem.read_file() raises on missing file."""
    from kg_extractor.loaders.file_system import InMemoryFileSystem

    fs = InMemoryFileSystem(files={})

    with pytest.raises(FileNotFoundError):
        fs.read_file(Path("/nonexistent.txt"))


def test_in_memory_file_system_list_files():
    """Test InMemoryFileSystem.list_files() lists in-memory files."""
    from kg_extractor.loaders.file_system import InMemoryFileSystem

    fs = InMemoryFileSystem(
        files={
            Path("/test/file1.py"): "# Python",
            Path("/test/file2.md"): "# Markdown",
            Path("/test/subdir/file3.py"): "# Nested",
        }
    )

    # List all files
    all_files = fs.list_files(Path("/test"))
    assert len(all_files) == 3

    # List with pattern (Python files only)
    py_files = fs.list_files(Path("/test"), pattern="**/*.py")
    assert len(py_files) == 2
    assert Path("/test/file1.py") in py_files
    assert Path("/test/subdir/file3.py") in py_files


def test_in_memory_file_system_exists():
    """Test InMemoryFileSystem.exists() checks in-memory existence."""
    from kg_extractor.loaders.file_system import InMemoryFileSystem

    fs = InMemoryFileSystem(
        files={
            Path("/test/file.txt"): "content",
        }
    )

    assert fs.exists(Path("/test/file.txt")) is True
    assert fs.exists(Path("/test/nonexistent.txt")) is False


def test_in_memory_file_system_empty():
    """Test InMemoryFileSystem with empty file set."""
    from kg_extractor.loaders.file_system import InMemoryFileSystem

    fs = InMemoryFileSystem()

    assert fs.list_files(Path("/")) == []
    assert fs.exists(Path("/any/path")) is False
