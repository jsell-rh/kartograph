# Specification: Production Knowledge Graph Extraction System

## Overview

**What**: A production-ready CLI tool that extracts entities and relationships from diverse data sources (code, configs, documentation, PDFs) and outputs JSON-LD for knowledge graph databases.

**Why**: Enable data engineers and ML teams to build rich knowledge graphs from any data source without writing custom extraction code for each domain.

## Problem Statement

### Current Pain Points

1. **Domain-Specific Extraction Scripts**: Teams write brittle, hardcoded extraction logic for each data source (infrastructure configs, codebases, documentation)

2. **Low Fidelity**: Traditional NLP/regex approaches extract only obvious entities, missing:
   - Nested entities in complex structures
   - Pattern-based entities (emails, URLs, Slack channels)
   - Implicit relationships
   - Context-specific entity types

3. **No Adaptability**: Scripts break when data structures change or new file types added

4. **Manual Entity Resolution**: No systematic way to handle duplicate entities across files

5. **Poor Observability**: Extraction failures are silent, no metrics to evaluate quality

### User Impact

**Data Engineers** spend weeks writing and maintaining extraction scripts instead of building insights.

**ML Engineers** can't build models on incomplete/low-quality knowledge graphs.

**Analysts** can't trust knowledge graphs due to missing entities and broken relationships.

## User Stories

### US-001: Extract from Infrastructure Configs

**As a** platform engineer
**I want** to extract entities from Kubernetes/Terraform configs
**So that** I can build a service catalog showing dependencies and ownership

**Acceptance Criteria**:

- ✅ Discovers entity types from data (Services, Namespaces, Teams, etc.)
- ✅ Extracts nested entities (endpoints, owners, dependencies)
- ✅ Captures ALL fields from source (not just common ones)
- ✅ Links related entities via predicates
- ✅ Outputs valid JSON-LD compatible with Dgraph/Neo4j

**Example**:

```yaml
# Input: data/services/myapp/app.yml
name: myapp
serviceOwners:
  - email: team@example.com
    role: Tech Lead
dependencies:
  - $ref: /services/auth/app.yml
```

```json
// Output: Entities extracted
{
  "entities": [
    {
      "@id": "urn:service:myapp",
      "@type": "Service",
      "name": "myapp",
      "hasOwner": {"@id": "urn:user:team@example.com"},
      "dependsOn": {"@id": "urn:service:auth"}
    },
    {
      "@id": "urn:user:team@example.com",
      "@type": "User",
      "name": "team@example.com",
      "email": "team@example.com",
      "role": "Tech Lead"
    }
  ]
}
```

### US-002: Extract from Codebase

**As a** developer
**I want** to extract code structure (modules, classes, functions)
**So that** I can understand dependencies and architecture

**Acceptance Criteria**:

- ✅ Discovers code-specific entities (PythonModule, Class, Function)
- ✅ Extracts imports/dependencies
- ✅ Captures docstrings and metadata
- ✅ Links functions to classes, modules to packages

### US-003: Resume After Failure

**As a** data engineer
**I want** extraction to resume from last checkpoint after crash
**So that** I don't lose hours of work on large datasets

**Acceptance Criteria**:

- ✅ Saves checkpoint after each chunk (configurable)
- ✅ `--resume` flag continues from last checkpoint
- ✅ Checkpoint includes: chunk index, entities extracted, metrics
- ✅ Checkpoint files use stable format (can migrate between versions)

### US-004: Monitor Extraction Quality

**As a** data engineer
**I want** metrics on extraction quality and performance
**So that** I can optimize configuration and validate results

**Acceptance Criteria**:

- ✅ Metrics include: entity counts, validation pass rate, processing speed
- ✅ Metrics exported to JSON for analysis
- ✅ Real-time progress reporting during extraction
- ✅ Detailed logs for failures (file, error, context)

### US-005: Configure via Environment

**As a** platform engineer
**I want** to configure extraction via environment variables
**So that** I can deploy in different environments (dev/staging/prod)

**Acceptance Criteria**:

- ✅ All tunables exposed as env vars (with `EXTRACTOR_` prefix)
- ✅ Support YAML config files for complex settings
- ✅ CLI flags override env vars/config files
- ✅ Validation errors show which config value is invalid

### US-006: Avoid Duplicate Entities

**As a** data engineer
**I want** the system to detect duplicate entities across chunks
**So that** my knowledge graph doesn't have redundant nodes

**Acceptance Criteria**:

- ✅ URN-based matching detects exact duplicates
- ✅ Merges entities with same URN (combines predicates)
- ✅ Configurable deduplication strategy (urn/agent/hybrid)
- ✅ Reports deduplication stats in metrics

### US-007: Support Multiple Auth Methods

**As a** platform engineer
**I want** to use Vertex AI or API key authentication
**So that** I can deploy in GCP or local environments

**Acceptance Criteria**:

- ✅ Vertex AI auth (primary): uses Application Default Credentials
- ✅ API key auth (fallback): direct Anthropic API
- ✅ Configurable via `EXTRACTOR_AUTH__AUTH_METHOD`
- ✅ Clear error messages if auth fails

### US-008: Customize Extraction Behavior

**As a** data engineer
**I want** to modify extraction prompts without changing code
**So that** I can tune extraction for my specific domain

**Acceptance Criteria**:

- ✅ Prompts stored as YAML templates with Jinja2
- ✅ Variable definitions document available inputs
- ✅ CLI tool to test prompt rendering
- ✅ Validation ensures required variables present

## Functional Requirements

### FR-001: File Processing

**Must**:

- Read files from specified data directory
- Support any file type (YAML, JSON, Python, Markdown, PDF, etc.)
- Handle large directories (10,000+ files)
- Process files in chunks for memory efficiency

**Must Not**:

- Require specific file structure or naming conventions
- Fail entire extraction if single file fails
- Load all files into memory simultaneously

### FR-002: Entity Extraction

**Must**:

- Discover entity types from data (not hardcoded)
- Extract ALL fields present in source (maximum fidelity)
- Create nested entities where appropriate (3+ properties, independent identity)
- Discover pattern-based entities (emails → EmailAddress, URLs → CodeRepository)
- Generate valid URNs (format: `urn:type:identifier`)

**Must Not**:

- Create Relationship entities (use predicates instead)
- Use invalid type names (must match `^[A-Za-z][A-Za-z0-9]*$`)
- Skip entities due to missing optional fields
- Create indexed types for arrays (`Items[0]` → use `Item`)

### FR-003: Relationship Extraction

**Must**:

- Express relationships as predicates on source entities
- Support both single references and arrays
- Resolve $ref pointers to target URNs
- Create bidirectional relationships where appropriate

**Must Not**:

- Create orphaned entities (no relationships)
- Leave broken references (target doesn't exist)

### FR-004: Validation

**Must**:

- Validate ALL entities have `@id`, `@type`, `name`
- Reject entities with invalid type names
- Fail chunk if >5% entities fail validation
- Report validation errors with file/entity context

### FR-005: Output

**Must**:

- Generate valid JSON-LD with `@context` and `@graph`
- Support loading into Dgraph and Neo4j
- Include metadata (timestamp, config, metrics)
- Use UTF-8 encoding

### FR-006: Checkpointing

**Must**:

- Save state after each chunk (configurable)
- Include: chunk index, entities, metrics, timestamp
- Support resume from checkpoint
- Validate checkpoint compatibility with current version

### FR-007: Metrics

**Must** track:

- Entity counts (total, by type)
- Relationship counts
- Validation pass rate
- Processing speed (files/sec, entities/sec)
- API usage (tokens, cost estimate)
- File success/failure rate

### FR-008: Error Handling

**Must**:

- Retry failed Agent SDK calls (max 3 times)
- Continue processing after file-level errors
- Log all errors with context
- Return non-zero exit code if >5% files fail

## Non-Functional Requirements

### NFR-001: Performance

- Process 1000 files in < 2 hours (with Agent SDK latency)
- Checkpoint overhead < 5% of total time
- Memory usage < 2GB for any dataset size

### NFR-002: Reliability

- < 5% file failure rate on well-formed inputs
- Resume from any checkpoint without data loss
- Graceful degradation if auth fails mid-extraction

### NFR-003: Observability

- Structured JSON logs for automated parsing
- Human-readable logs for local development
- Progress updates every 1 minute
- Final metrics summary on completion

### NFR-004: Maintainability

- 100% type coverage on public APIs
- All modules, classes, functions documented
- Configuration changes don't require code changes
- Pluggable components via interfaces

### NFR-005: Usability

- Single command to run extraction
- Clear error messages with remediation steps
- `--help` shows all options with examples
- Sensible defaults for all config values

## Success Criteria

### Baseline (Must Achieve)

1. ✅ Extracts 100x more entities than hardcoded approach (test: app-interface data)
2. ✅ 95%+ validation pass rate
3. ✅ 95%+ file success rate
4. ✅ Works on 3+ different domains (infrastructure, code, docs)
5. ✅ Resumes from checkpoint after simulated failure

### Target (Should Achieve)

6. ✅ 1.5+ relationships per entity (high connectivity)
7. ✅ <10% duplicate entities after deduplication
8. ✅ Process 10,000 files in < 5 hours
9. ✅ Zero config required for basic usage

### Stretch (Nice to Have)

10. ✅ Parallel chunk processing (3x speedup)
11. ✅ Agent-based semantic deduplication (better than URN)
12. ✅ Auto-tuning of chunk size based on complexity

## Out of Scope

- Real-time/streaming extraction (batch only)
- Graph query interface (extract only, load with separate tool)
- Web UI (CLI only)
- Custom entity resolution rules (use agent or URN matching only)
- Incremental updates (full re-extraction only)

## Risks & Mitigations

### Risk: Context Window Exceeded

**Impact**: Extraction fails for large files
**Mitigation**:

- Pre-check token count before extraction
- Fall back to file splitting if needed
- [NEEDS CLARIFICATION] Should we auto-split or fail with helpful error?

### Risk: Duplicate Entity Detection Accuracy

**Impact**: Knowledge graph has redundant nodes
**Mitigation**:

- Start with simple URN matching (deterministic)
- Add agent-based review for ambiguous cases later
- Track duplicate rate in metrics

### Risk: Agent SDK Latency

**Impact**: Extraction takes too long
**Mitigation**:

- Process chunks in parallel (future)
- Optimize chunk size based on profiling
- Cache entity index summaries

### Risk: API Cost

**Impact**: Large extractions expensive
**Mitigation**:

- Estimate cost before starting (dry-run mode?)
- Checkpoint frequently to avoid re-work
- [NEEDS CLARIFICATION] Should we add cost limit safety check?

## Dependencies

- Claude Agent SDK (anthropic-agent-sdk)
- Google Cloud SDK (for Vertex AI auth)
- Pydantic (configuration)
- Jinja2 (prompt templating)
- uv (package management)

## Glossary

- **Entity**: A node in the knowledge graph (Service, User, CodeRepository, etc.)
- **Relationship**: An edge between entities, expressed as a predicate
- **URN**: Uniform Resource Name (format: `urn:type:identifier`)
- **JSON-LD**: JSON for Linked Data, graph serialization format
- **Chunk**: A batch of files processed together
- **Checkpoint**: Saved state allowing resumption
- **Deduplication**: Process of merging duplicate entities

## References

- PROCESS.md: Extraction guidelines and validation rules
- Claude Agent SDK docs: <https://docs.claude.com/en/api/agent-sdk/python.md>
- JSON-LD spec: <https://json-ld.org/spec/latest/json-ld/>
