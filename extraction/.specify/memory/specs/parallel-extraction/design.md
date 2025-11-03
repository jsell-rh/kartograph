# Parallel Chunk Processing - Design Document

**Status:** In Progress
**GitHub Issue:** #15
**Jira Issue:** AIHCM-72
**Branch:** feat/parallel-extraction
**Author:** AI Assistant (Claude)
**Date:** 2025-10-24

## Overview

Enable parallel chunk processing in KG extraction to achieve 3x speedup on large datasets while maintaining robust rate limit handling for Vertex AI and Anthropic APIs.

## Problem Statement

Current extraction processes chunks sequentially (one at a time):

- Location: `extraction/kg_extractor/orchestrator.py:308`
- While loop processes chunks one by one
- Large datasets (1000+ files) take hours instead of minutes
- No utilization of available API concurrency

## Goals

### Primary

- **3x speedup** on large datasets (1000+ files)
- **Transparent rate limiting** - handled at LLM boundary
- **No race conditions** - thread-safe shared state
- **Graceful degradation** - handle 429 errors elegantly

### Secondary

- Configurable via `--workers N` flag (default: 3)
- Maintain checkpoint integrity with concurrent execution
- Memory-efficient (no 3x memory usage)

## Architecture

### Boundary-Based Design

The system follows a clean architectural boundary where rate limiting is **transparent** to callers:

```
┌─────────────────────────────────────────────────────┐
│  Orchestrator (caller)                              │
│  - Processes chunks in parallel with asyncio.gather │
│  - NO rate limit logic here                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  ExtractionAgent (domain logic)                     │
│  - Renders prompts, validates entities              │
│  - NO rate limit logic here                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
╔══════════════════════════════════════════════════════╗
║  AgentClient - THE BOUNDARY                          ║
║  Protocol: LLMClient                                 ║
║                                                      ║
║  ✓ Semaphore (limit concurrent API calls)           ║
║  ✓ Global backoff (shared across instances)         ║
║  ✓ 429 detection and handling                       ║
║  ✓ Exponential backoff (rate-aware)                 ║
║                                                      ║
║  TRANSPARENT TO CALLERS ↑                            ║
╚══════════════════┬═══════════════════════════════════╝
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Claude Agent SDK                                   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Anthropic/Vertex AI API                            │
│  (429 errors originate here)                        │
└─────────────────────────────────────────────────────┘
```

### Key Principle

**Rate limiting is encapsulated at the LLM client boundary** - no implementation details leak to callers. This maintains clean separation of concerns and makes the system easy to reason about.

## Implementation Phases

### Phase A: Rate Limiting at LLM Boundary (CURRENT)

**Goal:** Add transparent rate limiting to `AgentClient` without changing callers.

**File:** `kg_extractor/llm/agent_client.py`

**Changes:**

1. **Class-level shared state** (coordinates ALL instances):

   ```python
   class AgentClient:
       # Shared across all instances for global coordination
       _rate_limit_semaphore: asyncio.Semaphore | None = None
       _rate_limited_until: float | None = None
       _semaphore_lock = asyncio.Lock()

       def __init__(self, ..., max_concurrent: int = 3):
           self.max_concurrent = max_concurrent
           # Lazy-init shared semaphore
   ```

2. **Semaphore acquisition** in `_send_and_receive()`:

   ```python
   async def _send_and_receive(self, prompt, event_callback=None):
       # Wait if globally rate limited
       await self._wait_for_rate_limit_clearance()

       # Acquire semaphore (limit concurrent API calls)
       async with await self._get_semaphore():
           try:
               # Existing send/receive logic...
               return response
           except RateLimitError as e:
               # Set global backoff
               await self._set_global_backoff(...)
               raise
   ```

3. **Helper methods**:
   - `_get_semaphore()` - lazy-init shared semaphore
   - `_wait_for_rate_limit_clearance()` - wait if globally rate limited
   - `_detect_rate_limit_error()` - check if exception is 429
   - `_set_global_backoff()` - set global backoff timestamp
   - `_calculate_backoff()` - rate-aware backoff calculation

4. **Enhanced retry logic** (lines 506-524, 575-641):
   - Detect 429 errors specifically
   - Rate limit backoff: 5s → 10s → 20s → 40s
   - Other error backoff: 2s → 4s → 8s

**Success Criteria:**

- ✅ Multiple AgentClient instances coordinate via shared state
- ✅ 429 errors pause ALL instances (global backoff)
- ✅ Semaphore limits concurrent API calls
- ✅ Transparent to callers (no API changes)

---

### Phase B: Parallel Orchestration

**Goal:** Enable parallel chunk processing using asyncio.gather.

**File:** `kg_extractor/orchestrator.py`

**Changes:**

1. **Replace sequential loop** (line 308):

   ```python
   # OLD: Sequential
   while chunk_index < len(chunks_to_process):
       chunk = chunks_to_process[chunk_index]
       result = await self.extraction_agent.extract(...)
       chunk_index += 1

   # NEW: Parallel batches
   batch_size = self.config.workers  # From --workers flag
   for batch_start in range(0, len(chunks), batch_size):
       batch = chunks[batch_start:batch_start + batch_size]

       # Process batch in parallel
       tasks = [
           self._process_chunk(chunk)
           for chunk in batch
       ]
       results = await asyncio.gather(*tasks, return_exceptions=True)

       # Handle results, update shared state with lock
       for result in results:
           if isinstance(result, Exception):
               # Handle error
           else:
               # Collect entities, update metrics
   ```

2. **Extract `_process_chunk()` method**:

   ```python
   async def _process_chunk(self, chunk: Chunk) -> ExtractionResult:
       """Process a single chunk (for parallel execution)."""
       # Existing chunk processing logic from while loop
       # AgentClient handles rate limiting transparently
   ```

3. **Thread-safe shared state**:

   ```python
   # Add lock for entity collection
   self._entities_lock = asyncio.Lock()

   async with self._entities_lock:
       all_entities.extend(result.entities)
       all_validation_errors.extend(result.validation_errors)
   ```

4. **Checkpoint strategy**:
   - Save checkpoint after each BATCH completes (not per chunk)
   - Reduces checkpoint overhead with parallel execution
   - Still maintains recoverability

**Success Criteria:**

- ✅ Process N chunks concurrently (N = --workers)
- ✅ No race conditions in entity collection
- ✅ Checkpoint integrity maintained
- ✅ Rate limiting works transparently

---

### Phase C: CLI and Configuration

**Goal:** Add --workers flag and configuration.

**Files:**

- `kg_extractor/config.py` - Add workers config
- `extraction/extractor.py` - Add CLI flag

**Changes:**

1. **Config model** (`config.py`):

   ```python
   class ExtractionConfig(BaseSettings):
       # Parallel execution
       workers: int = Field(
           default=3,
           ge=1,
           le=20,
           description="Number of concurrent workers for chunk processing"
       )
   ```

2. **CLI flag** (`extractor.py`):

   ```python
   parser.add_argument(
       "--workers",
       type=int,
       default=3,
       help="Number of concurrent workers (default: 3, max: 20)"
   )
   ```

3. **Pass to AgentClient**:

   ```python
   llm_client = AgentClient(
       auth_config=config.auth,
       model=config.llm.model,
       max_concurrent=config.workers,  # NEW
   )
   ```

**Success Criteria:**

- ✅ `--workers N` flag works
- ✅ Environment variable support: `EXTRACTOR_WORKERS=5`
- ✅ Validation: 1 ≤ workers ≤ 20

---

## Rate Limit Handling Strategy

### Detection

Detect 429 errors from multiple sources:

1. Agent SDK exceptions containing "429" or "rate_limit"
2. Response text containing error patterns
3. Exception messages with "quota" or "throttle"

```python
def _detect_rate_limit_error(self, error: Exception) -> bool:
    """Detect if error is a rate limit (429) error."""
    error_str = str(error).lower()
    patterns = [
        "429",
        "rate limit",
        "rate_limit",
        "quota exceeded",
        "too many requests",
        "throttle",
    ]
    return any(pattern in error_str for pattern in patterns)
```

### Backoff Strategy

**Rate Limit Errors (429):**

- Attempt 1: Wait 5 seconds
- Attempt 2: Wait 10 seconds
- Attempt 3: Wait 20 seconds
- Fail after 3 attempts

**Other Errors:**

- Attempt 1: Wait 2 seconds
- Attempt 2: Wait 4 seconds
- Attempt 3: Wait 8 seconds
- Fail after 3 attempts

### Global Coordination

When ANY AgentClient instance hits a 429:

1. Set `_rate_limited_until` timestamp (shared class variable)
2. ALL instances check this before making API calls
3. ALL instances wait until timestamp expires
4. First instance to succeed clears the timestamp

## Testing Strategy

### Phase A Testing

1. **Unit tests** - Verify semaphore behavior, backoff calculation
2. **Integration test** - Mock 429 errors, verify global backoff
3. **Manual test** - Trigger real 429, observe coordination

### Phase B Testing

1. **Synthetic dataset** - 100 small files for quick iteration
2. **Parallel correctness** - Verify no lost entities, no duplicates
3. **Race condition test** - Run with 10 workers, verify integrity

### Phase C Testing

1. **CLI test** - Verify `--workers` flag parsing
2. **Benchmark** - Measure speedup: 1 worker vs 3 workers vs 5 workers
3. **Full-scale test** - 1000+ files, target 3x speedup

## Success Metrics

### Phase A

- ✅ Global backoff works (one 429 pauses all instances)
- ✅ Semaphore limits concurrent calls
- ✅ No changes required to orchestrator or extraction agent

### Phase B

- ✅ 2-3x speedup with 3 workers on 100-file dataset
- ✅ No race conditions (entity counts match sequential)
- ✅ Checkpoint integrity maintained

### Phase C

- ✅ 3x speedup on 1000+ file dataset
- ✅ Memory usage < 2x sequential
- ✅ Graceful handling of 429 errors under load

## Risks and Mitigations

### Risk: API Rate Limits

**Impact:** High - Can block entire extraction

**Mitigation:**

- Conservative default (3 workers)
- Aggressive backoff on 429 (5s → 10s → 20s)
- Global coordination (one 429 pauses all)
- Configurable via `--workers` for tuning

### Risk: Race Conditions

**Impact:** High - Data corruption, lost entities

**Mitigation:**

- Locks on shared state (entity list, metrics)
- Batch-based checkpoints (atomic operations)
- Integration tests with concurrent access

### Risk: Memory Usage

**Impact:** Medium - OOM on large datasets

**Mitigation:**

- Stream entities to disk (future enhancement)
- Limit workers to 20 max
- Monitor memory, warn if high

### Risk: Vertex AI Quota Differences

**Impact:** Medium - Different limits than Anthropic API

**Mitigation:**

- Agnostic 429 detection (works for both)
- Conservative default (3 workers)
- User can tune based on their quota

## Future Enhancements

### Priority 1 (Next Sprint)

- **Adaptive concurrency** - Reduce workers if frequent 429s
- **Memory monitoring** - Warn/throttle if memory high

### Priority 2 (Future)

- **Token bucket** - Proactive rate limiting
- **Per-chunk memory** - Stream to disk for very large datasets
- **Metrics dashboard** - Visualize parallelization efficiency

## References

- GitHub Issue: <https://github.com/jsell-rh/kartograph/issues/15>
- Jira Issue: <https://issues.redhat.com/browse/AIHCM-72>
- Original Spec: `.specify/memory/specs/feat-kg-extraction-production/001/tasks.md` (TASK-401)
- Agent SDK Docs: <https://docs.claude.com/en/api/agent-sdk/>
- Current Implementation: `extraction/kg_extractor/orchestrator.py`
