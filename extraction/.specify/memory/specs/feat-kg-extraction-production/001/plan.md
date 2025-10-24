# Technical Implementation Plan: Production KG Extraction System

## Overview

This document details the technical architecture and implementation approach for the production knowledge graph extraction system. It translates the requirements from `spec.md` into concrete technical decisions and implementation phases.

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                       │
│                      (extractor.py)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Orchestrator                              │
│  - Coordinates extraction workflow                           │
│  - Manages progress and checkpointing                        │
│  - Drives chunking and deduplication                         │
└──┬────────┬────────┬────────┬────────┬──────────────────────┘
   │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Config│ │Chunk-│ │Agent │ │Dedupe│ │Valid-│
│      │ │ing   │ │SDK   │ │      │ │ation │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

### Module Structure

```
kg_extractor/
├── __init__.py
├── config.py                 # Pydantic Settings (all configuration)
├── orchestrator.py           # Main workflow coordinator
├── chunking.py               # Chunking strategies
├── progress.py               # Checkpointing and resume
├── validation.py             # Entity validation rules
├── metrics.py                # Metrics tracking and export
│
├── agents/
│   ├── __init__.py
│   ├── base.py              # Auth handling (Vertex AI + API key)
│   ├── extraction.py        # Entity extraction agent
│   └── deduplication.py     # Semantic deduplication agent
│
├── deduplication/
│   ├── __init__.py
│   ├── base.py              # Strategy interface (ABC)
│   ├── urn_based.py         # URN-based deduplication
│   └── agent_based.py       # Agent-powered semantic matching
│
├── loaders/
│   ├── __init__.py
│   ├── dgraph.py            # Dgraph JSON-LD output
│   └── neo4j.py             # Neo4j JSON-LD output
│
└── prompts/
    ├── __init__.py
    ├── loader.py            # Jinja2 template loader
    ├── registry.py          # Prompt discovery and validation
    ├── cli.py               # Prompt management CLI commands
    └── templates/
        ├── extraction.yaml
        ├── deduplication.yaml
        └── validation.yaml
```

## Technology Stack

### Core Technologies

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Language | Python | 3.13+ | Modern type system, performance improvements |
| Package Manager | uv | Latest | Fast, deterministic dependency resolution |
| LLM Integration | Claude Agent SDK | Latest | Managed context, tool ecosystem, structured outputs |
| Configuration | Pydantic Settings | 2.x | Type-safe config with env var support |
| Templating | Jinja2 | 3.x | Industry-standard template engine |
| Authentication | google-auth | Latest | Vertex AI authentication |
| HTTP Client | httpx | Latest | Async support for API key auth |

### Development Tools

- **Type Checking**: mypy (strict mode)
- **Linting**: ruff (replaces flake8, black, isort)
- **Testing**: pytest with pytest-asyncio
- **Documentation**: Sphinx with autodoc

## Component Details

### 1. Configuration System

**File**: `kg_extractor/config.py`

**Design**:

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional
from pathlib import Path

class AuthConfig(BaseModel):
    """Authentication configuration."""
    auth_method: Literal["vertex_ai", "api_key"] = "vertex_ai"
    api_key: Optional[str] = Field(default=None, repr=False)  # Hide in logs
    vertex_project_id: Optional[str] = None
    vertex_region: str = "us-central1"
    vertex_credentials_file: Optional[Path] = None

class ChunkingConfig(BaseModel):
    """Chunking strategy configuration."""
    strategy: Literal["hybrid", "directory", "size", "count"] = "hybrid"
    target_size_mb: int = 10
    max_files_per_chunk: int = 100
    respect_directory_boundaries: bool = True

class DeduplicationConfig(BaseModel):
    """Deduplication configuration."""
    strategy: Literal["urn", "agent", "hybrid"] = "urn"
    urn_merge_strategy: Literal["first", "last", "merge_predicates"] = "merge_predicates"
    agent_similarity_threshold: float = 0.85

class CheckpointConfig(BaseModel):
    """Checkpoint configuration."""
    enabled: bool = True
    strategy: Literal["per_chunk", "every_n", "time_based"] = "per_chunk"
    every_n_chunks: int = 10
    time_interval_minutes: int = 30
    checkpoint_dir: Path = Path(".checkpoints")

class ExtractionConfig(BaseSettings):
    """Main extraction configuration."""

    # Input/Output
    data_dir: Path
    context_dirs: list[Path] = Field(default_factory=list)
    output_file: Path = Field(default=Path("knowledge_graph.jsonld"))

    # Sub-configurations
    auth: AuthConfig = Field(default_factory=AuthConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)

    # Prompts
    prompt_template_dir: Path = Field(default=Path("kg_extractor/prompts/templates"))

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_logging: bool = False
    log_file: Optional[Path] = None

    # Performance
    max_retries: int = 3
    timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

**Usage Examples**:

```bash
# Via environment variables
export EXTRACTOR_DATA_DIR=/path/to/data
export EXTRACTOR_AUTH__AUTH_METHOD=vertex_ai
export EXTRACTOR_AUTH__VERTEX_PROJECT_ID=my-project
export EXTRACTOR_CHUNKING__STRATEGY=hybrid

# Via .env file
EXTRACTOR_DATA_DIR=/path/to/data
EXTRACTOR_AUTH__AUTH_METHOD=api_key
EXTRACTOR_AUTH__API_KEY=sk-ant-...

# Via CLI flags (override env vars)
python extractor.py --data-dir /path/to/data --auth.auth-method api_key
```

### 2. Agent SDK Integration

**File**: `kg_extractor/agents/base.py`

**Design**:

```python
from abc import ABC, abstractmethod
from anthropic import Anthropic
from anthropic.vertex import AnthropicVertex
from kg_extractor.config import AuthConfig

class AgentBase(ABC):
    """Base class for Agent SDK integration with auth handling."""

    def __init__(self, auth_config: AuthConfig):
        self.auth_config = auth_config
        self.client = self._create_client()

    def _create_client(self) -> Anthropic | AnthropicVertex:
        """Create appropriate client based on auth method."""
        if self.auth_config.auth_method == "vertex_ai":
            return AnthropicVertex(
                project_id=self.auth_config.vertex_project_id,
                region=self.auth_config.vertex_region,
                credentials_file=self.auth_config.vertex_credentials_file,
            )
        elif self.auth_config.auth_method == "api_key":
            return Anthropic(api_key=self.auth_config.api_key)
        else:
            raise ValueError(f"Unknown auth method: {self.auth_config.auth_method}")

    @abstractmethod
    async def execute(self, **kwargs):
        """Execute agent task."""
        pass
```

**File**: `kg_extractor/agents/extraction.py`

**Design**:

```python
from pathlib import Path
from kg_extractor.agents.base import AgentBase
from kg_extractor.prompts.loader import PromptLoader
from anthropic.agent import Agent, Tool

class ExtractionAgent(AgentBase):
    """Agent for extracting entities and relationships."""

    def __init__(self, auth_config, prompt_loader: PromptLoader):
        super().__init__(auth_config)
        self.prompt_loader = prompt_loader

    async def extract(
        self,
        file_paths: list[Path],
        schema_dir: Path | None = None,
        required_fields: list[str] = ["@id", "@type", "name"],
    ) -> dict:
        """
        Extract entities from files using Agent SDK.

        Returns:
            {
                "entities": [...],
                "metrics": {
                    "entity_count": int,
                    "relationship_count": int,
                    "validation_errors": [...]
                }
            }
        """
        # Load and render prompt
        template = self.prompt_loader.load("extraction")
        system_prompt, user_prompt = template.render(
            file_paths=file_paths,
            schema_dir=schema_dir,
            required_fields=required_fields,
        )

        # Create agent with tools
        agent = Agent(
            client=self.client,
            model="claude-sonnet-4-5@20250929",
            system=system_prompt,
            tools=[
                Tool(name="read_file", ...),
                Tool(name="read_schema", ...),
            ],
        )

        # Execute extraction
        response = await agent.run(user_prompt)

        # Parse and validate response
        return self._parse_extraction_result(response)
```

### 3. Prompt Management System

**File**: `kg_extractor/prompts/templates/extraction.yaml`

**Format**:

```yaml
metadata:
  name: entity_extraction
  version: "1.0.0"
  description: "Main entity extraction prompt for KG extraction"
  author: "KG Extraction Team"
  created: "2025-01-23"

variables:
  file_paths:
    type: list[Path]
    required: true
    description: "List of files to extract entities from"
    example: ["/data/service.yaml", "/data/team.yaml"]

  schema_dir:
    type: Path
    required: false
    description: "Directory containing schema files for reference"
    example: "/schemas"

  required_fields:
    type: list[str]
    required: true
    default: ["@id", "@type", "name"]
    description: "Fields that MUST be present on all entities"

system_prompt: |
  # Knowledge Graph Entity Extraction

  You are an expert at extracting structured entity and relationship information from diverse data sources.

  ## Input Files

  {% for path in file_paths %}
  - `{{ path }}`
  {% endfor %}

  ## Task

  Extract ALL entities and relationships from the provided files. Follow these rules:

  ### Entity Extraction Rules

  1. **Discover Entity Types**: Do NOT use hardcoded types. Infer types from the data structure.
     - Example: `serviceOwners` → extract `User` entities
     - Example: `dependencies` → extract `Service` entities

  2. **Maximum Fidelity**: Extract ALL fields present in source data.
     - Include metadata, timestamps, descriptions, etc.
     - Use scalar predicates for simple properties

  3. **Required Fields**: ALL entities MUST have:
     {% for field in required_fields %}
     - `{{ field }}`
     {% endfor %}

  4. **Valid Type Names**: Type names must match `^[A-Za-z][A-Za-z0-9]*$`
     - ✅ Valid: `Service`, `User`, `CodeRepository`
     - ❌ Invalid: `service`, `Users[0]`, `Service-Type`

  5. **URN Format**: All `@id` values must be valid URNs: `urn:type:identifier`
     - Example: `urn:service:myapp`
     - Example: `urn:user:alice@example.com`

  6. **Pattern-Based Entities**: Discover entities from patterns:
     - Email addresses → `EmailAddress` or `User`
     - URLs → `CodeRepository` or `Website`
     - Slack channels → `SlackChannel`

  ### Relationship Extraction Rules

  1. **Use Predicates**: Express relationships as predicates on entities, NOT as separate Relationship entities.
     ```json
     // ✅ Correct
     {
       "@id": "urn:service:myapp",
       "@type": "Service",
       "dependsOn": {"@id": "urn:service:auth"}
     }

     // ❌ Incorrect
     {
       "@type": "Relationship",
       "from": "urn:service:myapp",
       "to": "urn:service:auth"
     }
     ```

  2. **Resolve References**: Convert `$ref` pointers to target URNs

  3. **Bidirectional**: Create inverse predicates where appropriate
     - `Service.hasOwner` ↔ `User.owns`

  ### Validation

  After extraction, validate:
  - All entities have required fields
  - Type names are valid identifiers
  - URNs follow correct format
  - No orphaned entities (all have at least one relationship)

  {% if schema_dir %}
  ## Schema Reference

  Schema files are available in `{{ schema_dir }}` for reference. Use them to understand:
  - Expected entity types
  - Common predicates
  - Field naming conventions

  However, do NOT limit extraction to schema-defined types. Discover new types as needed.
  {% endif %}

user_prompt: |
  Please extract all entities and relationships from the provided files.

  Return your result as a JSON object with this structure:

  ```json
  {
    "entities": [
      {
        "@id": "urn:type:identifier",
        "@type": "TypeName",
        "name": "Display Name",
        "predicate1": "scalar value",
        "predicate2": {"@id": "urn:other:entity"}
      }
    ],
    "metadata": {
      "entity_count": 123,
      "relationship_count": 456,
      "types_discovered": ["Service", "User", "Team"]
    }
  }
  ```

```

**File**: `kg_extractor/prompts/loader.py`

**Design**:
```python
from pathlib import Path
from typing import Any
import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, Field

class PromptVariable(BaseModel):
    """Definition of a prompt template variable."""
    type: str
    required: bool = True
    default: Any = None
    description: str
    example: Any = None

class PromptTemplate(BaseModel):
    """A prompt template with metadata and variables."""
    name: str
    version: str
    description: str
    variables: dict[str, PromptVariable]
    system_prompt: str
    user_prompt: str

    def render(self, **kwargs) -> tuple[str, str]:
        """Render system and user prompts with provided variables."""
        # Validate required variables
        missing = [
            name for name, var in self.variables.items()
            if var.required and name not in kwargs
        ]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Apply defaults
        render_vars = {
            name: kwargs.get(name, var.default)
            for name, var in self.variables.items()
        }

        # Render with Jinja2 (strict mode - fail on undefined)
        env = Environment(undefined=StrictUndefined)
        system = env.from_string(self.system_prompt).render(**render_vars)
        user = env.from_string(self.user_prompt).render(**render_vars)

        return system, user

    def generate_documentation(self) -> str:
        """Generate markdown documentation for this prompt."""
        doc = f"# {self.name} (v{self.version})\n\n"
        doc += f"{self.description}\n\n"
        doc += "## Variables\n\n"

        for name, var in self.variables.items():
            doc += f"### `{name}`\n\n"
            doc += f"- **Type**: `{var.type}`\n"
            doc += f"- **Required**: {var.required}\n"
            if var.default is not None:
                doc += f"- **Default**: `{var.default}`\n"
            doc += f"- **Description**: {var.description}\n"
            if var.example is not None:
                doc += f"- **Example**: `{var.example}`\n"
            doc += "\n"

        return doc

class PromptLoader:
    """Loads and manages prompt templates."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """Load a prompt template by name."""
        if name in self._cache:
            return self._cache[name]

        template_file = self.template_dir / f"{name}.yaml"
        if not template_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_file}")

        with open(template_file) as f:
            data = yaml.safe_load(f)

        template = PromptTemplate(
            name=data["metadata"]["name"],
            version=data["metadata"]["version"],
            description=data["metadata"]["description"],
            variables={
                k: PromptVariable(**v)
                for k, v in data["variables"].items()
            },
            system_prompt=data["system_prompt"],
            user_prompt=data["user_prompt"],
        )

        self._cache[name] = template
        return template

    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [
            f.stem for f in self.template_dir.glob("*.yaml")
        ]

    def generate_docs(self, output_dir: Path) -> None:
        """Generate documentation for all templates."""
        output_dir.mkdir(parents=True, exist_ok=True)

        for name in self.list_templates():
            template = self.load(name)
            doc = template.generate_documentation()

            doc_file = output_dir / f"{name}.md"
            with open(doc_file, "w") as f:
                f.write(doc)
```

### 4. Chunking Strategy

**File**: `kg_extractor/chunking.py`

**Design**:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Chunk:
    """A chunk of files to process together."""
    index: int
    files: list[Path]
    total_size_bytes: int

    @property
    def size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

class ChunkingStrategy(ABC):
    """Abstract base for chunking strategies."""

    @abstractmethod
    def chunk(self, files: list[Path]) -> list[Chunk]:
        """Chunk files according to strategy."""
        pass

class HybridChunkingStrategy(ChunkingStrategy):
    """
    Hybrid directory-aware size-based chunking.

    - Respects directory boundaries (files in same dir stay together)
    - Targets chunks of ~target_size_mb
    - Splits large directories if needed
    """

    def __init__(
        self,
        target_size_mb: int = 10,
        max_files_per_chunk: int = 100,
    ):
        self.target_size_bytes = target_size_mb * 1024 * 1024
        self.max_files_per_chunk = max_files_per_chunk

    def chunk(self, files: list[Path]) -> list[Chunk]:
        # Group files by directory
        by_dir: dict[Path, list[Path]] = {}
        for file in files:
            by_dir.setdefault(file.parent, []).append(file)

        chunks = []
        current_chunk_files = []
        current_chunk_size = 0
        chunk_index = 0

        for dir_path, dir_files in sorted(by_dir.items()):
            dir_size = sum(f.stat().st_size for f in dir_files)

            # If adding this directory exceeds target, flush current chunk
            if current_chunk_files and (
                current_chunk_size + dir_size > self.target_size_bytes
                or len(current_chunk_files) + len(dir_files) > self.max_files_per_chunk
            ):
                chunks.append(Chunk(
                    index=chunk_index,
                    files=current_chunk_files,
                    total_size_bytes=current_chunk_size,
                ))
                chunk_index += 1
                current_chunk_files = []
                current_chunk_size = 0

            # Add directory files to current chunk
            current_chunk_files.extend(dir_files)
            current_chunk_size += dir_size

        # Flush remaining files
        if current_chunk_files:
            chunks.append(Chunk(
                index=chunk_index,
                files=current_chunk_files,
                total_size_bytes=current_chunk_size,
            ))

        return chunks
```

### 5. Deduplication Strategy

**File**: `kg_extractor/deduplication/base.py`

**Design**:

```python
from abc import ABC, abstractmethod
from typing import Any

class DeduplicationStrategy(ABC):
    """Abstract base for deduplication strategies."""

    @abstractmethod
    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> list[dict]:
        """
        Deduplicate new entities against existing ones.

        Returns:
            Merged entity list with duplicates removed.
        """
        pass
```

**File**: `kg_extractor/deduplication/urn_based.py`

**Design**:

```python
from kg_extractor.deduplication.base import DeduplicationStrategy

class URNBasedDeduplication(DeduplicationStrategy):
    """Simple URN-based deduplication with configurable merge strategy."""

    def __init__(self, merge_strategy: str = "merge_predicates"):
        self.merge_strategy = merge_strategy

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> list[dict]:
        # Build URN index
        by_urn = {e["@id"]: e for e in existing_entities}

        for entity in new_entities:
            urn = entity["@id"]

            if urn not in by_urn:
                # New entity
                by_urn[urn] = entity
            else:
                # Duplicate - merge according to strategy
                if self.merge_strategy == "first":
                    pass  # Keep existing
                elif self.merge_strategy == "last":
                    by_urn[urn] = entity  # Replace with new
                elif self.merge_strategy == "merge_predicates":
                    by_urn[urn] = self._merge_predicates(by_urn[urn], entity)

        return list(by_urn.values())

    def _merge_predicates(self, existing: dict, new: dict) -> dict:
        """Merge predicates from both entities."""
        merged = existing.copy()

        for key, value in new.items():
            if key in ["@id", "@type"]:
                continue  # Don't merge identity fields

            if key not in merged:
                merged[key] = value
            elif isinstance(value, list):
                # Merge arrays
                existing_values = merged[key] if isinstance(merged[key], list) else [merged[key]]
                merged[key] = existing_values + [v for v in value if v not in existing_values]
            # For scalars, prefer new value
            else:
                merged[key] = value

        return merged
```

### 6. Progress and Checkpointing

**File**: `kg_extractor/progress.py`

**Design**:

```python
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import json

class Checkpoint(BaseModel):
    """Checkpoint state for resumable extraction."""
    version: str = "1.0.0"
    timestamp: datetime
    chunk_index: int
    total_chunks: int
    entities_extracted: int
    entities: list[dict]
    metrics: dict
    config_hash: str  # Detect config changes

    def save(self, checkpoint_dir: Path) -> Path:
        """Save checkpoint to disk."""
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoint_dir / f"checkpoint_{self.chunk_index:04d}.json"
        with open(checkpoint_file, "w") as f:
            f.write(self.model_dump_json(indent=2))

        # Also save as "latest" for easy resume
        latest_file = checkpoint_dir / "checkpoint_latest.json"
        with open(latest_file, "w") as f:
            f.write(self.model_dump_json(indent=2))

        return checkpoint_file

    @classmethod
    def load(cls, checkpoint_file: Path) -> "Checkpoint":
        """Load checkpoint from disk."""
        with open(checkpoint_file) as f:
            return cls.model_validate_json(f.read())

    @classmethod
    def find_latest(cls, checkpoint_dir: Path) -> "Checkpoint | None":
        """Find and load the latest checkpoint."""
        latest_file = checkpoint_dir / "checkpoint_latest.json"
        if not latest_file.exists():
            return None
        return cls.load(latest_file)

class ProgressReporter:
    """Real-time progress reporting."""

    def __init__(self, total_chunks: int):
        self.total_chunks = total_chunks
        self.start_time = datetime.now()

    def report(
        self,
        chunk_index: int,
        entities_in_chunk: int,
        total_entities: int,
    ) -> None:
        """Report progress for current chunk."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        percent = (chunk_index / self.total_chunks) * 100

        print(f"[{chunk_index}/{self.total_chunks}] ({percent:.1f}%) "
              f"Extracted {entities_in_chunk} entities "
              f"(total: {total_entities}) "
              f"[{elapsed:.1f}s elapsed]")
```

## Implementation Phases

### Phase 1: Skateboard (Core Functionality)

**Goal**: End-to-end extraction working with minimal features

**Deliverables**:

1. ✅ Configuration system with Pydantic Settings
2. ✅ Simple file discovery (recursive glob)
3. ✅ Hybrid chunking strategy
4. ✅ Agent SDK integration with Vertex AI auth
5. ✅ Basic extraction agent (single prompt template)
6. ✅ URN-based deduplication
7. ✅ Entity validation (required fields, type names)
8. ✅ JSON-LD output
9. ✅ Basic metrics (entity counts, types)
10. ✅ CLI entry point

**Success Criteria**:

- Extracts 100+ entities from test dataset
- 95%+ validation pass rate
- Outputs valid JSON-LD

**Timeline**: 3-5 days

### Phase 2: Scooter (Production Features)

**Goal**: Add reliability and observability

**Deliverables**:

1. ✅ Checkpointing and resume
2. ✅ API key authentication (fallback)
3. ✅ Retry logic with exponential backoff
4. ✅ Structured JSON logging
5. ✅ Progress reporting
6. ✅ Comprehensive metrics (quality, performance, coverage)
7. ✅ Error handling and recovery
8. ✅ Prompt template system (YAML + Jinja2)
9. ✅ Configuration validation

**Success Criteria**:

- Resumes from checkpoint after simulated failure
- <5% file failure rate
- Logs are parseable and useful

**Timeline**: 5-7 days

### Phase 3: Bicycle (Polish and Optimization)

**Goal**: Optimize performance and usability

**Deliverables**:

1. ✅ Multiple chunking strategies (directory, size, count)
2. ✅ Configurable deduplication strategies
3. ✅ Prompt management CLI (`extractor prompt list`, `extractor prompt docs`)
4. ✅ Cost estimation (dry-run mode)
5. ✅ Enhanced validation (orphaned entities, broken refs)
6. ✅ Metrics export to multiple formats (JSON, CSV)
7. ✅ Documentation generation from prompts
8. ✅ Unit and integration tests

**Success Criteria**:

- Process 1000 files in <2 hours
- Zero config required for basic usage
- Comprehensive test coverage

**Timeline**: 5-7 days

### Phase 4: Car (Advanced Features)

**Goal**: Enable advanced use cases

**Deliverables**:

1. ✅ Parallel chunk processing
2. ✅ Agent-based semantic deduplication
3. ✅ Auto-tuning of chunk size
4. ✅ Schema-guided extraction
5. ✅ Incremental extraction mode
6. ✅ Graph query validation (load into Dgraph, run queries)
7. ✅ Performance profiling and optimization

**Success Criteria**:

- 3x speedup with parallel processing
- <5% duplicate entities with agent-based dedup
- Auto-tuning improves throughput by 20%

**Timeline**: 7-10 days

## Testing Strategy

### Unit Tests

- Configuration parsing and validation
- Chunking strategies
- URN-based deduplication
- Entity validation
- Prompt template rendering

### Integration Tests

- Agent SDK calls (with mocked responses)
- End-to-end extraction on small dataset
- Checkpoint save/load
- Authentication (Vertex AI + API key)

### Performance Tests

- Large dataset (10,000+ files)
- Memory usage profiling
- Checkpoint overhead measurement

### Validation Tests

- JSON-LD schema compliance
- Dgraph/Neo4j loading
- Entity relationship integrity

## Deployment

### Local Development

```bash
# Install with uv
uv sync

# Run extraction
uv run python extractor.py --data-dir ./data

# Resume from checkpoint
uv run python extractor.py --data-dir ./data --resume
```

### CI/CD

```yaml
# .github/workflows/extract.yml
name: Knowledge Graph Extraction

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2am

jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run extraction
        env:
          EXTRACTOR_AUTH__AUTH_METHOD: vertex_ai
          EXTRACTOR_AUTH__VERTEX_PROJECT_ID: my-project
        run: |
          uv sync
          uv run python extractor.py \
            --data-dir ./data \
            --output-file kg.jsonld

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: knowledge-graph
          path: kg.jsonld
```

## Risks and Mitigations

### Risk: Agent SDK Token Limits

**Mitigation**:

- Track token usage per chunk
- Implement automatic file splitting if needed
- Provide clear error messages with remediation

### Risk: Extraction Inconsistency

**Mitigation**:

- Strong validation rules enforced early
- Comprehensive prompt engineering with examples
- Metrics to detect quality degradation

### Risk: Performance at Scale

**Mitigation**:

- Profile on representative datasets
- Implement parallel processing in Phase 4
- Optimize chunk size based on metrics

### Risk: Cost Overruns

**Mitigation**:

- Add dry-run mode for cost estimation
- Track API usage in metrics
- Configurable limits

## References

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/python.md)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [JSON-LD Specification](https://json-ld.org/spec/latest/json-ld/)
- [uv Package Manager](https://github.com/astral-sh/uv)
