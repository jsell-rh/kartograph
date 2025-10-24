"""Configuration system using Pydantic Settings.

All configuration can be set via:
1. CLI arguments (highest priority)
2. Environment variables (EXTRACTOR_*)
3. .env file
4. Default values (lowest priority)
"""

import hashlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @model_validator(mode="after")
    def validate_auth_config(self) -> "AuthConfig":
        """Validate auth configuration based on auth_method."""
        if self.auth_method == "vertex_ai" and not self.vertex_project_id:
            raise ValueError("vertex_project_id required when auth_method=vertex_ai")
        if self.auth_method == "api_key" and not self.api_key:
            raise ValueError("api_key required when auth_method=api_key")
        return self


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
    detect_orphans: bool = Field(
        default=True,
        description="Detect orphaned entities (no relationships)",
    )
    detect_broken_refs: bool = Field(
        default=True,
        description="Detect broken references (URNs that don't exist)",
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
    verbose: bool = Field(
        default=False,
        description="Enable verbose mode with rich progress display and agent activity",
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
    def validate_data_dir_exists(cls, v: Path) -> Path:
        """Ensure data directory exists."""
        if not v.exists():
            raise ValueError(f"Data directory not found: {v}")
        if not v.is_dir():
            raise ValueError(f"Data directory is not a directory: {v}")
        return v

    def compute_hash(self) -> str:
        """
        Compute configuration hash for checkpoint validation.

        Includes fields that affect extraction results, including the data source.
        This ensures checkpoints are only compatible with the same data + config.
        """
        # Fields that affect results (exclude logging, checkpointing, etc.)
        relevant_config = {
            "data_dir": str(self.data_dir.absolute()),  # Include data source!
            "chunking": self.chunking.model_dump(),
            "deduplication": self.deduplication.model_dump(),
            "validation": self.validation.model_dump(),
            "llm": self.llm.model_dump(exclude={"max_retries", "timeout_seconds"}),
        }

        config_json = json.dumps(relevant_config, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]

    def compute_data_dir_hash(self) -> str:
        """
        Compute hash of data directory path for checkpoint isolation.

        Returns a short hash uniquely identifying this data directory.
        Used to create isolated checkpoint directories per dataset.
        """
        data_dir_str = str(self.data_dir.absolute())
        return hashlib.sha256(data_dir_str.encode()).hexdigest()[:16]
