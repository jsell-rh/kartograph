"""Unit tests for configuration models."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError


def test_auth_config_defaults():
    """Test AuthConfig defaults (requires vertex_project_id for vertex_ai)."""
    from kg_extractor.config import AuthConfig

    # Default auth_method is vertex_ai, so we need to provide project_id
    config = AuthConfig(vertex_project_id="test-project")
    assert config.auth_method == "vertex_ai"
    assert config.vertex_region == "us-central1"
    assert config.vertex_project_id == "test-project"
    assert config.api_key is None


def test_auth_config_vertex_ai_validation():
    """Test AuthConfig validates vertex_project_id when using Vertex AI."""
    from kg_extractor.config import AuthConfig

    # Should fail without project_id
    with pytest.raises(ValidationError, match="vertex_project_id"):
        AuthConfig(auth_method="vertex_ai")


def test_auth_config_api_key_validation():
    """Test AuthConfig validates api_key when using API key auth."""
    from kg_extractor.config import AuthConfig

    # Should fail without api_key
    with pytest.raises(ValidationError, match="api_key"):
        AuthConfig(auth_method="api_key")


def test_auth_config_vertex_ai_valid():
    """Test AuthConfig with valid Vertex AI configuration."""
    from kg_extractor.config import AuthConfig

    config = AuthConfig(
        auth_method="vertex_ai",
        vertex_project_id="my-project",
        vertex_region="us-east1",
    )
    assert config.auth_method == "vertex_ai"
    assert config.vertex_project_id == "my-project"
    assert config.vertex_region == "us-east1"


def test_auth_config_api_key_valid():
    """Test AuthConfig with valid API key configuration."""
    from kg_extractor.config import AuthConfig

    config = AuthConfig(
        auth_method="api_key",
        api_key="sk-ant-test-key",  # pragma: allowlist secret
    )
    assert config.auth_method == "api_key"
    assert config.api_key == "sk-ant-test-key"  # pragma: allowlist secret


def test_chunking_config_defaults():
    """Test ChunkingConfig with default values."""
    from kg_extractor.config import ChunkingConfig

    config = ChunkingConfig()
    assert config.strategy == "hybrid"
    assert config.target_size_mb == 10
    assert config.max_files_per_chunk == 100
    assert config.respect_directory_boundaries is True


def test_chunking_config_validation():
    """Test ChunkingConfig validates constraints."""
    from kg_extractor.config import ChunkingConfig

    # Should fail with negative values
    with pytest.raises(ValidationError):
        ChunkingConfig(target_size_mb=-1)

    with pytest.raises(ValidationError):
        ChunkingConfig(max_files_per_chunk=0)


def test_deduplication_config_defaults():
    """Test DeduplicationConfig with default values."""
    from kg_extractor.config import DeduplicationConfig

    config = DeduplicationConfig()
    assert config.strategy == "urn"
    assert config.urn_merge_strategy == "merge_predicates"
    assert config.agent_similarity_threshold == 0.85


def test_checkpoint_config_defaults():
    """Test CheckpointConfig with default values."""
    from kg_extractor.config import CheckpointConfig

    config = CheckpointConfig()
    assert config.enabled is True
    assert config.strategy == "per_chunk"
    assert config.checkpoint_dir == Path(".checkpoints")


def test_validation_config_defaults():
    """Test ValidationConfig with default values."""
    from kg_extractor.config import ValidationConfig

    config = ValidationConfig()
    assert config.required_fields == ["@id", "@type", "name"]
    assert config.allow_missing_name is False
    assert config.strict_urn_format is True
    assert config.fail_on_validation_errors is False


def test_llm_config_defaults():
    """Test LLMConfig with default values."""
    from kg_extractor.config import LLMConfig

    config = LLMConfig()
    assert config.model == "claude-sonnet-4-5@20250929"
    assert config.max_tokens == 4096
    assert config.temperature == 0.0
    assert config.max_retries == 3
    assert config.timeout_seconds == 300


def test_logging_config_defaults():
    """Test LoggingConfig with default values."""
    from kg_extractor.config import LoggingConfig

    config = LoggingConfig()
    assert config.log_level == "INFO"
    assert config.json_logging is False
    assert config.log_file is None
    assert config.log_llm_prompts is False


def test_extraction_config_minimal(tmp_path: Path):
    """Test ExtractionConfig with minimal required fields."""
    from kg_extractor.config import AuthConfig, ExtractionConfig

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    config = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(
            auth_method="api_key", api_key="test-key"  # pragma: allowlist secret
        ),
    )

    assert config.data_dir == data_dir
    assert config.output_file == Path("knowledge_graph.jsonld")
    assert config.auth.auth_method == "api_key"


def test_extraction_config_validates_data_dir():
    """Test ExtractionConfig validates data directory exists."""
    from kg_extractor.config import AuthConfig, ExtractionConfig

    with pytest.raises(ValidationError, match="Data directory not found"):
        ExtractionConfig(
            data_dir=Path("/nonexistent"),
            auth=AuthConfig(
                auth_method="api_key", api_key="test"  # pragma: allowlist secret
            ),
        )


def test_extraction_config_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test ExtractionConfig loads from environment variables."""
    from kg_extractor.config import ExtractionConfig

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Set environment variables
    monkeypatch.setenv("EXTRACTOR_DATA_DIR", str(data_dir))
    monkeypatch.setenv("EXTRACTOR_AUTH__AUTH_METHOD", "api_key")
    monkeypatch.setenv(
        "EXTRACTOR_AUTH__API_KEY", "sk-test-123"
    )  # pragma: allowlist secret
    monkeypatch.setenv("EXTRACTOR_CHUNKING__STRATEGY", "directory")
    monkeypatch.setenv("EXTRACTOR_CHUNKING__TARGET_SIZE_MB", "20")

    config = ExtractionConfig()

    assert config.data_dir == data_dir
    assert config.auth.auth_method == "api_key"
    assert config.auth.api_key == "sk-test-123"  # pragma: allowlist secret
    assert config.chunking.strategy == "directory"
    assert config.chunking.target_size_mb == 20


def test_extraction_config_compute_hash(tmp_path: Path):
    """Test ExtractionConfig.compute_hash() for checkpoint validation."""
    from kg_extractor.config import AuthConfig, ExtractionConfig

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create two configs with different extraction-relevant settings
    config1 = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(
            auth_method="api_key", api_key="test1"  # pragma: allowlist secret
        ),
    )
    config2 = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(
            auth_method="api_key", api_key="test2"  # pragma: allowlist secret
        ),
    )

    # Hashes should be same (auth doesn't affect extraction)
    hash1 = config1.compute_hash()
    hash2 = config2.compute_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 16  # SHA256 truncated to 16 chars
    assert hash1 == hash2  # Auth changes don't affect hash


def test_extraction_config_hash_changes_with_chunking(tmp_path: Path):
    """Test config hash changes when chunking strategy changes."""
    from kg_extractor.config import AuthConfig, ChunkingConfig, ExtractionConfig

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    config1 = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(
            auth_method="api_key", api_key="test"  # pragma: allowlist secret
        ),
        chunking=ChunkingConfig(strategy="hybrid"),
    )
    config2 = ExtractionConfig(
        data_dir=data_dir,
        auth=AuthConfig(
            auth_method="api_key", api_key="test"  # pragma: allowlist secret
        ),
        chunking=ChunkingConfig(strategy="directory"),
    )

    # Different chunking should produce different hashes
    assert config1.compute_hash() != config2.compute_hash()
