"""Tests for chunk splitting (413 error handling)."""

import tempfile
from pathlib import Path

import pytest

from kg_extractor.chunking.models import Chunk


def test_chunk_split_even_files():
    """Test splitting a chunk with an even number of files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(4):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}" * 100)  # Make files have some size
            files.append(file_path)

        # Create chunk
        total_size = sum(f.stat().st_size for f in files)
        chunk = Chunk(chunk_id="test-chunk", files=files, total_size_bytes=total_size)

        # Split
        first_half, second_half = chunk.split()

        # Verify IDs
        assert first_half.chunk_id == "test-chunk-a"
        assert second_half.chunk_id == "test-chunk-b"

        # Verify file counts
        assert len(first_half.files) == 2
        assert len(second_half.files) == 2

        # Verify files are split correctly
        assert first_half.files == files[:2]
        assert second_half.files == files[2:]

        # Verify sizes
        first_size = sum(f.stat().st_size for f in first_half.files)
        second_size = sum(f.stat().st_size for f in second_half.files)
        assert first_half.total_size_bytes == first_size
        assert second_half.total_size_bytes == second_size
        assert first_half.total_size_bytes + second_half.total_size_bytes == total_size


def test_chunk_split_odd_files():
    """Test splitting a chunk with an odd number of files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(5):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}" * 100)
            files.append(file_path)

        total_size = sum(f.stat().st_size for f in files)
        chunk = Chunk(chunk_id="test-chunk", files=files, total_size_bytes=total_size)

        # Split
        first_half, second_half = chunk.split()

        # With 5 files, should split as 2 + 3
        assert len(first_half.files) == 2
        assert len(second_half.files) == 3

        # Verify all files are preserved
        all_split_files = first_half.files + second_half.files
        assert set(all_split_files) == set(files)


def test_chunk_split_two_files():
    """Test splitting a chunk with exactly two files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(2):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}" * 100)
            files.append(file_path)

        total_size = sum(f.stat().st_size for f in files)
        chunk = Chunk(chunk_id="test-chunk", files=files, total_size_bytes=total_size)

        # Split
        first_half, second_half = chunk.split()

        # Should split as 1 + 1
        assert len(first_half.files) == 1
        assert len(second_half.files) == 1

        assert first_half.files[0] == files[0]
        assert second_half.files[0] == files[1]


def test_chunk_split_single_file_raises():
    """Test that splitting a chunk with a single file raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create single file
        file_path = Path(tmpdir) / "file.txt"
        file_path.write_text("content" * 100)

        chunk = Chunk(
            chunk_id="test-chunk",
            files=[file_path],
            total_size_bytes=file_path.stat().st_size,
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="Cannot split chunk.*only 1 file"):
            chunk.split()


def test_chunk_split_preserves_all_files():
    """Test that splitting preserves all files without duplication."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(10):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)

        total_size = sum(f.stat().st_size for f in files)
        chunk = Chunk(chunk_id="test-chunk", files=files, total_size_bytes=total_size)

        # Split
        first_half, second_half = chunk.split()

        # Verify no duplication
        first_set = set(first_half.files)
        second_set = set(second_half.files)
        assert len(first_set) == len(first_half.files)  # No dups in first
        assert len(second_set) == len(second_half.files)  # No dups in second
        assert len(first_set & second_set) == 0  # No overlap

        # Verify all files present
        assert first_set | second_set == set(files)


def test_chunk_split_recursive():
    """Test recursive chunk splitting (splitting a chunk multiple times)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 8 files
        files = []
        for i in range(8):
            file_path = Path(tmpdir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)

        total_size = sum(f.stat().st_size for f in files)
        chunk = Chunk(chunk_id="chunk-000", files=files, total_size_bytes=total_size)

        # First split: 8 -> 4 + 4
        first, second = chunk.split()
        assert len(first.files) == 4
        assert len(second.files) == 4
        assert first.chunk_id == "chunk-000-a"
        assert second.chunk_id == "chunk-000-b"

        # Second split on first half: 4 -> 2 + 2
        first_a, first_b = first.split()
        assert len(first_a.files) == 2
        assert len(first_b.files) == 2
        assert first_a.chunk_id == "chunk-000-a-a"
        assert first_b.chunk_id == "chunk-000-a-b"

        # Third split on second half: 4 -> 2 + 2
        second_a, second_b = second.split()
        assert len(second_a.files) == 2
        assert len(second_b.files) == 2
        assert second_a.chunk_id == "chunk-000-b-a"
        assert second_b.chunk_id == "chunk-000-b-b"

        # Verify all 8 files preserved across all splits
        all_final_files = (
            first_a.files + first_b.files + second_a.files + second_b.files
        )
        assert set(all_final_files) == set(files)
