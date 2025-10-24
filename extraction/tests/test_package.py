"""Basic smoke tests for package structure."""

import kg_extractor


def test_package_version():
    """Test package has a version."""
    assert hasattr(kg_extractor, "__version__")
    assert isinstance(kg_extractor.__version__, str)
    assert kg_extractor.__version__ == "0.1.0"


def test_package_imports():
    """Test package can be imported."""
    import kg_extractor.agents
    import kg_extractor.deduplication
    import kg_extractor.loaders
    import kg_extractor.prompts

    # All subpackages should be importable
    assert kg_extractor.agents is not None
    assert kg_extractor.deduplication is not None
    assert kg_extractor.loaders is not None
    assert kg_extractor.prompts is not None
