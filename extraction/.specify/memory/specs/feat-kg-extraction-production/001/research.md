# Research: Production KG Extraction System

## Context

This document captures research, context, and decisions made during the design of the production knowledge graph extraction system. It explains the **why** behind key architectural choices.

## Problem Statement

The existing interactive KG extraction approach (using Claude CLI orchestration) successfully demonstrated:

- Domain-agnostic entity discovery (100x more entities than hardcoded approaches)
- High-fidelity extraction with scalar predicates
- Schema-guided reasoning

However, it had limitations:

- **Not production-ready**: Interactive, requires manual intervention
- **No resumability**: Failures require starting over
- **No observability**: Limited metrics and logging
- **No configurability**: Hardcoded prompts and settings
- **Not testable**: Difficult to test LLM-dependent logic

## Research Questions

### 1. Why Agent SDK vs CLI Orchestration?

**Question**: Should we continue using Claude CLI (subprocess orchestration) or migrate to Agent SDK?

**Research**:

- **CLI Approach**:
  - ✅ Works well for interactive use
  - ✅ Handles context automatically
  - ❌ Subprocess overhead
  - ❌ Harder to handle errors programmatically
  - ❌ Limited control over retries, rate limiting
  - ❌ Difficult to mock for testing

- **Agent SDK Approach**:
  - ✅ Native Python integration
  - ✅ Programmatic error handling
  - ✅ Built-in tool ecosystem
  - ✅ Structured outputs support
  - ✅ Easier to test with mocks
  - ✅ Retry/circuit breaker patterns
  - ❌ Context management is manual
  - ❌ Newer, less battle-tested

**Decision**: **Use Agent SDK**

**Rationale**:

1. Production systems need programmatic error handling
2. Testing requires mockable interfaces
3. Retry/rate limiting crucial for reliability
4. Context management is solvable with chunking
5. Native Python is more maintainable

**References**:

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/python.md)
- Previous iteration: `/home/jsell/code/kartograph-kg-iteration/`

---

### 2. How to Chunk Large Datasets?

**Question**: What chunking strategy balances semantic coherence with manageable context size?

**Research**:

We evaluated four strategies:

#### A. File Count Chunking

- **Approach**: Group files into chunks of N files each
- **Pros**: Simple, predictable chunk count
- **Cons**: Ignores file size (could overwhelm context), ignores semantic boundaries

#### B. Directory Structure Chunking

- **Approach**: Process one directory at a time
- **Pros**: Semantic coherence (related files together), respects organizational structure
- **Cons**: Unbalanced sizes (some dirs have 1000s of files), unpredictable performance

#### C. Size-Based Chunking

- **Approach**: Target ~10MB per chunk
- **Pros**: Balanced processing time, predictable context usage
- **Cons**: May split semantically related files, requires size calculation overhead

#### D. Hybrid Directory-Aware Size-Based Chunking

- **Approach**:
  1. Group files by directory
  2. Target ~10MB chunks
  3. Keep files in same directory together
  4. Split large directories if needed
- **Pros**: Semantic coherence + balanced sizes
- **Cons**: Slightly more complex implementation

**Decision**: **Hybrid Directory-Aware Size-Based Chunking**

**Rationale**:

1. Maintains semantic coherence (service configs stay together)
2. Predictable chunk sizes → consistent performance
3. Complexity is minimal (see `plan.md` implementation)
4. Configurable via settings (can swap strategies later)

**Parameters**:

- Target chunk size: 10MB (configurable)
- Max files per chunk: 100 (configurable)
- Respect directory boundaries: True (configurable)

---

### 3. How to Deduplicate Entities Across Chunks?

**Question**: How do we merge duplicate entities discovered in different chunks?

**Research**:

#### Approach A: No Deduplication

- **Pros**: Simple, fast
- **Cons**: Duplicate entities in output (unacceptable)

#### Approach B: URN-Based Exact Match

- **Approach**: Build index by `@id` (URN), merge on exact match
- **Pros**: Fast (O(n) with hash table), deterministic, simple to test
- **Cons**: Misses semantic duplicates (e.g., `urn:user:alice` vs `urn:person:alice@example.com`)

#### Approach C: Agent-Based Semantic Matching

- **Approach**: Use LLM to compare entities and decide if they're duplicates
- **Pros**: Handles semantic duplicates, context-aware
- **Cons**: Slow (O(n²) comparisons), expensive (LLM calls), non-deterministic

#### Approach D: Hybrid URN + Agent

- **Approach**:
  1. URN-based deduplication (fast path)
  2. Agent-based matching for ambiguous cases (e.g., different URN formats)
- **Pros**: Fast for obvious cases, smart for edge cases
- **Cons**: More complex implementation

**Decision**: **Start with URN-Based (Approach B), Design for Hybrid (Approach D)**

**Rationale** (per user guidance):
> "Do you think we'd get substantial gains? Why don't we start with simple, but make sure that the way it's built allows for swapping out/augmenting the dedupe method."

1. **Skateboard phase**: URN-based is sufficient for 95%+ cases
2. **Extensibility**: Strategy pattern allows swapping implementations
3. **Future-proof**: Can add agent-based as Phase 4 enhancement
4. **Testability**: Deterministic deduplication is easier to test

**Merge Strategies** (for URN-based):

- `first`: Keep first entity encountered (fast)
- `last`: Keep last entity encountered (simple)
- `merge_predicates`: Merge fields from both entities (comprehensive, default)

---

### 4. How to Handle Context Window Limits?

**Question**: What if files are too large for Agent SDK context window?

**Research**:

**Context Limits**:

- Claude Sonnet 4.5: 200K tokens input
- Typical source file: 100-10,000 tokens
- Chunk of 100 files: ~1-100K tokens
- Usually fine, but edge cases exist (e.g., large generated files)

**Strategies**:

#### A. Manual File Splitting

- **Approach**: Pre-process large files, split into smaller segments
- **Pros**: Guaranteed to fit
- **Cons**: Complex, may split semantic units, added latency

#### B. Let Agent SDK Handle It

- **Approach**: Trust Agent SDK to manage context (chunking, summarization)
- **Pros**: Simple, leverages SDK features
- **Cons**: May fail for truly large files

#### C. Multi-Tiered Fallback

1. Try full file(s)
2. If fails, split into smaller chunks
3. If still fails, summarize or skip

**Decision**: **Let Agent SDK Handle It (Approach B), Monitor for Issues**

**Rationale** (per user guidance):
> "Let's not worry about manually splitting files unless it becomes a problem. Let's prioritize simplicity"

1. **Simplicity first**: Avoid premature optimization
2. **Trust SDK**: Agent SDK likely has internal handling
3. **Observable**: Track failures, add splitting only if needed
4. **Metrics**: Monitor `context_overflow_errors` metric

**Safeguards**:

- Track token estimates per chunk
- Log warnings for files >50K tokens
- Add `--max-file-size` flag for manual limits
- Implement splitting in Phase 3 if metrics show it's needed

---

### 5. How to Manage Authentication?

**Question**: Should we support multiple auth methods? Which should be primary?

**Research**:

**Authentication Methods**:

#### Vertex AI (Google Cloud)

- **Use Case**: Production deployments in GCP
- **Pros**: No API key management, integrates with IAM, audit logs
- **Cons**: Requires GCP setup, more complex locally

#### API Key (Direct Anthropic)

- **Use Case**: Development, testing, non-GCP environments
- **Pros**: Simple, works anywhere, easy to rotate
- **Cons**: Key management burden, no centralized audit logs

**Decision**: **Support Both, Vertex AI Primary**

**Rationale** (per user requirement):
> "we will be using Vertex AI authentication. however, we should support API keys as well via the config."

1. **Production**: Vertex AI for security and compliance
2. **Development**: API key for quick local iteration
3. **Flexibility**: Teams can choose based on their infrastructure
4. **Fallback**: API key as backup if Vertex AI unavailable

**Implementation**:

```python
class AuthConfig(BaseModel):
    auth_method: Literal["vertex_ai", "api_key"] = "vertex_ai"
    # Vertex AI fields
    vertex_project_id: Optional[str] = None
    vertex_region: str = "us-central1"
    # API key fields
    api_key: Optional[str] = Field(default=None, repr=False)  # Hide in logs
```

---

### 6. Why YAML Templates for Prompts?

**Question**: Should prompts be hardcoded or externalized? What format?

**Research**:

**Options**:

#### A. Hardcoded in Python

- **Pros**: Simple, type-safe, versioned with code
- **Cons**: Requires code changes to tweak prompts, not accessible to non-developers

#### B. Plain Text Files

- **Pros**: Simple, easy to edit
- **Cons**: No structure, no variable definitions, no validation

#### C. JSON Templates

- **Pros**: Structured, parseable
- **Cons**: Poor for multi-line strings, no templating

#### D. YAML + Jinja2

- **Pros**: Human-readable, great for multi-line text, powerful templating, metadata support
- **Cons**: Two technologies to learn (YAML + Jinja)

**Decision**: **YAML + Jinja2 (Approach D)**

**Rationale** (per user requirement):
> "Ideally (according to best code practices), we hard-code as few things as possible. This _includes_ system prompts. I'd prefer for prompts used for agents to be Jinja-templated strings. Maybe stored as yaml?"

1. **Separation of Concerns**: Prompts are content, not code
2. **Accessibility**: Non-developers can improve prompts
3. **Experimentation**: A/B test prompts without code changes
4. **Documentation**: Metadata and variable definitions in same file
5. **Type Safety**: Pydantic models for template structure

**Template Structure**:

```yaml
metadata:
  name: entity_extraction
  version: "1.0.0"
  description: "Main extraction prompt"

variables:
  file_paths:
    type: list[Path]
    required: true
    description: "Files to extract from"
    example: ["/data/service.yaml"]

system_prompt: |
  Extract entities from:
  {% for path in file_paths %}
  - {{ path }}
  {% endfor %}
```

**Auto-Documentation**:

- Generate markdown docs from templates
- CLI command: `extractor prompt docs --output ./docs/prompts/`
- Discover available variables via introspection

---

### 7. Architecture: Clean Boundaries for Testing & Reliability

**Question**: How do we structure components to enable testing, retries, and error handling?

**Research**:

**Problem**: LLM interactions are:

- **Non-deterministic**: Same input may yield different outputs
- **Unreliable**: Rate limits, timeouts, transient errors
- **Expensive**: Each call costs money
- **Difficult to test**: Can't call real LLM in unit tests

**Solution**: **Protocol Boundaries with Strategy Pattern**

#### Key Boundaries

##### 1. LLM Query Interface Boundary

**Interface**:

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    model: str
    max_tokens: int
    temperature: float

@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str

class LLMClient(Protocol):
    """Abstract interface for LLM interactions."""

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Send query to LLM and return response."""
        ...
```

**Benefits**:

- ✅ **Transparent Retries**: Wrap with retry decorator
- ✅ **Circuit Breaker**: Detect/handle rate limits
- ✅ **Cost Tracking**: Log tokens per request
- ✅ **Testing**: Mock implementation for tests
- ✅ **Caching**: Add caching layer transparently
- ✅ **Rate Limiting**: Throttle requests

**Implementations**:

```python
class AnthropicLLMClient:
    """Production implementation using Anthropic API."""
    async def query(self, request: LLMRequest) -> LLMResponse:
        # Real API call with error handling
        ...

class MockLLMClient:
    """Test implementation with canned responses."""
    def __init__(self, responses: dict[str, str]):
        self.responses = responses

    async def query(self, request: LLMRequest) -> LLMResponse:
        # Return pre-defined response based on request
        return self.responses.get(request.user_prompt[:50], default_response)

class RetryingLLMClient:
    """Decorator that adds retry logic."""
    def __init__(self, inner: LLMClient, max_retries: int = 3):
        self.inner = inner
        self.max_retries = max_retries

    async def query(self, request: LLMRequest) -> LLMResponse:
        for attempt in range(self.max_retries):
            try:
                return await self.inner.query(request)
            except RateLimitError:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        raise MaxRetriesExceeded()
```

##### 2. File System Boundary

**Interface**:

```python
class FileSystem(Protocol):
    """Abstract interface for file operations."""

    def read_file(self, path: Path) -> str:
        """Read file contents."""
        ...

    def write_file(self, path: Path, content: str) -> None:
        """Write file contents."""
        ...

    def list_files(self, directory: Path, pattern: str) -> list[Path]:
        """List files matching pattern."""
        ...

# Production implementation
class DiskFileSystem:
    def read_file(self, path: Path) -> str:
        return path.read_text()
    # ...

# Test implementation
class InMemoryFileSystem:
    def __init__(self):
        self.files: dict[Path, str] = {}

    def read_file(self, path: Path) -> str:
        return self.files[path]
    # ...
```

**Benefits**:

- ✅ Test without disk I/O
- ✅ Parallel tests (no shared filesystem state)
- ✅ Fast test execution

##### 3. Checkpoint Persistence Boundary

**Interface**:

```python
class CheckpointStore(Protocol):
    """Abstract interface for checkpoint persistence."""

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint."""
        ...

    def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load checkpoint."""
        ...

    def find_latest(self) -> Checkpoint | None:
        """Find most recent checkpoint."""
        ...
```

**Benefits**:

- ✅ Test checkpoint logic without disk writes
- ✅ Swap implementations (disk, S3, database)

##### 4. Validation Boundary

**Pure Functions** (no I/O, fully deterministic):

```python
def validate_entity(entity: dict, required_fields: list[str]) -> list[ValidationError]:
    """Validate entity structure. Pure function."""
    errors = []

    for field in required_fields:
        if field not in entity:
            errors.append(ValidationError(f"Missing required field: {field}"))

    if not is_valid_urn(entity.get("@id", "")):
        errors.append(ValidationError("Invalid URN format"))

    return errors
```

**Benefits**:

- ✅ Easy to test (no mocks needed)
- ✅ Fast execution
- ✅ Composable

#### Dependency Injection

**Orchestrator Design**:

```python
class ExtractionOrchestrator:
    """Main workflow coordinator with injected dependencies."""

    def __init__(
        self,
        llm_client: LLMClient,
        file_system: FileSystem,
        checkpoint_store: CheckpointStore,
        chunking_strategy: ChunkingStrategy,
        deduplication_strategy: DeduplicationStrategy,
    ):
        self.llm = llm_client
        self.fs = file_system
        self.checkpoints = checkpoint_store
        self.chunker = chunking_strategy
        self.deduper = deduplication_strategy

    async def extract(self, config: ExtractionConfig) -> ExtractionResult:
        # All dependencies injected, easy to test
        ...
```

**Test Example**:

```python
async def test_extraction_with_mocks():
    # Arrange: Create mock dependencies
    llm = MockLLMClient(responses={
        "Extract entities": LLMResponse(content='{"entities": [...]}', ...)
    })
    fs = InMemoryFileSystem()
    fs.files[Path("/data/service.yaml")] = "name: myapp"

    checkpoints = InMemoryCheckpointStore()
    chunker = HybridChunkingStrategy()
    deduper = URNBasedDeduplication()

    orchestrator = ExtractionOrchestrator(llm, fs, checkpoints, chunker, deduper)

    # Act: Run extraction
    result = await orchestrator.extract(ExtractionConfig(data_dir=Path("/data")))

    # Assert: Verify behavior
    assert result.entity_count > 0
    assert len(result.validation_errors) == 0
```

---

### 8. Test-Driven Development Strategy

**Question**: How do we ensure high-quality, testable code from day one?

**Research**:

**TDD Principles**:

1. **Red**: Write failing test first
2. **Green**: Implement minimal code to pass
3. **Refactor**: Clean up while tests stay green

**Application to KG Extraction**:

#### Phase 1: Unit Tests First

**Example: Entity Validation**

```python
# tests/test_validation.py (write FIRST)
def test_validate_entity_missing_required_field():
    entity = {"@id": "urn:service:foo", "@type": "Service"}
    errors = validate_entity(entity, required_fields=["@id", "@type", "name"])

    assert len(errors) == 1
    assert "name" in errors[0].message

def test_validate_entity_invalid_urn():
    entity = {"@id": "not-a-urn", "@type": "Service", "name": "Foo"}
    errors = validate_entity(entity, required_fields=["@id", "@type", "name"])

    assert any("URN" in e.message for e in errors)

# kg_extractor/validation.py (implement AFTER test)
def validate_entity(entity: dict, required_fields: list[str]) -> list[ValidationError]:
    errors = []

    for field in required_fields:
        if field not in entity:
            errors.append(ValidationError(f"Missing required field: {field}"))

    if not entity.get("@id", "").startswith("urn:"):
        errors.append(ValidationError("Invalid URN format"))

    return errors
```

#### Phase 2: Integration Tests with Mocks

**Example: Extraction Agent**

```python
# tests/test_extraction_agent.py
async def test_extraction_agent_with_mock_llm():
    # Arrange: Mock LLM client
    mock_llm = MockLLMClient(responses={
        "Extract entities from": LLMResponse(
            content='{"entities": [{"@id": "urn:service:foo", "@type": "Service", "name": "Foo"}]}',
            tokens_used=1000,
        )
    })

    agent = ExtractionAgent(llm_client=mock_llm, prompt_loader=...)

    # Act: Extract from files
    result = await agent.extract(file_paths=[Path("/data/service.yaml")])

    # Assert: Verify extraction
    assert result["metadata"]["entity_count"] == 1
    assert result["entities"][0]["name"] == "Foo"
```

#### Phase 3: End-to-End Tests

**Example: Full Workflow**

```python
# tests/integration/test_e2e.py
async def test_full_extraction_workflow():
    # Arrange: Set up test data
    test_data_dir = Path("tests/fixtures/data")

    # Use real Agent SDK but with small dataset
    config = ExtractionConfig(
        data_dir=test_data_dir,
        auth=AuthConfig(auth_method="api_key", api_key=os.getenv("TEST_API_KEY")),
    )

    orchestrator = create_orchestrator(config)

    # Act: Run extraction
    result = await orchestrator.extract(config)

    # Assert: Verify results
    assert result.entity_count >= 10  # Expected minimum
    assert result.validation_pass_rate >= 0.95

    # Verify JSON-LD is valid
    graph = load_jsonld(config.output_file)
    assert len(graph["@graph"]) == result.entity_count
```

#### Phase 4: Property-Based Tests

**Example: Deduplication**

```python
from hypothesis import given, strategies as st

@given(st.lists(st.dictionaries(
    keys=st.sampled_from(["@id", "@type", "name"]),
    values=st.text(),
)))
def test_deduplication_idempotent(entities):
    """Deduplicating twice should produce same result as once."""
    deduper = URNBasedDeduplication()

    once = await deduper.deduplicate(entities, [])
    twice = await deduper.deduplicate(once, [])

    assert once == twice

@given(st.lists(st.dictionaries(...)))
def test_deduplication_preserves_required_fields(entities):
    """All entities should still have required fields after dedup."""
    deduper = URNBasedDeduplication()

    # Assume all input entities are valid
    for e in entities:
        e.update({"@id": f"urn:test:{uuid.uuid4()}", "@type": "Test", "name": "Test"})

    result = await deduper.deduplicate(entities, [])

    for entity in result:
        assert "@id" in entity
        assert "@type" in entity
        assert "name" in entity
```

**TDD Workflow for Each Feature**:

1. **Write Contract** (interface/protocol definition)
2. **Write Test** (using mock implementations)
3. **Implement** (minimal code to pass test)
4. **Refactor** (improve design, tests stay green)
5. **Integration Test** (connect real components)

**Benefits**:

- ✅ **Confidence**: Tests prove code works
- ✅ **Documentation**: Tests show how to use APIs
- ✅ **Refactoring Safety**: Tests catch regressions
- ✅ **Design Quality**: Testable code is well-designed code

---

## Decisions Summary

| Question | Decision | Rationale |
|----------|----------|-----------|
| SDK vs CLI? | Agent SDK | Programmatic control, testability, retry logic |
| Chunking strategy? | Hybrid directory-aware size-based | Semantic coherence + balanced sizes |
| Deduplication? | URN-based (Phase 1), hybrid (Phase 4) | Simple first, extensible design |
| Context limits? | Let SDK handle, monitor | Avoid premature optimization |
| Authentication? | Vertex AI primary, API key fallback | Production + dev flexibility |
| Prompt format? | YAML + Jinja2 | Human-readable, templating, metadata |
| Component boundaries? | Protocol interfaces with DI | Testing, retries, swappable implementations |
| Development approach? | Test-Driven Development | Quality, confidence, maintainability |

## Open Questions

1. **Parallel Processing**: Should we process chunks in parallel? (Phase 4 decision)
2. **Schema Integration**: How deeply should schemas guide extraction? (Experiment in Phase 2)
3. **Incremental Extraction**: How to detect changed files and re-extract only those? (Phase 4 feature)
4. **Cost Optimization**: What's the cost/quality tradeoff with different models? (Monitor in production)

## References

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/python.md)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Test-Driven Development by Example (Kent Beck)](https://www.oreilly.com/library/view/test-driven-development/0321146530/)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- Previous iteration: `/home/jsell/code/kartograph-kg-iteration/`
