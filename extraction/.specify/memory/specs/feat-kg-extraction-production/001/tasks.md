# Implementation Tasks: Production KG Extraction System

## Overview

This document breaks down the implementation into concrete tasks organized by phase (Skateboard → Scooter → Bicycle → Car). Each task includes:

- **ID**: Unique task identifier
- **Description**: What needs to be done
- **Dependencies**: Tasks that must complete first
- **Estimated Effort**: T-shirt size (XS, S, M, L, XL)
- **Testing**: How to verify completion

## Phase 1: Skateboard (Core Functionality)

**Goal**: End-to-end extraction working with minimal features
**Timeline**: 3-5 days
**Success Criteria**: Extract 100+ entities from test dataset with 95%+ validation pass rate

### Setup Tasks

#### TASK-001: Project Structure Setup

- **Description**: Create project structure with uv package manager
- **Dependencies**: None
- **Effort**: XS
- **Steps**:
  1. Initialize `pyproject.toml` with uv
  2. Add dependencies: anthropic, pydantic, pydantic-settings, jinja2, pyyaml
  3. Create package structure (kg_extractor/ directories)
  4. Set up pytest and testing infrastructure
- **Testing**: `uv sync` succeeds, imports work

#### TASK-002: Configuration Models

- **Description**: Implement Pydantic configuration models
- **Dependencies**: TASK-001
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/config.py`
  2. Implement all config models from `contracts/config.md`
  3. Add validation logic
  4. Test environment variable parsing
- **Testing**: Unit tests for config validation, env var parsing

#### TASK-003: Data Models

- **Description**: Implement core data models
- **Dependencies**: TASK-001
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/models.py`
  2. Implement Entity, ExtractionResult, ValidationError models
  3. Add URN and type name validators
  4. Implement JSON-LD serialization
- **Testing**: Unit tests for validation rules, serialization

### Interface Implementation Tasks

#### TASK-004: LLM Client Interface

- **Description**: Implement LLM client with Vertex AI and API key support
- **Dependencies**: TASK-002
- **Effort**: L
- **Steps**:
  1. Create `kg_extractor/llm/base.py` with Protocol
  2. Implement `AnthropicLLMClient` with both auth methods
  3. Implement `MockLLMClient` for testing
  4. Add error handling for rate limits, context overflow
- **Testing**: Unit tests with mocks, integration test with real API (small)

#### TASK-005: File System Interface

- **Description**: Implement file system abstraction
- **Dependencies**: TASK-001
- **Effort**: S
- **Steps**:
  1. Create `kg_extractor/filesystem.py`
  2. Implement `DiskFileSystem`
  3. Implement `InMemoryFileSystem` for testing
  4. Add file discovery with glob patterns
- **Testing**: Contract tests for both implementations

#### TASK-006: Checkpoint Store Interface

- **Description**: Implement checkpoint persistence
- **Dependencies**: TASK-003
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/progress.py`
  2. Implement `Checkpoint` model
  3. Implement `DiskCheckpointStore`
  4. Implement `InMemoryCheckpointStore` for testing
- **Testing**: Save/load tests, contract tests

### Core Logic Tasks

#### TASK-007: Chunking Strategy

- **Description**: Implement hybrid chunking strategy
- **Dependencies**: TASK-005
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/chunking.py`
  2. Implement `HybridChunkingStrategy`
  3. Add directory-aware size-based logic
  4. Handle edge cases (empty dirs, huge files)
- **Testing**: Unit tests with various file structures

#### TASK-008: Entity Validation

- **Description**: Implement validation logic
- **Dependencies**: TASK-003
- **Effort**: S
- **Steps**:
  1. Create `kg_extractor/validation.py`
  2. Implement `validate_entity()` function
  3. Add URN format validation
  4. Add required field validation
  5. Add type name validation
- **Testing**: Unit tests with valid/invalid entities

#### TASK-009: URN-Based Deduplication

- **Description**: Implement URN-based deduplication
- **Dependencies**: TASK-003
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/deduplication/urn_based.py`
  2. Implement `URNBasedDeduplication` class
  3. Implement merge_predicates logic
  4. Add metrics tracking
- **Testing**: Unit tests with duplicate entities

#### TASK-010: Prompt Template System

- **Description**: Implement YAML-based prompt templates
- **Dependencies**: TASK-001
- **Effort**: M
- **Steps**:
  1. Create `kg_extractor/prompts/loader.py`
  2. Implement `PromptTemplate` model
  3. Implement `DiskPromptLoader`
  4. Create extraction.yaml template
  5. Add Jinja2 rendering
- **Testing**: Unit tests for rendering, template loading

#### TASK-011: Extraction Agent

- **Description**: Implement entity extraction agent
- **Dependencies**: TASK-004, TASK-010
- **Effort**: L
- **Steps**:
  1. Create `kg_extractor/agents/extraction.py`
  2. Implement `ExtractionAgent` class
  3. Integrate Agent SDK
  4. Parse and validate LLM responses
  5. Handle extraction errors
- **Testing**: Integration tests with mock LLM

#### TASK-012: Main Orchestrator

- **Description**: Implement orchestrator coordinating all components
- **Dependencies**: TASK-007, TASK-008, TASK-009, TASK-011
- **Effort**: XL
- **Steps**:
  1. Create `kg_extractor/orchestrator.py`
  2. Implement `ExtractionOrchestrator` class
  3. Wire up all dependencies
  4. Implement extraction workflow
  5. Add progress reporting
- **Testing**: End-to-end test with small dataset

#### TASK-013: CLI Entry Point

- **Description**: Create command-line interface
- **Dependencies**: TASK-012
- **Effort**: M
- **Steps**:
  1. Create `extractor.py` CLI entry point
  2. Add argument parsing
  3. Wire up configuration
  4. Add logging setup
  5. Handle errors gracefully
- **Testing**: Manual CLI testing, integration tests

#### TASK-014: JSON-LD Output

- **Description**: Implement JSON-LD graph output
- **Dependencies**: TASK-012
- **Effort**: S
- **Steps**:
  1. Create `kg_extractor/output.py`
  2. Implement `JSONLDGraph` class
  3. Add context generation
  4. Implement file writer
- **Testing**: Validate JSON-LD against spec

#### TASK-015: Basic Metrics

- **Description**: Implement basic metrics tracking
- **Dependencies**: TASK-012
- **Effort**: S
- **Steps**:
  1. Create `kg_extractor/metrics.py`
  2. Track entity counts, types
  3. Track timing metrics
  4. Output metrics summary
- **Testing**: Verify metrics accuracy

### Phase 1 Completion

#### TASK-016: End-to-End Test

- **Description**: Run full extraction on test dataset
- **Dependencies**: All Phase 1 tasks
- **Effort**: M
- **Steps**:
  1. Create test dataset (sample YAML files)
  2. Run extraction end-to-end
  3. Verify entity count >100
  4. Verify validation pass rate >95%
  5. Verify JSON-LD validity
- **Testing**: Automated integration test

---

## Phase 2: Scooter (Production Features)

**Goal**: Add reliability and observability
**Timeline**: 5-7 days
**Success Criteria**: Resume from checkpoint after failure, <5% file failure rate

### Reliability Tasks

#### TASK-201: Checkpointing Integration

- **Description**: Integrate checkpointing into orchestrator
- **Dependencies**: TASK-012, TASK-006
- **Effort**: M
- **Steps**:
  1. Add checkpoint saves at each chunk
  2. Implement resume logic
  3. Add config hash validation
  4. Handle checkpoint incompatibility
- **Testing**: Simulate crash, resume, verify correctness

#### TASK-202: Retry Logic

- **Description**: Add retry logic to LLM client
- **Dependencies**: TASK-004
- **Effort**: M
- **Steps**:
  1. Implement `RetryingLLMClient` decorator
  2. Add exponential backoff
  3. Handle rate limits specially
  4. Add max retries configuration
- **Testing**: Mock rate limits, verify retries

#### TASK-203: Error Handling

- **Description**: Comprehensive error handling
- **Dependencies**: TASK-012
- **Effort**: M
- **Steps**:
  1. Add try/catch at all boundaries
  2. Categorize errors (retryable vs fatal)
  3. Log errors with context
  4. Continue on non-fatal errors
- **Testing**: Inject failures, verify recovery

### Observability Tasks

#### TASK-204: Structured Logging

- **Description**: Implement JSON logging
- **Dependencies**: TASK-002
- **Effort**: S
- **Steps**:
  1. Add LogEntry model
  2. Implement JSON log formatter
  3. Add structured logging throughout
  4. Support both JSON and human-readable
- **Testing**: Parse JSON logs, verify fields

#### TASK-205: Progress Reporting

- **Description**: Real-time progress updates
- **Dependencies**: TASK-012
- **Effort**: S
- **Steps**:
  1. Implement `ProgressReporter` class
  2. Report after each chunk
  3. Show ETA calculation
  4. Add progress bar (optional)
- **Testing**: Verify progress accuracy

#### TASK-206: Comprehensive Metrics

- **Description**: Add all metric categories
- **Dependencies**: TASK-015
- **Effort**: M
- **Steps**:
  1. Implement PerformanceMetrics
  2. Implement QualityMetrics
  3. Implement CoverageMetrics
  4. Track LLM token usage
  5. Calculate cost estimates
- **Testing**: Verify all metrics calculated correctly

#### TASK-207: Cost Tracking

- **Description**: Track and estimate LLM costs
- **Dependencies**: TASK-004
- **Effort**: S
- **Steps**:
  1. Implement `CostTrackingLLMClient` decorator
  2. Track input/output tokens
  3. Calculate cost estimates
  4. Report costs in metrics
- **Testing**: Verify cost calculations

### Configuration Tasks

#### TASK-208: Environment Variable Support

- **Description**: Full env var configuration
- **Dependencies**: TASK-002
- **Effort**: S
- **Steps**:
  1. Test all nested env vars
  2. Document env var naming
  3. Add .env.example file
  4. Validate env var parsing
- **Testing**: Load config from various env var combinations

#### TASK-209: Config Validation CLI

- **Description**: Add config validation command
- **Dependencies**: TASK-013
- **Effort**: XS
- **Steps**:
  1. Add `extractor config validate` command
  2. Show parsed config
  3. Report validation errors
  4. Show defaults applied
- **Testing**: Test with valid/invalid configs

### Phase 2 Completion

#### TASK-210: Failure Recovery Test

- **Description**: Test checkpoint resume after simulated failure
- **Dependencies**: All Phase 2 tasks
- **Effort**: M
- **Steps**:
  1. Run extraction
  2. Kill process mid-run
  3. Resume with --resume flag
  4. Verify no duplicate work
  5. Verify final results correct
- **Testing**: Automated test with process killing

---

## Phase 3: Bicycle (Polish and Optimization)

**Goal**: Optimize performance and usability
**Timeline**: 5-7 days
**Success Criteria**: Process 1000 files in <2 hours, zero config required for basic usage

### Strategy Tasks

#### TASK-301: Multiple Chunking Strategies

- **Description**: Implement additional chunking strategies
- **Dependencies**: TASK-007
- **Effort**: M
- **Steps**:
  1. Implement `DirectoryChunkingStrategy`
  2. Implement `SizeChunkingStrategy`
  3. Implement `CountChunkingStrategy`
  4. Add strategy selection logic
- **Testing**: Test each strategy with various datasets

#### TASK-302: Configurable Deduplication

- **Description**: Make deduplication strategy configurable
- **Dependencies**: TASK-009
- **Effort**: S
- **Steps**:
  1. Add strategy factory function
  2. Add config option for strategy selection
  3. Support different merge strategies
  4. Document trade-offs
- **Testing**: Test switching strategies via config

### Prompt Management Tasks

#### TASK-303: Prompt Management CLI

- **Description**: Add prompt management commands
- **Dependencies**: TASK-010
- **Effort**: M
- **Steps**:
  1. Add `extractor prompt list` command
  2. Add `extractor prompt show <name>` command
  3. Add `extractor prompt docs` command
  4. Add `extractor prompt test` command (render with test data)
- **Testing**: Test each command

#### TASK-304: Prompt Documentation Generation

- **Description**: Auto-generate prompt docs
- **Dependencies**: TASK-303
- **Effort**: S
- **Steps**:
  1. Implement template.generate_documentation()
  2. Generate markdown for each prompt
  3. Include variable definitions
  4. Add usage examples
- **Testing**: Verify generated docs are correct

### Validation Tasks

#### TASK-305: Enhanced Validation

- **Description**: Add advanced validation rules
- **Dependencies**: TASK-008
- **Effort**: M
- **Steps**:
  1. Detect orphaned entities (no relationships)
  2. Detect broken references (URNs not in graph)
  3. Validate relationship consistency
  4. Add validation report
- **Testing**: Test with various graph structures

#### TASK-306: Validation Report

- **Description**: Generate detailed validation report
- **Dependencies**: TASK-305
- **Effort**: S
- **Steps**:
  1. Create validation report model
  2. Group errors by type
  3. Show severity breakdown
  4. Export report as JSON/Markdown
- **Testing**: Verify report completeness

### Metrics Tasks

#### TASK-307: Metrics Export

- **Description**: Export metrics to multiple formats
- **Dependencies**: TASK-206
- **Effort**: S
- **Steps**:
  1. Add JSON export
  2. Add CSV export
  3. Add markdown summary export
  4. Add `--metrics-output` CLI flag
- **Testing**: Test each export format

### Usability Tasks

#### TASK-308: Dry-Run Mode

- **Description**: Add dry-run for cost estimation
- **Dependencies**: TASK-207
- **Effort**: M
- **Steps**:
  1. Add `--dry-run` flag
  2. Discover files without processing
  3. Estimate token usage
  4. Estimate cost
  5. Show what would be done
- **Testing**: Verify estimates are reasonable

#### TASK-309: Smart Defaults

- **Description**: Make config optional for common cases
- **Dependencies**: TASK-002
- **Effort**: S
- **Steps**:
  1. Add sensible defaults for all config
  2. Auto-detect data directory structure
  3. Make output file optional (default: ./kg.jsonld)
  4. Document minimal usage
- **Testing**: Test with zero config

### Testing Tasks

#### TASK-310: Test Suite Completion

- **Description**: Achieve comprehensive test coverage
- **Dependencies**: All previous tasks
- **Effort**: L
- **Steps**:
  1. Write unit tests for all modules
  2. Write integration tests for workflows
  3. Write contract tests for interfaces
  4. Achieve >80% code coverage
  5. Add property-based tests (Hypothesis)
- **Testing**: Coverage report, all tests passing

### Phase 3 Completion

#### TASK-311: Performance Benchmark

- **Description**: Benchmark on 1000-file dataset
- **Dependencies**: All Phase 3 tasks
- **Effort**: M
- **Steps**:
  1. Create 1000-file test dataset
  2. Run extraction, measure time
  3. Verify completes in <2 hours
  4. Profile for bottlenecks
  5. Document performance characteristics
- **Testing**: Automated performance test

---

## Phase 4: Car (Advanced Features)

**Goal**: Enable advanced use cases
**Timeline**: 7-10 days
**Success Criteria**: 3x speedup with parallelization, <5% duplicates with agent-based dedup

### Parallelization Tasks

#### TASK-401: Parallel Chunk Processing

- **Description**: Process multiple chunks in parallel
- **Dependencies**: TASK-012
- **Effort**: L
- **Steps**:
  1. Add async/await throughout orchestrator
  2. Implement parallel chunk processing
  3. Add concurrency limit
  4. Handle shared state (checkpoints, metrics)
  5. Add `--workers` CLI flag
- **Testing**: Verify parallelization correctness, no race conditions

#### TASK-402: Parallel Deduplication

- **Description**: Parallelize deduplication comparisons
- **Dependencies**: TASK-009, TASK-401
- **Effort**: M
- **Steps**:
  1. Batch entity comparisons
  2. Parallelize comparison batches
  3. Merge results safely
- **Testing**: Verify dedup correctness with parallelization

### Agent-Based Deduplication Tasks

#### TASK-403: Agent-Based Deduplication

- **Description**: Implement LLM-powered semantic deduplication
- **Dependencies**: TASK-004, TASK-009
- **Effort**: L
- **Steps**:
  1. Implement `AgentBasedDeduplication` class
  2. Create deduplication prompt template
  3. Implement entity comparison logic
  4. Add similarity threshold configuration
  5. Optimize batch comparisons
- **Testing**: Test with semantically similar entities

#### TASK-404: Hybrid Deduplication

- **Description**: Combine URN-based and agent-based
- **Dependencies**: TASK-009, TASK-403
- **Effort**: M
- **Steps**:
  1. Implement `HybridDeduplication` class
  2. URN-based for obvious duplicates
  3. Agent-based for ambiguous cases
  4. Add intelligent fallback logic
- **Testing**: Benchmark vs pure strategies

### Advanced Features

#### TASK-405: Schema-Guided Extraction

- **Description**: Use schemas to guide extraction
- **Dependencies**: TASK-011
- **Effort**: L
- **Steps**:
  1. Add schema directory configuration
  2. Load schemas from directory
  3. Inject schema context into prompts
  4. Validate extracted entities against schemas
- **Testing**: Test with/without schemas, verify improvement

#### TASK-406: Incremental Extraction

- **Description**: Only extract from changed files
- **Dependencies**: TASK-012
- **Effort**: L
- **Steps**:
  1. Track file modification times in checkpoint
  2. Detect changed files
  3. Re-extract only changed files
  4. Merge with existing entities
  5. Add `--incremental` flag
- **Testing**: Modify files, verify only those re-extracted

#### TASK-407: Auto-Tuning

- **Description**: Automatically tune chunk size
- **Dependencies**: TASK-007, TASK-206
- **Effort**: M
- **Steps**:
  1. Track chunk processing time
  2. Detect optimal chunk size
  3. Adjust chunk size dynamically
  4. Report tuning in metrics
- **Testing**: Verify chunk size converges to optimal

#### TASK-408: Graph Validation

- **Description**: Load into Dgraph and validate
- **Dependencies**: TASK-014
- **Effort**: M
- **Steps**:
  1. Add Dgraph loader
  2. Test loading JSON-LD
  3. Run graph queries to validate
  4. Report graph statistics
  5. Add `--validate-in-dgraph` flag
- **Testing**: Test with local Dgraph instance

### Performance Optimization

#### TASK-409: Performance Profiling

- **Description**: Profile and optimize bottlenecks
- **Dependencies**: All Phase 4 tasks
- **Effort**: L
- **Steps**:
  1. Profile extraction on large dataset
  2. Identify bottlenecks
  3. Optimize critical paths
  4. Reduce memory usage
  5. Document optimizations
- **Testing**: Before/after performance comparison

### Phase 4 Completion

#### TASK-410: Full-Scale Test

- **Description**: Extract from full app-interface dataset
- **Dependencies**: All Phase 4 tasks
- **Effort**: L
- **Steps**:
  1. Run on full app-interface
  2. Verify 3x speedup with parallelization
  3. Verify <5% duplicate rate
  4. Generate comprehensive metrics
  5. Validate in Dgraph
- **Testing**: Full production run

---

## Task Dependencies Graph

```
Phase 1 (Skateboard):
001 → 002, 003, 004, 005, 006
002 → 004, 013
003 → 006, 008, 009, 014
004 → 011
005 → 007
007, 008, 009, 011 → 012
012 → 013, 014, 015
013, 014, 015 → 016

Phase 2 (Scooter):
012, 006 → 201
004 → 202
012 → 203
002 → 204, 208
012 → 205
015 → 206
004 → 207
013 → 209
201-209 → 210

Phase 3 (Bicycle):
007 → 301
009 → 302
010 → 303
303 → 304
008 → 305
305 → 306
206 → 307
207 → 308
002 → 309
All → 310
All Phase 3 → 311

Phase 4 (Car):
012 → 401
009, 401 → 402
004, 009 → 403
009, 403 → 404
011 → 405
012 → 406
007, 206 → 407
014 → 408
All Phase 4 → 409
All → 410
```

## Effort Summary

| Phase | Tasks | XS | S | M | L | XL | Total Days |
|-------|-------|----|----|---|----|----|----|
| Phase 1 | 16 | 2 | 4 | 7 | 2 | 1 | 3-5 |
| Phase 2 | 10 | 2 | 5 | 3 | 0 | 0 | 5-7 |
| Phase 3 | 11 | 1 | 5 | 4 | 1 | 0 | 5-7 |
| Phase 4 | 10 | 0 | 0 | 4 | 6 | 0 | 7-10 |
| **Total** | **47** | **5** | **14** | **18** | **9** | **1** | **20-29** |

## Testing Strategy by Phase

**Phase 1**: Focus on unit and integration tests

- Every component has unit tests
- End-to-end test on small dataset
- Contract tests for all interfaces

**Phase 2**: Add reliability testing

- Failure injection tests
- Checkpoint resume tests
- Performance monitoring

**Phase 3**: Comprehensive testing

- Property-based tests
- Performance benchmarks
- Coverage >80%

**Phase 4**: Production testing

- Large-scale integration tests
- Parallelization correctness
- Full dataset validation

## References

- `spec.md`: Requirements and user stories
- `plan.md`: Technical implementation details
- `contracts/`: Interface definitions
- `data-model.md`: Data structure specifications
