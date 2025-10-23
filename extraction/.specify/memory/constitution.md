# Production Knowledge Graph Extraction System - Constitution

## Project Purpose

Build a production-ready, domain-agnostic knowledge graph extraction system that leverages Claude's reasoning capabilities through the Agent SDK to extract rich, high-fidelity entity and relationship information from diverse data sources.

## Core Principles

### 1. Simplicity First, Then Sophistication

**Rationale**: Build incrementally from simple, working solutions to advanced capabilities.

- Start with "skateboard" implementations that work end-to-end
- Iterate to "scooter" → "bicycle" → "car" as needs emerge
- Avoid premature optimization or over-engineering
- Each phase must be fully functional before advancing

**Example**: Begin with simple URN-based deduplication before adding AI-powered semantic matching.

### 2. Domain-Agnostic Design

**Rationale**: The system must work across infrastructure configs, codebases, documentation, PDFs, and any future data types.

- NO hardcoded entity types or extraction logic
- Use AI reasoning to discover patterns in data
- Leverage schemas when available, but don't depend on them
- Prompt templates define extraction behavior, not Python code

**Anti-pattern**: Hardcoded `if file_type == 'yaml': extract_services()` logic.

### 3. Production Quality from Day One

**Rationale**: This system will run in CI/production, handle failures gracefully, and provide observability.

- Strict typing with Python 3.13+ and Pydantic
- Comprehensive error handling and retries
- Checkpointing for resumability
- Dual logging (human-readable + structured JSON)
- Metrics for evaluation and monitoring

**Non-negotiable**: Every component must handle failures gracefully.

### 4. Configuration Over Code

**Rationale**: Behavior should be configurable without code changes.

- All tunables exposed via Pydantic Settings
- Environment variables for deployment flexibility
- YAML files for complex configurations
- Prompt templates in YAML, not Python strings
- Pluggable strategies via interfaces

**Example**: Chunking strategy, deduplication method, checkpoint frequency all configurable.

### 5. Extensibility Through Interfaces

**Rationale**: Future enhancements should slot in without refactoring core system.

- Strategy pattern for swappable implementations
- Abstract base classes for key components
- Plugin architecture where applicable
- Clear contracts between components

**Example**: Multiple deduplication strategies sharing a common interface.

### 6. Validation as First-Class Concern

**Rationale**: Ensure extracted data meets quality standards before downstream use.

- ALL entities must have `@id`, `@type`, `name`
- Type names must be valid identifiers (`^[A-Za-z][A-Za-z0-9]*$`)
- NO Relationship entities (use predicates)
- NO indexed types (`Items[0]` → `Item`)
- Validation happens during extraction, not post-processing

**Enforcement**: Fail fast on validation errors with actionable error messages.

### 7. Measurable Performance

**Rationale**: We can't improve what we don't measure.

- Track entity/relationship counts and density
- Measure extraction quality (validation pass rate)
- Monitor performance (time, tokens, throughput)
- Assess coverage and completeness
- Export metrics for analysis and comparison

**Goal**: Every iteration should be measurably better than the last.

## Technical Constraints

### Required Technologies

- **Language**: Python 3.13+
- **Package Manager**: uv (for fast, deterministic builds)
- **LLM Integration**: Claude Agent SDK (anthropic-agent-sdk)
- **Configuration**: Pydantic Settings
- **Templating**: Jinja2 (for prompts)
- **Authentication**: Google Vertex AI (primary), Anthropic API key (fallback)

### Prohibited Patterns

- ❌ Hardcoded prompts in Python strings
- ❌ Hardcoded entity types or extraction logic
- ❌ Silent failures without logging
- ❌ Blocking operations without timeouts
- ❌ Untyped function signatures
- ❌ Configuration values scattered in code

### Quality Standards

- **Type Coverage**: 100% of public API typed
- **Error Handling**: Every external call wrapped in try/except with logging
- **Testing**: Unit tests for business logic, integration tests for Agent SDK calls
- **Documentation**: Every module, class, and function has docstrings
- **Logging**: Structured logging with context (file, chunk, entity count)

## Development Workflow

### Spec-Driven Development

1. **Specify**: Define WHAT and WHY in `.specify/memory/specs/`
2. **Plan**: Design HOW in technical implementation plans
3. **Clarify**: Resolve ambiguities before coding
4. **Implement**: Build according to spec
5. **Validate**: Verify against success criteria
6. **Iterate**: Refine based on metrics

### Version Control

- Feature branches from `main`
- Atomic commits with descriptive messages
- Squash merge to main after review

### Code Review Criteria

- ✅ Follows project principles
- ✅ Type-safe and tested
- ✅ Configurable behavior
- ✅ Comprehensive error handling
- ✅ Logging and metrics
- ✅ Documentation complete

## Success Criteria

### Functional

- ✅ Extracts entities from diverse file types
- ✅ Discovers entities through AI reasoning (not hardcoded)
- ✅ Maintains entity identity across chunks
- ✅ Outputs valid JSON-LD
- ✅ Resumes from checkpoints after failure
- ✅ Supports both Vertex AI and API key auth

### Non-Functional

- ✅ Processes 1000+ files without human intervention
- ✅ < 5% file failure rate
- ✅ Checkpoint overhead < 5% of total time
- ✅ 100% entity validation pass rate
- ✅ Configurable via environment variables
- ✅ Logs actionable error messages

### Quality

- ✅ 90%+ type coverage
- ✅ All public APIs documented
- ✅ Core business logic unit tested
- ✅ Integration tests with Agent SDK
- ✅ Metrics exported to JSON

## Guardrails

### When to Clarify

Stop and ask for clarification if:

- User story is ambiguous ("might need", "could have")
- Success criteria are unmeasurable
- Technical approach has multiple valid options
- Requirements conflict with principles

### When to Simplify

Choose simpler implementation if:

- Complex solution doesn't have measurable benefit
- Simpler solution meets 80% of needs
- Complexity can be added later if needed
- Testing/maintenance burden is high

### When to Refactor

Refactor existing code when:

- New requirement violates current architecture
- Pattern repeated 3+ times
- Component too complex to understand/test
- Performance bottleneck identified

## Revision History

- **v1.0.0** (2025-01-23): Initial constitution for production KG extraction system
