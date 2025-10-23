"""File system and data loading interfaces."""

from kg_extractor.loaders.file_system import DiskFileSystem, InMemoryFileSystem
from kg_extractor.loaders.protocol import FileSystem

__all__ = ["FileSystem", "DiskFileSystem", "InMemoryFileSystem"]
