# Production Knowledge Graph Extraction System

A production-ready system for extracting knowledge graphs from diverse data sources using Claude AI.

## Overview

This is a Python-based extraction system that uses Claude Agent SDK to discover and extract entities and relationships from structured data. The system is designed to be:

- **Domain-agnostic**: No hardcoded entity types, discovers patterns from data
- **Production-ready**: Checkpointing, retries, observability, error handling
- **Testable**: Clean interfaces, dependency injection, comprehensive test suite
- **Configurable**: Environment variables, config files, CLI arguments
- **Resumable**: Checkpoint-based recovery from failures

## Project Status

🚧 **Under Development** - Currently in specification phase

See [.specify/memory/](.specify/memory/) for complete technical specifications following the [spec-kit](https://github.com/github/spec-kit) methodology.

## Architecture

```
kg_extractor/
├── config.py              # Pydantic configuration models
├── orchestrator.py        # Main workflow coordinator
├── chunking.py            # File chunking strategies
├── validation.py          # Entity validation
├── progress.py            # Checkpointing
├── metrics.py             # Metrics tracking
│
├── agents/
│   ├── base.py           # Agent SDK base with auth
│   ├── extraction.py     # Entity extraction agent
│   └── deduplication.py  # Semantic deduplication
│
├── deduplication/
│   ├── base.py           # Strategy interface
│   └── urn_based.py      # URN-based deduplication
│
├── llm/
│   ├── base.py           # LLM client protocol
│   └── anthropic.py      # Anthropic/Vertex AI client
│
├── filesystem.py         # File I/O abstraction
└── prompts/
    ├── loader.py         # YAML template loader
    └── templates/        # Jinja2 prompt templates
```

## Quick Start (Planned)

```bash
# Install with uv
uv sync

# Basic extraction
uv run python extractor.py --data-dir ./data

# With configuration
export EXTRACTOR_AUTH__AUTH_METHOD=api_key
export EXTRACTOR_AUTH__API_KEY=sk-ant-...
uv run python extractor.py \
  --data-dir ./data \
  --output-file kg.jsonld \
  --resume

# Dry run (cost estimation)
uv run python extractor.py --data-dir ./data --dry-run
```

## Documentation

### Specifications (.specify/memory/)

Following the [spec-kit](https://github.com/github/spec-kit) methodology:

- **[constitution.md](.specify/memory/constitution.md)** - Project principles and constraints
- **[spec.md](.specify/memory/specs/feat-kg-extraction-production/001/spec.md)** - Requirements and user stories
- **[plan.md](.specify/memory/specs/feat-kg-extraction-production/001/plan.md)** - Technical implementation plan
- **[research.md](.specify/memory/specs/feat-kg-extraction-production/001/research.md)** - Design decisions and rationale
- **[data-model.md](.specify/memory/specs/feat-kg-extraction-production/001/data-model.md)** - Data structures and schemas
- **[tasks.md](.specify/memory/specs/feat-kg-extraction-production/001/tasks.md)** - Implementation tasks (47 tasks across 4 phases)

### Contracts (.specify/memory/specs/.../contracts/)

Interface definitions for core components:

- **[llm-client.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/llm-client.md)** - LLM interface with retry/cost tracking
- **[file-system.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/file-system.md)** - File I/O abstraction
- **[checkpoint-store.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/checkpoint-store.md)** - Checkpoint persistence
- **[config.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/config.md)** - Configuration system
- **[prompts.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/prompts.md)** - YAML prompt templates
- **[deduplication.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/deduplication.md)** - Deduplication strategies

### Process Documentation (docs/)

- **[PROCESS.md](docs/PROCESS.md)** - Extraction methodology and validation rules

### Research (docs/research/)

Historical research and iteration reports from the experimental phase.

### Legacy Scripts (docs/legacy-scripts/)

Python scripts from the experimental iteration phase:

- `load_dgraph.py` - Reference for Dgraph loader implementation
- `load_neo4j.py` - Reference for Neo4j loader implementation
- `claude_cli_*.py` - Previous CLI-based extraction approach

## Key Features

### Phase 1: Skateboard (3-5 days)

- ✅ Spec complete - Ready for implementation
- ⏳ Basic extraction with Agent SDK
- ⏳ URN-based deduplication
- ⏳ Entity validation
- ⏳ JSON-LD output
- ⏳ CLI interface

### Phase 2: Scooter (5-7 days)

- ⏳ Checkpointing and resume
- ⏳ Retry logic with exponential backoff
- ⏳ Structured JSON logging
- ⏳ Progress reporting
- ⏳ Comprehensive metrics
- ⏳ Cost tracking

### Phase 3: Bicycle (5-7 days)

- ⏳ Multiple chunking strategies
- ⏳ Prompt management CLI
- ⏳ Enhanced validation
- ⏳ Metrics export (JSON/CSV)
- ⏳ Dry-run mode
- ⏳ >80% test coverage

### Phase 4: Car (7-10 days)

- ⏳ Parallel chunk processing
- ⏳ Agent-based semantic deduplication
- ⏳ Schema-guided extraction
- ⏳ Incremental extraction
- ⏳ Auto-tuning

## Design Principles

From [constitution.md](.specify/memory/constitution.md):

1. **Simplicity First, Then Sophistication** - Build skateboard → scooter → bicycle → car
2. **Domain-Agnostic Design** - No hardcoded entity types, AI discovers patterns
3. **Production Quality from Day One** - Strict typing, error handling, checkpointing
4. **Configuration Over Code** - Tunables via env vars, prompts in YAML
5. **Extensibility Through Interfaces** - Strategy pattern for swappable components
6. **Validation as First-Class Concern** - All entities must have @id, @type, name

## Configuration

Configuration is loaded from (in priority order):

1. CLI arguments (highest priority)
2. Environment variables (`EXTRACTOR_*`)
3. `.env` file
4. Default values (lowest priority)

Example `.env`:

```bash
EXTRACTOR_DATA_DIR=/data
EXTRACTOR_AUTH__AUTH_METHOD=vertex_ai
EXTRACTOR_AUTH__VERTEX_PROJECT_ID=my-project
EXTRACTOR_CHUNKING__STRATEGY=hybrid
EXTRACTOR_CHUNKING__TARGET_SIZE_MB=20
EXTRACTOR_CHECKPOINT__ENABLED=true
```

See [config.md](.specify/memory/specs/feat-kg-extraction-production/001/contracts/config.md) for full configuration reference.

## Development

### Setup

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run mypy kg_extractor

# Linting
uv run ruff check kg_extractor
```

### Testing

The system uses protocol-based interfaces for testability:

```python
# Production: Real LLM client
client = AnthropicLLMClient(auth_config)

# Testing: Mock LLM client
client = MockLLMClient(responses={
    "Extract entities": '{"entities": [...]}'
})

# Orchestrator works with both
orchestrator = ExtractionOrchestrator(llm_client=client, ...)
```

See [research.md](.specify/memory/specs/feat-kg-extraction-production/001/research.md#8-test-driven-development-strategy) for TDD strategy.

## Implementation Status

See [tasks.md](.specify/memory/specs/feat-kg-extraction-production/001/tasks.md) for complete task breakdown.

**Phase 1 (Skateboard)**: 0/16 tasks complete

- TASK-001: Project structure setup
- TASK-002: Configuration models
- TASK-003: Data models
- ... (see tasks.md for full list)

## Contributing

This is a spec-driven project following [spec-kit](https://github.com/github/spec-kit) methodology:

1. All changes start with specification updates
2. Specifications live in `.specify/memory/`
3. Implementation follows Test-Driven Development
4. All interfaces have protocol definitions and tests

## Authentication

Supports two authentication methods:

### Vertex AI (Production)

```bash
export EXTRACTOR_AUTH__AUTH_METHOD=vertex_ai
export EXTRACTOR_AUTH__VERTEX_PROJECT_ID=my-project
export EXTRACTOR_AUTH__VERTEX_REGION=us-central1
```

### API Key (Development)

```bash
export EXTRACTOR_AUTH__AUTH_METHOD=api_key
export EXTRACTOR_AUTH__API_KEY=sk-ant-api03-...
```

## Output Format

All graphs use JSON-LD format compatible with Neo4j and Dgraph:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "urn": "https://example.com/urn/"
  },
  "@graph": [
    {
      "@id": "urn:service:myapp",
      "@type": "Service",
      "name": "myapp",
      "owner": {"@id": "urn:user:alice@example.com"},
      "dependsOn": [{"@id": "urn:service:auth"}]
    }
  ]
}
```

## Validation Rules

All entities must satisfy:

- `@id` field with valid URN format: `urn:type:identifier`
- `@type` field with valid type name: `^[A-Z][A-Za-z0-9]*$`
- `name` field with human-readable name
- No `Relationship` entities (use predicates instead)

See [PROCESS.md](docs/PROCESS.md) for complete validation rules.

## License

MIT License - see [LICENSE](../LICENSE)

## Questions?

- **Specifications**: See `.specify/memory/` directory
- **Design Decisions**: See [research.md](.specify/memory/specs/feat-kg-extraction-production/001/research.md)
- **Implementation Plan**: See [plan.md](.specify/memory/specs/feat-kg-extraction-production/001/plan.md)
- **Tasks**: See [tasks.md](.specify/memory/specs/feat-kg-extraction-production/001/tasks.md)
