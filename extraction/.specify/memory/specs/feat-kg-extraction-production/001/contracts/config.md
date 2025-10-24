# Contract: Configuration System

## Purpose

Defines the configuration structure for the extraction system to enable:

- **Environment-based configuration** (12-factor app principles)
- **Type-safe configuration** with validation
- **Hierarchical config** (CLI args > env vars > config file > defaults)
- **Testability** with minimal config for tests
- **Documentation** (auto-generated from Pydantic models)

## Interface Definition

### Configuration Models

```python
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional
from pathlib import Path

class AuthConfig(BaseModel):
    """
    Authentication configuration.

    Supports both Vertex AI (Google Cloud) and API key authentication.
    """
    auth_method: Literal["vertex_ai", "api_key"] = Field(
        default="vertex_ai",
        description="Authentication method to use",
    )

    # Vertex AI fields
    vertex_project_id: Optional[str] = Field(
        default=None,
        description="Google Cloud project ID for Vertex AI",
    )
    vertex_region: str = Field(
        default="us-central1",
        description="Google Cloud region for Vertex AI",
    )
    vertex_credentials_file: Optional[Path] = Field(
        default=None,
        description="Path to Google Cloud credentials JSON file",
    )

    # API key fields
    api_key: Optional[str] = Field(
        default=None,
        repr=False,  # Hide in logs/repr
        description="Anthropic API key (if using api_key auth)",
    )

    @field_validator("vertex_project_id")
    @classmethod
    def validate_vertex_project_id(cls, v, info):
        """Ensure vertex_project_id is set when using Vertex AI."""
        if info.data.get("auth_method") == "vertex_ai" and not v:
            raise ValueError("vertex_project_id required when auth_method=vertex_ai")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v, info):
        """Ensure api_key is set when using API key auth."""
        if info.data.get("auth_method") == "api_key" and not v:
            raise ValueError("api_key required when auth_method=api_key")
        return v


class ChunkingConfig(BaseModel):
    """Chunking strategy configuration."""
    strategy: Literal["hybrid", "directory", "size", "count"] = Field(
        default="hybrid",
        description="Chunking strategy to use",
    )
    target_size_mb: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Target chunk size in MB (for size-based strategies)",
    )
    max_files_per_chunk: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum files per chunk",
    )
    respect_directory_boundaries: bool = Field(
        default=True,
        description="Keep files in same directory together",
    )


class DeduplicationConfig(BaseModel):
    """Deduplication configuration."""
    strategy: Literal["urn", "agent", "hybrid"] = Field(
        default="urn",
        description="Deduplication strategy to use",
    )
    urn_merge_strategy: Literal["first", "last", "merge_predicates"] = Field(
        default="merge_predicates",
        description="How to merge duplicate URNs",
    )
    agent_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for agent-based dedup",
    )


class CheckpointConfig(BaseModel):
    """Checkpoint configuration."""
    enabled: bool = Field(
        default=True,
        description="Enable checkpointing",
    )
    strategy: Literal["per_chunk", "every_n", "time_based"] = Field(
        default="per_chunk",
        description="Checkpoint strategy",
    )
    every_n_chunks: int = Field(
        default=10,
        ge=1,
        description="Checkpoint every N chunks (for every_n strategy)",
    )
    time_interval_minutes: int = Field(
        default=30,
        ge=1,
        description="Checkpoint interval in minutes (for time_based strategy)",
    )
    checkpoint_dir: Path = Field(
        default=Path(".checkpoints"),
        description="Directory to store checkpoints",
    )


class ValidationConfig(BaseModel):
    """Validation configuration."""
    required_fields: list[str] = Field(
        default=["@id", "@type", "name"],
        description="Fields required on all entities",
    )
    allow_missing_name: bool = Field(
        default=False,
        description="Allow entities without 'name' field",
    )
    strict_urn_format: bool = Field(
        default=True,
        description="Enforce strict URN format (urn:type:identifier)",
    )
    fail_on_validation_errors: bool = Field(
        default=False,
        description="Fail extraction if validation errors occur",
    )


class LLMConfig(BaseModel):
    """LLM model configuration."""
    model: str = Field(
        default="claude-sonnet-4-5@20250929",
        description="LLM model to use",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=8192,
        description="Maximum tokens in LLM response",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM temperature (0=deterministic, 1=creative)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for LLM calls",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Timeout for LLM calls in seconds",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    json_logging: bool = Field(
        default=False,
        description="Use JSON-formatted logs",
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (None for stdout only)",
    )
    log_llm_prompts: bool = Field(
        default=False,
        description="Log full LLM prompts (for debugging)",
    )


class ExtractionConfig(BaseSettings):
    """
    Main extraction configuration.

    Configuration is loaded from (in priority order):
    1. CLI arguments (highest priority)
    2. Environment variables (EXTRACTOR_*)
    3. .env file
    4. Default values (lowest priority)
    """

    # Input/Output
    data_dir: Path = Field(
        description="Directory containing data to extract from",
    )
    context_dirs: list[Path] = Field(
        default_factory=list,
        description="Additional context directories (e.g., schemas)",
    )
    output_file: Path = Field(
        default=Path("knowledge_graph.jsonld"),
        description="Output JSON-LD file path",
    )

    # Sub-configurations
    auth: AuthConfig = Field(
        default_factory=AuthConfig,
        description="Authentication configuration",
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Chunking configuration",
    )
    deduplication: DeduplicationConfig = Field(
        default_factory=DeduplicationConfig,
        description="Deduplication configuration",
    )
    checkpoint: CheckpointConfig = Field(
        default_factory=CheckpointConfig,
        description="Checkpoint configuration",
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Validation configuration",
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    # Prompts
    prompt_template_dir: Path = Field(
        default=Path("kg_extractor/prompts/templates"),
        description="Directory containing prompt templates",
    )

    # Resumption
    resume: bool = Field(
        default=False,
        description="Resume from latest checkpoint",
    )

    # Pydantic settings config
    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",  # Fail on unknown config keys
    )

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir_exists(cls, v):
        """Ensure data directory exists."""
        if not v.exists():
            raise ValueError(f"Data directory not found: {v}")
        if not v.is_dir():
            raise ValueError(f"Data directory is not a directory: {v}")
        return v

    def compute_hash(self) -> str:
        """
        Compute configuration hash for checkpoint validation.

        Only includes fields that affect extraction results.
        """
        import hashlib
        import json

        # Fields that affect results (exclude logging, checkpointing, etc.)
        relevant_config = {
            "chunking": self.chunking.model_dump(),
            "deduplication": self.deduplication.model_dump(),
            "validation": self.validation.model_dump(),
            "llm": self.llm.model_dump(exclude={"max_retries", "timeout_seconds"}),
        }

        config_json = json.dumps(relevant_config, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]
```

## Usage Examples

### Default Configuration

```python
from kg_extractor.config import ExtractionConfig
from pathlib import Path

# Minimal config (uses defaults)
config = ExtractionConfig(data_dir=Path("/data"))

# All defaults applied
assert config.auth.auth_method == "vertex_ai"
assert config.chunking.strategy == "hybrid"
assert config.deduplication.strategy == "urn"
assert config.checkpoint.enabled is True
```

### Environment Variable Configuration

```bash
# .env file
EXTRACTOR_DATA_DIR=/data
EXTRACTOR_OUTPUT_FILE=/output/kg.jsonld

# Authentication
EXTRACTOR_AUTH__AUTH_METHOD=api_key
EXTRACTOR_AUTH__API_KEY=sk-ant-api03-...

# Chunking
EXTRACTOR_CHUNKING__STRATEGY=hybrid
EXTRACTOR_CHUNKING__TARGET_SIZE_MB=20

# Deduplication
EXTRACTOR_DEDUPLICATION__STRATEGY=urn
EXTRACTOR_DEDUPLICATION__URN_MERGE_STRATEGY=merge_predicates

# Checkpointing
EXTRACTOR_CHECKPOINT__ENABLED=true
EXTRACTOR_CHECKPOINT__STRATEGY=per_chunk
EXTRACTOR_CHECKPOINT__CHECKPOINT_DIR=.checkpoints

# LLM
EXTRACTOR_LLM__MODEL=claude-sonnet-4-5@20250929
EXTRACTOR_LLM__TEMPERATURE=0.0
EXTRACTOR_LLM__MAX_RETRIES=3

# Logging
EXTRACTOR_LOGGING__LOG_LEVEL=INFO
EXTRACTOR_LOGGING__JSON_LOGGING=false
```

```python
# Load config from environment + .env file
config = ExtractionConfig()
```

### CLI Argument Configuration

```bash
# Override environment with CLI args
python extractor.py \
  --data-dir /data \
  --output-file /output/kg.jsonld \
  --auth.auth-method api_key \
  --auth.api-key sk-ant-... \
  --chunking.strategy hybrid \
  --chunking.target-size-mb 20 \
  --resume
```

### Programmatic Configuration

```python
from kg_extractor.config import (
    ExtractionConfig,
    AuthConfig,
    ChunkingConfig,
)

config = ExtractionConfig(
    data_dir=Path("/data"),
    output_file=Path("/output/kg.jsonld"),
    auth=AuthConfig(
        auth_method="vertex_ai",
        vertex_project_id="my-project",
        vertex_region="us-central1",
    ),
    chunking=ChunkingConfig(
        strategy="hybrid",
        target_size_mb=20,
        max_files_per_chunk=100,
    ),
    resume=True,
)
```

### Testing Configuration

```python
# tests/conftest.py
import pytest
from kg_extractor.config import ExtractionConfig, AuthConfig
from pathlib import Path

@pytest.fixture
def test_config(tmp_path: Path) -> ExtractionConfig:
    """Minimal config for testing."""
    return ExtractionConfig(
        data_dir=tmp_path / "data",
        output_file=tmp_path / "output.jsonld",
        auth=AuthConfig(
            auth_method="api_key",
            api_key="test-key",  # pragma: allowlist secret - Mock key for testing
        ),
        checkpoint=CheckpointConfig(
            enabled=False,  # Disable checkpointing in tests
        ),
        logging=LoggingConfig(
            log_level="DEBUG",
            json_logging=False,
        ),
    )
```

## Configuration Hash

The configuration hash is used to detect incompatible changes when resuming from checkpoints:

```python
config1 = ExtractionConfig(
    data_dir=Path("/data"),
    chunking=ChunkingConfig(strategy="hybrid", target_size_mb=10),
)
hash1 = config1.compute_hash()  # "a1b2c3d4e5f6g7h8"

# Change extraction-relevant config
config2 = ExtractionConfig(
    data_dir=Path("/data"),
    chunking=ChunkingConfig(strategy="directory"),  # Changed
)
hash2 = config2.compute_hash()  # Different hash!

# Change non-relevant config (logging, etc.)
config3 = ExtractionConfig(
    data_dir=Path("/data"),
    chunking=ChunkingConfig(strategy="hybrid", target_size_mb=10),
    logging=LoggingConfig(log_level="DEBUG"),  # Changed logging
)
hash3 = config3.compute_hash()  # Same hash as hash1!

# Validation
assert hash1 != hash2  # Extraction config changed
assert hash1 == hash3  # Only logging changed, extraction unaffected
```

## Auto-Generated Documentation

Generate markdown documentation from config schema:

```python
# extractor config docs
def generate_config_docs(output_file: Path) -> None:
    """Generate configuration documentation."""
    schema = ExtractionConfig.model_json_schema()

    docs = "# Configuration Reference\n\n"

    for field_name, field_info in schema["properties"].items():
        docs += f"## {field_name}\n\n"
        docs += f"**Type**: `{field_info.get('type', 'object')}`\n\n"
        docs += f"**Description**: {field_info.get('description', 'N/A')}\n\n"

        if "default" in field_info:
            docs += f"**Default**: `{field_info['default']}`\n\n"

    output_file.write_text(docs)
```

## Design Rationale

### Why Pydantic Settings?

**Type Safety + Environment Integration**:

- Validate types at runtime
- Parse environment variables automatically
- Nested configuration via `__` delimiter
- IDE autocomplete support

### Why Nested Config Models?

**Organization + Modularity**:

- Logical grouping (`auth`, `chunking`, etc.)
- Each model can be tested independently
- Easier to document
- Clear boundaries

### Why compute_hash()?

**Checkpoint Validation**:

- Detect incompatible config changes
- Only hash extraction-relevant fields
- Prevent invalid resumption
- Clear error messages

### Why repr=False on api_key?

**Security**:

- Prevent API key leaks in logs
- Don't show in exceptions
- Still accessible programmatically
- Best practice for secrets

## Validation

Configuration is validated on construction:

```python
# Missing required field
try:
    config = ExtractionConfig()  # No data_dir
except ValidationError as e:
    print(e)  # "Field required: data_dir"

# Invalid type
try:
    config = ExtractionConfig(
        data_dir="/data",
        chunking=ChunkingConfig(target_size_mb="big"),  # Should be int
    )
except ValidationError as e:
    print(e)  # "Input should be a valid integer"

# Custom validation
try:
    config = ExtractionConfig(
        data_dir=Path("/nonexistent"),
    )
except ValidationError as e:
    print(e)  # "Data directory not found: /nonexistent"
```

## Migration Path

**Phase 1 (Skateboard)**: Core config

- ExtractionConfig with basic fields
- Environment variable support
- Validation

**Phase 2 (Scooter)**: Enhanced config

- Config file support (YAML/TOML)
- Config presets (dev, prod, test)
- Config validation CLI command

**Phase 3 (Bicycle)**: Advanced features

- Secret management integration (Vault, Secret Manager)
- Config schema versioning
- Config migration utilities

**Phase 4 (Car)**: Enterprise features

- Multi-environment config
- Remote config (etcd, Consul)
- Config audit logging

## References

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-Factor App Config](https://12factor.net/config)
- [Environment Variable Best Practices](https://12factor.net/config)
