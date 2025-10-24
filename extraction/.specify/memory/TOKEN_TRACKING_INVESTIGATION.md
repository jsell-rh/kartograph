# Token Tracking Investigation

## Problem

User reported incorrect token counts after processing one chunk:

- **Input Tokens: 18** (way too low!)
- **Output Tokens: 9638** (reasonable)

Expected: Input tokens should be 50,000+ for a full chunk (file contents + prompt + tool results)

## Root Cause Hypothesis

The Agent SDK makes **multiple API calls** during extraction:

1. Initial prompt → Agent decides to use Read tool → **API Call #1**
2. Read results → Agent processes, uses Grep → **API Call #2**
3. Grep results → Agent uses more tools → **API Call #3**
4. ... (many more tool calls) ...
5. Final → Agent submits results → **API Call #N**

Each API call has its own token usage. However, our code only captures usage from the FINAL ResultMessage:

```python
# In agent_client.py line 288-296
if isinstance(message, ResultMessage):
    self.last_usage = {
        "input_tokens": message.usage.get("input_tokens", 0),  # ← Only final call!
        "output_tokens": message.usage.get("output_tokens", 0), # ← Only final call!
    }
    break  # ← Exit after first ResultMessage
```

**Theory**: `message.usage` only contains usage for the FINAL API call (18 tokens), not cumulative usage across ALL calls (50,000+ tokens).

## Evidence

1. **Input tokens way too low**: 18 is plausible for a small final prompt, but not for all file contents
2. **Output tokens reasonable**: 9638 is plausible for the final JSON response
3. **Naming convention**: `message.total_cost_usd` is named "total" suggesting cumulative tracking
4. **Single ResultMessage**: We only receive ONE ResultMessage at the end, containing only final call usage

## ResultMessage Structure (from SDK source)

Found in `.venv/lib/python3.13/site-packages/claude_agent_sdk/types.py`:

```python
@dataclass
class ResultMessage:
    """Result message with cost and usage information."""

    subtype: str
    duration_ms: int              # ← Cumulative duration
    duration_api_ms: int          # ← Cumulative API duration
    is_error: bool
    num_turns: int                # ← NUMBER OF API CALLS!
    session_id: str
    total_cost_usd: float | None  # ← CUMULATIVE cost (note "total")
    usage: dict[str, Any] | None  # ← Usage dict (but for what?)
    result: str | None
```

**Key Observations**:

1. `total_cost_usd` is named "total" → **cumulative across all turns**
2. `num_turns` tells us how many API calls were made
3. `duration_ms` and `duration_api_ms` are likely cumulative (match naming of cost)
4. `usage` is NOT named "total_usage" → **probably only final turn!**

**Hypothesis Confirmed**: The `usage` dict likely only contains tokens for the final turn, not cumulative.

## Problem: No Cumulative Token Fields

The ResultMessage does NOT appear to have:

- ❌ `total_input_tokens`
- ❌ `cumulative_input_tokens`
- ❌ `conversation_input_tokens`

We only have:

- ✅ `total_cost_usd` (cumulative)
- ❓ `usage["input_tokens"]` (probably final turn only)

## Possible Solutions

### Option 1: Calculate from total_cost_usd

Since we have cumulative cost, we could reverse-calculate tokens:

```python
# Model pricing for claude-sonnet-4-5@20250929
INPUT_PRICE = 3.00 / 1_000_000   # $3 per million input tokens
OUTPUT_PRICE = 15.00 / 1_000_000 # $15 per million output tokens

# But we can't separate input vs output tokens from just total cost!
total_tokens = total_cost_usd / SOME_AVERAGE_PRICE  # ❌ Inaccurate
```

**Problem**: We can't distinguish input vs output tokens from total cost alone.

### Option 2: Track from StreamEvents

Usage might be provided incrementally through StreamEvent objects. Need to check if StreamEvents contain usage data.

### Option 3: Accept Limitation

Show only:

- ✅ Total cost (accurate, cumulative)
- ✅ Duration (accurate, cumulative)
- ✅ Number of turns (accurate)
- ⚠️  Tokens for final turn only (with warning)

OR just hide token counts and show cost only.

## Debug Logging Added

I've added comprehensive debug logging to dump ALL ResultMessage attributes:

```python
# Logs all non-private attributes
for attr in dir(message):
    if not attr.startswith("_"):
        value = getattr(message, attr)
        if not callable(value):
            logger.debug(f"  {attr}: {value}")
```

## Next Steps

1. **Run extraction with DEBUG logging**:

   ```bash
   python3 extractor.py \
     --data-dir /path/to/test/data \
     --output-file test_output.jsonld \
     --log-level DEBUG \
     --log-file debug.log
   ```

2. **Search debug.log for "ResultMessage attributes"** to see all available fields

3. **Look for cumulative token fields** like:
   - `total_input_tokens`
   - `cumulative_input_tokens`
   - `conversation_input_tokens`
   - Or similar naming

4. **Update agent_client.py** to use the correct cumulative fields:

   ```python
   self.last_usage = {
       "input_tokens": message.CORRECT_CUMULATIVE_FIELD_HERE,
       "output_tokens": message.CORRECT_CUMULATIVE_FIELD_HERE,
   }
   ```

## Alternative Scenarios

If ResultMessage doesn't have cumulative fields, we might need to:

1. **Track usage from multiple messages**: Accumulate usage across multiple ResultMessage objects (though we likely only get one)

2. **Track from StreamEvents**: Usage might be provided incrementally through StreamEvent objects

3. **Use conversation history**: Access a separate conversation/history object that tracks cumulative usage

## Commits

- `3e29ea6`: Added basic debug logging for message.usage
- `db6a038`: Added comprehensive logging for all ResultMessage attributes
- `c3f26e0`: Documented investigation findings

## ✅ SOLUTION FOUND

After reading the official Agent SDK cost tracking docs:
<https://docs.claude.com/en/api/agent-sdk/cost-tracking.md>

**The `usage` dict IS cumulative, but has MULTIPLE input token fields that must be summed:**

```python
{
    "input_tokens": 18,                      # Base input tokens (what we were reading)
    "cache_creation_input_tokens": 45000,   # Tokens to CREATE cache ← WE WERE MISSING THIS!
    "cache_read_input_tokens": 5000,        # Tokens READ from cache ← AND THIS!
    "output_tokens": 9638                    # Output tokens
}
```

**Root Cause**: We were only reading `usage["input_tokens"]` (18), completely missing the cache-related tokens (50,000+)!

The Agent SDK uses **prompt caching** for efficiency - reusing file contents and prompts across API turns. When caching is active, most input tokens appear in `cache_creation_input_tokens` or `cache_read_input_tokens`, NOT in the base `input_tokens` field.

### Fixed Implementation

```python
# Correct: Sum ALL input token types for true cumulative count
total_input_tokens = (
    message.usage.get("input_tokens", 0) +
    message.usage.get("cache_creation_input_tokens", 0) +
    message.usage.get("cache_read_input_tokens", 0)
)

self.last_usage = {
    "input_tokens": total_input_tokens,  # Now correct!
    "output_tokens": message.usage.get("output_tokens", 0),
    "total_cost_usd": message.total_cost_usd,
}
```

This correctly captures the TRUE cumulative input token count across all API turns, including cached tokens.
