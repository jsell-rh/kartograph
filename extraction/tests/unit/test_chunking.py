"""Unit tests for chunking strategies."""

from pathlib import Path

import pytest


def test_chunking_strategy_protocol():
    """Test ChunkingStrategy protocol defines required methods."""
    from kg_extractor.chunking.protocol import ChunkingStrategy

    # Protocol should define required methods
    assert hasattr(ChunkingStrategy, "create_chunks")


def test_chunk_model():
    """Test Chunk model structure."""
    from kg_extractor.chunking.models import Chunk

    chunk = Chunk(
        chunk_id="chunk-001",
        files=[Path("/test/file1.py"), Path("/test/file2.py")],
        total_size_bytes=5000,
    )

    assert chunk.chunk_id == "chunk-001"
    assert len(chunk.files) == 2
    assert chunk.total_size_bytes == 5000


def test_hybrid_chunker_basic(tmp_path: Path):
    """Test HybridChunker creates chunks."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create test files
    (tmp_path / "file1.py").write_text("print('hello')")
    (tmp_path / "file2.py").write_text("print('world')")

    config = ChunkingConfig(
        strategy="hybrid",
        target_size_mb=1,
        max_files_per_chunk=10,
    )

    chunker = HybridChunker(config=config)
    files = [tmp_path / "file1.py", tmp_path / "file2.py"]
    chunks = chunker.create_chunks(files)

    assert len(chunks) > 0
    assert all(len(chunk.files) > 0 for chunk in chunks)


def test_hybrid_chunker_respects_max_files(tmp_path: Path):
    """Test HybridChunker respects max_files_per_chunk."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create 20 small files
    files = []
    for i in range(20):
        file_path = tmp_path / f"file{i:03d}.py"
        file_path.write_text("x = 1")
        files.append(file_path)

    config = ChunkingConfig(
        strategy="hybrid",
        target_size_mb=100,  # Large size so it's not the limiting factor
        max_files_per_chunk=5,
    )

    chunker = HybridChunker(config=config)
    chunks = chunker.create_chunks(files)

    # Should create multiple chunks to respect max_files_per_chunk
    for chunk in chunks:
        assert len(chunk.files) <= 5


def test_hybrid_chunker_respects_target_size(tmp_path: Path):
    """Test HybridChunker respects target_size_mb."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create files with different sizes
    files = []
    # Create 5 files of 0.3 MB each (total 1.5 MB)
    for i in range(5):
        file_path = tmp_path / f"file{i:03d}.py"
        file_path.write_text("x" * (300 * 1024))  # ~300 KB
        files.append(file_path)

    config = ChunkingConfig(
        strategy="hybrid",
        target_size_mb=1,  # 1 MB target
        max_files_per_chunk=100,  # Large count so it's not the limiting factor
    )

    chunker = HybridChunker(config=config)
    chunks = chunker.create_chunks(files)

    # Should create multiple chunks to respect target size
    for chunk in chunks:
        # Allow some tolerance (10% over target)
        target_bytes = 1 * 1024 * 1024
        assert chunk.total_size_bytes <= target_bytes * 1.1


def test_hybrid_chunker_respects_directory_boundaries(tmp_path: Path):
    """Test HybridChunker keeps files in same directory together."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create directory structure
    dir1 = tmp_path / "service1"
    dir2 = tmp_path / "service2"
    dir1.mkdir()
    dir2.mkdir()

    # Create files in each directory
    files = []
    for i in range(3):
        f1 = dir1 / f"file{i}.py"
        f1.write_text("x = 1")
        files.append(f1)

        f2 = dir2 / f"file{i}.py"
        f2.write_text("x = 2")
        files.append(f2)

    config = ChunkingConfig(
        strategy="hybrid",
        target_size_mb=1,
        max_files_per_chunk=2,
        respect_directory_boundaries=True,
    )

    chunker = HybridChunker(config=config)
    chunks = chunker.create_chunks(files)

    # Verify files in same directory stay together
    for chunk in chunks:
        # All files in chunk should be from same parent directory
        if len(chunk.files) > 1:
            first_parent = chunk.files[0].parent
            assert all(f.parent == first_parent for f in chunk.files)


def test_hybrid_chunker_assigns_unique_ids(tmp_path: Path):
    """Test HybridChunker assigns unique IDs to chunks."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create multiple files
    files = []
    for i in range(10):
        file_path = tmp_path / f"file{i:03d}.py"
        file_path.write_text("x = 1")
        files.append(file_path)

    config = ChunkingConfig(
        strategy="hybrid",
        target_size_mb=1,
        max_files_per_chunk=3,
    )

    chunker = HybridChunker(config=config)
    chunks = chunker.create_chunks(files)

    # All chunk IDs should be unique
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_hybrid_chunker_empty_file_list():
    """Test HybridChunker handles empty file list."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    config = ChunkingConfig(strategy="hybrid")
    chunker = HybridChunker(config=config)

    chunks = chunker.create_chunks([])
    assert chunks == []


def test_hybrid_chunker_single_file(tmp_path: Path):
    """Test HybridChunker handles single file."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    file_path = tmp_path / "single.py"
    file_path.write_text("print('hello')")

    config = ChunkingConfig(strategy="hybrid")
    chunker = HybridChunker(config=config)

    chunks = chunker.create_chunks([file_path])

    assert len(chunks) == 1
    assert len(chunks[0].files) == 1
    assert chunks[0].files[0] == file_path


def test_hybrid_chunker_calculates_total_size(tmp_path: Path):
    """Test HybridChunker correctly calculates total_size_bytes."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    # Create files with known sizes
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.write_text("x" * 1000)  # 1000 bytes
    file2.write_text("y" * 2000)  # 2000 bytes

    config = ChunkingConfig(
        strategy="hybrid",
        max_files_per_chunk=10,
    )

    chunker = HybridChunker(config=config)
    chunks = chunker.create_chunks([file1, file2])

    assert len(chunks) == 1
    # Total should be 3000 bytes (approximately)
    assert chunks[0].total_size_bytes >= 3000
    assert chunks[0].total_size_bytes <= 3100  # Allow small overhead


def test_hybrid_chunker_skips_nonexistent_files():
    """Test HybridChunker skips files that don't exist."""
    from kg_extractor.chunking.hybrid_chunker import HybridChunker
    from kg_extractor.config import ChunkingConfig

    config = ChunkingConfig(strategy="hybrid")
    chunker = HybridChunker(config=config)

    # Include some nonexistent files
    files = [
        Path("/nonexistent/file1.py"),
        Path("/nonexistent/file2.py"),
    ]

    chunks = chunker.create_chunks(files)

    # Should skip nonexistent files, resulting in empty chunks list
    assert chunks == []


def test_chunk_serialization():
    """Test Chunk can serialize to/from dict."""
    from kg_extractor.chunking.models import Chunk

    chunk = Chunk(
        chunk_id="chunk-001",
        files=[Path("/test/file1.py"), Path("/test/file2.py")],
        total_size_bytes=5000,
    )

    # Serialize to dict
    data = chunk.model_dump()

    assert data["chunk_id"] == "chunk-001"
    assert len(data["files"]) == 2
    assert data["total_size_bytes"] == 5000

    # Deserialize from dict (need to convert paths back)
    data["files"] = [Path(p) for p in data["files"]]
    loaded = Chunk.model_validate(data)

    assert loaded.chunk_id == chunk.chunk_id
    assert loaded.files == chunk.files
    assert loaded.total_size_bytes == chunk.total_size_bytes
