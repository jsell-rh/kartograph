"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def sample_yaml_file(tmp_data_dir: Path) -> Path:
    """Create a sample YAML file for testing."""
    yaml_file = tmp_data_dir / "sample.yaml"
    yaml_file.write_text(
        """
name: test-service
owner: alice@example.com
dependencies:
  - auth-service
  - database
"""
    )
    return yaml_file


@pytest.fixture
def test_auth_config():
    """Create a test AuthConfig with api_key method."""
    from kg_extractor.config import AuthConfig

    return AuthConfig(
        auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
    )
