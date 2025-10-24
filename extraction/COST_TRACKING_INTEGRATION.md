# Cost Tracking Integration Plan

## Problem

Current cost estimates are **rough guesses**:

- 4 chars/token (varies widely)
- 2000 token prompt overhead (could be 500-5000)
- 10% output ratio (highly variable)
- Fixed processing speeds (ignores network, retries, tool calls)

**Result**: Estimates could be off by 2-3x!

## Solution: Track Actuals & Learn

### Phase 1: Capture Actual Usage

We need to get actual token counts from the API response. For Claude Agent SDK:

```python
# In agent_client.py - capture usage from API response
# The Agent SDK should provide usage stats in the response

class AgentClient:
    def __init__(self):
        self.last_usage = None  # Store last API call usage

    async def extract_entities(self, ...):
        # After getting response
        response = await self.client.query(...)

        # Capture usage stats (need to find where SDK exposes this)
        # Might be in ResultMessage or separate usage message
        if hasattr(response, 'usage'):
            self.last_usage = {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
            }
```

### Phase 2: Track in Orchestrator

```python
# In orchestrator.py
from kg_extractor.cost_tracker import ActualCost, CostTracker

class ExtractionOrchestrator:
    def __init__(self, ...):
        self.cost_tracker = CostTracker()
        self.dry_run_estimate = None

    async def extract(self):
        # Store dry-run estimate if it was run
        start_time = time.time()

        # ... run extraction ...

        # Capture actuals
        duration = time.time() - start_time

        # Aggregate token usage across all chunks
        total_input_tokens = sum(chunk.usage['input_tokens'] for chunk in chunks)
        total_output_tokens = sum(chunk.usage['output_tokens'] for chunk in chunks)

        # Calculate cost
        pricing = MODEL_PRICING[model]
        actual_cost = (total_input_tokens / 1e6 * pricing['input'] +
                      total_output_tokens / 1e6 * pricing['output'])

        # Record actual
        actual = ActualCost(
            timestamp=datetime.now().isoformat(),
            total_files=len(all_files),
            total_chunks=len(chunks),
            total_size_bytes=sum(c.total_size_bytes for c in chunks),
            actual_input_tokens=total_input_tokens,
            actual_output_tokens=total_output_tokens,
            actual_cost_usd=actual_cost,
            actual_duration_seconds=duration,
            model=model,
            # Include estimates if dry-run was done
            estimated_input_tokens=self.dry_run_estimate.estimated_input_tokens if self.dry_run_estimate else None,
            estimated_output_tokens=self.dry_run_estimate.estimated_output_tokens if self.dry_run_estimate else None,
            estimated_cost_usd=self.dry_run_estimate.estimated_cost_usd if self.dry_run_estimate else None,
            estimated_duration_seconds=self.dry_run_estimate.estimated_duration_seconds if self.dry_run_estimate else None,
        )

        self.cost_tracker.record_run(actual)

        return result, actual
```

### Phase 3: Report at End

```python
# In extractor.py main()
result, actual_cost = await orchestrator.extract()

# Show comparison
if dry_run_estimate:
    cost_tracker.print_comparison(actual_cost)
else:
    # Just show actuals
    print(f"\nActual Cost: ${actual_cost.actual_cost_usd:.2f}")
    print(f"Actual Duration: {actual_cost.actual_duration_seconds / 60:.1f} minutes")
```

### Phase 4: Improve Estimates

```python
# In cost_estimator.py
class CostEstimator:
    def __init__(self, llm_config: LLMConfig):
        # Load learned parameters from history
        self.cost_tracker = CostTracker()
        learned = self.cost_tracker.get_average_metrics(model=llm_config.model)

        if learned.get('sample_size', 0) >= 5:
            # Use learned values if we have enough samples
            self.CHARS_PER_TOKEN = learned['avg_chars_per_token']
            self.OUTPUT_RATIO = learned['avg_output_ratio']
            self.TOKENS_PER_SECOND = learned['avg_tokens_per_second']
        else:
            # Fall back to defaults
            self.CHARS_PER_TOKEN = 4
            self.OUTPUT_RATIO = 0.1
            self.TOKENS_PER_SECOND = 500
```

## Implementation Priority

**Must Have:**

1. Capture actual usage from Agent SDK ← **CRITICAL, need to find where SDK exposes this**
2. Show actual cost at end of run
3. Store history (optional, nice to have)

**Nice to Have:**
4. Compare estimated vs actual if dry-run was used
5. Learn from history to improve estimates
6. CLI command to view cost history: `extractor costs show`

## Key Question

**Where does Agent SDK expose token usage?**

Need to check:

- `ResultMessage` - might have usage field
- Separate `UsageMessage` type?
- Metadata in response stream?
- Need to read Agent SDK docs or inspect response objects

This is the **critical blocker** for accurate cost tracking.
