# Data Model: Production KG Extraction System

## Overview

This document defines all data structures, schemas, and models used in the production knowledge graph extraction system. All models use Pydantic for type safety and validation.

## Entity and Relationship Models

### JSON-LD Entity Schema

Entities are represented in JSON-LD format for compatibility with graph databases:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List
import re

class Entity(BaseModel):
    """
    Base entity model conforming to JSON-LD specification.

    All entities MUST have @id, @type, and name fields.
    """
    id: str = Field(alias="@id", description="Unique URN identifier")
    type: str = Field(alias="@type", description="Entity type name")
    name: str = Field(description="Human-readable name")

    # Additional predicates (dynamic)
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,  # Allow both 'id' and '@id'
        "extra": "allow",  # Allow additional fields
    }

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v):
        """Ensure @id follows URN format: urn:type:identifier"""
        if not re.match(r"^urn:[a-z][a-z0-9]*:[a-zA-Z0-9._-]+$", v):
            raise ValueError(f"Invalid URN format: {v}. Expected: urn:type:identifier")
        return v

    @field_validator("type")
    @classmethod
    def validate_type_name(cls, v):
        """Ensure @type is valid identifier: ^[A-Za-z][A-Za-z0-9]*$"""
        if not re.match(r"^[A-Z][A-Za-z0-9]*$", v):
            raise ValueError(
                f"Invalid type name: {v}. Must start with capital letter, "
                "contain only alphanumeric characters"
            )
        return v

    def to_jsonld(self) -> dict:
        """Convert to JSON-LD representation."""
        data = {
            "@id": self.id,
            "@type": self.type,
            "name": self.name,
        }
        data.update(self.extra)
        return data


class EntityReference(BaseModel):
    """Reference to another entity (for relationships)."""
    id: str = Field(alias="@id", description="URN of referenced entity")

    model_config = {"populate_by_name": True}

    def to_jsonld(self) -> dict:
        """Convert to JSON-LD reference."""
        return {"@id": self.id}
```

### Extraction Result Schema

```python
from datetime import datetime

class ExtractionMetadata(BaseModel):
    """Metadata about extraction process."""
    entity_count: int = Field(ge=0, description="Number of entities extracted")
    relationship_count: int = Field(ge=0, description="Number of relationships")
    types_discovered: List[str] = Field(
        default_factory=list,
        description="Unique entity types found",
    )
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When extraction occurred",
    )
    source_files: List[str] = Field(
        default_factory=list,
        description="Files extraction was performed on",
    )


class ExtractionResponse(BaseModel):
    """
    Response from extraction agent.

    This is the structured output expected from LLM.
    """
    entities: List[Dict[str, Any]] = Field(
        description="Extracted entities in JSON-LD format",
    )
    metadata: ExtractionMetadata = Field(
        description="Metadata about extraction",
    )

    @field_validator("entities")
    @classmethod
    def validate_entities(cls, v):
        """Ensure all entities have required fields."""
        for i, entity in enumerate(v):
            if "@id" not in entity:
                raise ValueError(f"Entity {i} missing @id")
            if "@type" not in entity:
                raise ValueError(f"Entity {i} missing @type")
            if "name" not in entity:
                raise ValueError(f"Entity {i} missing name")
        return v


class ExtractionResult(BaseModel):
    """Complete extraction result with validation."""
    entities: List[Entity]
    metadata: ExtractionMetadata
    validation_errors: List[str] = Field(default_factory=list)
    chunks_processed: int = Field(default=0, ge=0)

    @property
    def validation_pass_rate(self) -> float:
        """Calculate validation pass rate."""
        if self.metadata.entity_count == 0:
            return 1.0
        errors = len(self.validation_errors)
        return 1.0 - (errors / self.metadata.entity_count)

    @property
    def relationships_per_entity(self) -> float:
        """Calculate average relationships per entity."""
        if self.metadata.entity_count == 0:
            return 0.0
        return self.metadata.relationship_count / self.metadata.entity_count
```

## Validation Models

### Validation Error Schema

```python
from enum import Enum

class ValidationErrorSeverity(str, Enum):
    """Severity level of validation error."""
    ERROR = "error"  # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"  # Nice to fix

class ValidationError(BaseModel):
    """A validation error on an entity."""
    entity_id: str = Field(description="URN of entity with error")
    field: str | None = Field(default=None, description="Field with error")
    error_type: str = Field(description="Type of error (e.g., 'missing_field')")
    message: str = Field(description="Human-readable error message")
    severity: ValidationErrorSeverity = Field(default=ValidationErrorSeverity.ERROR)

    def __str__(self) -> str:
        if self.field:
            return f"[{self.severity.value.upper()}] {self.entity_id}.{self.field}: {self.message}"
        return f"[{self.severity.value.upper()}] {self.entity_id}: {self.message}"


class ValidationResult(BaseModel):
    """Result of entity validation."""
    entity_id: str
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(e.severity == ValidationErrorSeverity.ERROR for e in self.errors)

    @property
    def has_warnings(self) -> bool:
        return any(e.severity == ValidationErrorSeverity.WARNING for e in self.errors)
```

## Metrics Models

### Performance Metrics

```python
class PerformanceMetrics(BaseModel):
    """Performance metrics for extraction."""
    # Timing
    total_duration_seconds: float = Field(ge=0.0)
    extraction_duration_seconds: float = Field(ge=0.0)
    deduplication_duration_seconds: float = Field(ge=0.0)
    validation_duration_seconds: float = Field(ge=0.0)

    # Throughput
    files_per_second: float = Field(ge=0.0)
    entities_per_second: float = Field(ge=0.0)

    # Resource usage
    peak_memory_mb: float = Field(ge=0.0)
    total_llm_tokens: int = Field(ge=0)

    # Cost estimate
    estimated_cost_usd: float = Field(ge=0.0)


class QualityMetrics(BaseModel):
    """Quality metrics for extraction."""
    # Entity quality
    entities_with_all_required_fields: int = Field(ge=0)
    entities_missing_fields: int = Field(ge=0)
    validation_pass_rate: float = Field(ge=0.0, le=1.0)

    # Relationship quality
    orphaned_entities: int = Field(
        ge=0,
        description="Entities with no relationships",
    )
    relationships_per_entity: float = Field(ge=0.0)

    # Type quality
    unique_types_discovered: int = Field(ge=0)
    entities_per_type: Dict[str, int] = Field(default_factory=dict)


class CoverageMetrics(BaseModel):
    """Coverage metrics for extraction."""
    # File coverage
    total_files: int = Field(ge=0)
    files_processed: int = Field(ge=0)
    files_skipped: int = Field(ge=0)
    files_failed: int = Field(ge=0)

    # Content coverage
    total_size_bytes: int = Field(ge=0)
    processed_size_bytes: int = Field(ge=0)

    @property
    def file_success_rate(self) -> float:
        if self.total_files == 0:
            return 1.0
        return self.files_processed / self.total_files

    @property
    def coverage_percent(self) -> float:
        if self.total_size_bytes == 0:
            return 100.0
        return (self.processed_size_bytes / self.total_size_bytes) * 100


class ExtractionMetrics(BaseModel):
    """Complete metrics for extraction run."""
    performance: PerformanceMetrics
    quality: QualityMetrics
    coverage: CoverageMetrics

    # Deduplication metrics
    duplicates_found: int = Field(ge=0)
    duplicates_merged: int = Field(ge=0)

    # LLM metrics
    llm_calls: int = Field(ge=0)
    llm_errors: int = Field(ge=0)
    llm_retries: int = Field(ge=0)

    def to_summary_dict(self) -> dict:
        """Generate summary for logging."""
        return {
            "entities": self.quality.entities_with_all_required_fields,
            "types": self.quality.unique_types_discovered,
            "relationships_per_entity": self.quality.relationships_per_entity,
            "validation_pass_rate": self.quality.validation_pass_rate,
            "file_success_rate": self.coverage.file_success_rate,
            "duration_seconds": self.performance.total_duration_seconds,
            "cost_usd": self.performance.estimated_cost_usd,
        }
```

## Checkpoint Models

See `contracts/checkpoint-store.md` for detailed checkpoint models:

- `Checkpoint`: Full checkpoint state
- `CheckpointMetadata`: Lightweight checkpoint metadata

## Configuration Models

See `contracts/config.md` for detailed configuration models:

- `ExtractionConfig`: Main configuration
- `AuthConfig`: Authentication settings
- `ChunkingConfig`: Chunking settings
- `DeduplicationConfig`: Deduplication settings
- `CheckpointConfig`: Checkpoint settings
- `ValidationConfig`: Validation settings
- `LLMConfig`: LLM settings
- `LoggingConfig`: Logging settings

## Chunking Models

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class FileInfo:
    """Information about a file to be processed."""
    path: Path
    size_bytes: int
    modified_time: float

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass
class Chunk:
    """A chunk of files to process together."""
    index: int  # 0-indexed
    files: List[FileInfo]
    directory: Path | None = None  # Parent directory if applicable

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def __str__(self) -> str:
        return f"Chunk {self.index}: {self.file_count} files, {self.size_mb:.2f}MB"


class ChunkingResult(BaseModel):
    """Result of chunking operation."""
    chunks: List[Chunk]
    total_files: int
    total_size_bytes: int

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def avg_chunk_size_mb(self) -> float:
        if not self.chunks:
            return 0.0
        return (self.total_size_bytes / (1024 * 1024)) / len(self.chunks)
```

## LLM Request/Response Models

See `contracts/llm-client.md` for detailed LLM models:

- `LLMRequest`: LLM query request
- `LLMResponse`: LLM query response
- `FinishReason`: Enum for stop reasons

## Prompt Models

See `contracts/prompts.md` for detailed prompt models:

- `PromptTemplate`: Complete prompt template
- `PromptVariable`: Variable definition
- `PromptMetadata`: Prompt metadata

## Deduplication Models

See `contracts/deduplication.md` for detailed deduplication models:

- `DeduplicationResult`: Result of deduplication

## Output Models

### JSON-LD Graph Output

```python
class JSONLDContext(BaseModel):
    """JSON-LD context for namespace definitions."""
    context: Dict[str, str] = Field(
        default={
            "@vocab": "https://schema.org/",
            "urn": "https://example.com/urn/",
        },
        alias="@context",
    )

    model_config = {"populate_by_name": True}


class JSONLDGraph(BaseModel):
    """
    Complete JSON-LD graph for output.

    Compatible with Neo4j and Dgraph.
    """
    context: JSONLDContext = Field(default_factory=JSONLDContext)
    graph: List[Dict[str, Any]] = Field(alias="@graph", default_factory=list)

    model_config = {"populate_by_name": True}

    def add_entity(self, entity: Entity) -> None:
        """Add entity to graph."""
        self.graph.append(entity.to_jsonld())

    def add_entities(self, entities: List[Entity]) -> None:
        """Add multiple entities to graph."""
        for entity in entities:
            self.add_entity(entity)

    def to_jsonld_string(self, indent: int = 2) -> str:
        """Export as JSON-LD string."""
        import json
        data = {
            "@context": self.context.context,
            "@graph": self.graph,
        }
        return json.dumps(data, indent=indent, ensure_ascii=False)

    def save(self, path: Path) -> None:
        """Save graph to file."""
        path.write_text(self.to_jsonld_string())

    @classmethod
    def load(cls, path: Path) -> "JSONLDGraph":
        """Load graph from file."""
        import json
        data = json.loads(path.read_text())
        return cls(
            context=JSONLDContext(context=data.get("@context", {})),
            graph=data.get("@graph", []),
        )

    @property
    def entity_count(self) -> int:
        return len(self.graph)

    @property
    def types(self) -> set[str]:
        """Get all unique entity types in graph."""
        return {e.get("@type", "Unknown") for e in self.graph}
```

## Error Models

```python
class ExtractionError(Exception):
    """Base exception for extraction errors."""
    pass

class ChunkingError(ExtractionError):
    """Error during chunking."""
    pass

class LLMError(ExtractionError):
    """Error during LLM call."""
    pass

class ValidationFailedError(ExtractionError):
    """Validation failed and fail_on_validation_errors=True."""

    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} errors")

class ConfigurationError(ExtractionError):
    """Invalid configuration."""
    pass
```

## Logging Models

### Structured Log Entry

```python
class LogEntry(BaseModel):
    """Structured log entry for JSON logging."""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: str  # DEBUG, INFO, WARNING, ERROR
    message: str
    component: str  # e.g., "orchestrator", "llm_client"
    extra: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string for logging."""
        import json
        return json.dumps({
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "component": self.component,
            **self.extra,
        })
```

## Type Aliases

```python
from typing import TypeAlias

# URN identifier
URN: TypeAlias = str

# Entity type name
EntityType: TypeAlias = str

# JSON-LD dictionary
JSONLDEntity: TypeAlias = Dict[str, Any]

# File path
FilePath: TypeAlias = Path
```

## Constants

```python
# Validation constants
DEFAULT_REQUIRED_FIELDS = ["@id", "@type", "name"]
URN_PATTERN = r"^urn:[a-z][a-z0-9]*:[a-zA-Z0-9._-]+$"
TYPE_NAME_PATTERN = r"^[A-Z][A-Za-z0-9]*$"

# Chunking constants
DEFAULT_CHUNK_SIZE_MB = 10
DEFAULT_MAX_FILES_PER_CHUNK = 100

# LLM constants
DEFAULT_MODEL = "claude-sonnet-4-5@20250929"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.0

# Cost constants (per million tokens)
SONNET_INPUT_COST_PER_MTOK = 3.0
SONNET_OUTPUT_COST_PER_MTOK = 15.0
```

## Model Relationships

```
ExtractionConfig
├── AuthConfig
├── ChunkingConfig
├── DeduplicationConfig
├── CheckpointConfig
├── ValidationConfig
├── LLMConfig
└── LoggingConfig

ExtractionOrchestrator
├── uses: ExtractionConfig
├── uses: LLMClient
├── uses: FileSystem
├── uses: CheckpointStore
├── uses: ChunkingStrategy
├── uses: DeduplicationStrategy
├── produces: ExtractionResult
└── produces: ExtractionMetrics

ExtractionResult
├── contains: List[Entity]
├── contains: ExtractionMetadata
└── contains: List[ValidationError]

JSONLDGraph
├── contains: JSONLDContext
└── contains: List[JSONLDEntity]

Checkpoint
├── contains: List[JSONLDEntity]
├── contains: ExtractionMetrics
└── references: ExtractionConfig (via hash)
```

## Validation Rules

All models enforce these validation rules:

1. **Entity Validation**:
   - `@id` must match URN pattern
   - `@type` must match type name pattern
   - `name` must be non-empty string
   - All required fields present

2. **Metric Validation**:
   - All counts ≥ 0
   - All rates between 0.0 and 1.0
   - All durations ≥ 0.0

3. **Configuration Validation**:
   - Required fields present
   - Value ranges enforced (min/max)
   - Path existence checked
   - Auth method validates required subfields

4. **Checkpoint Validation**:
   - Version compatibility
   - Config hash match
   - Progress consistency (chunk_index ≤ total_chunks)

## Serialization

All Pydantic models support:

```python
# JSON serialization
model.model_dump_json(indent=2)  # To JSON string
model.model_dump()  # To dict

# Deserialization
Model.model_validate_json(json_string)  # From JSON string
Model.model_validate(dict_data)  # From dict

# Schema generation
Model.model_json_schema()  # JSON Schema
```

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JSON-LD Specification](https://json-ld.org/spec/latest/json-ld/)
- [Schema.org Vocabulary](https://schema.org/)
- [URN Syntax (RFC 8141)](https://www.rfc-editor.org/rfc/rfc8141)
