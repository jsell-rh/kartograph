# MCP Tool Issue - Trace Analysis (RESOLVED)

## TL;DR - The Real Bug

**Line 260 was checking:**

```python
elif current_tool_name == "submit_extraction_results":
```

**But the actual tool name is:**

```
"mcp__extraction__submit_extraction_results"
```

**So the condition NEVER matched!** Fixed by checking:

```python
elif "submit_extraction_results" in current_tool_name:
```

---

## Original Analysis (Partially Incorrect)

## Evidence from Logs

The log shows:

```
✓ Extraction complete! I've successfully extracted and submitted **23 entities** from 4 YAML files.
```

This message comes from `extraction_mcp_server.py:127` - the MCP server's confirmation.
**Conclusion: The tool IS being called successfully.**

Then we see:

```
MCP tool not used, falling back to JSON parsing
```

This comes from `agent_client.py:415` - the extraction method.
**Conclusion: `self._mcp_result` is None**

## Code Flow Trace

### In `_send_and_receive()` (lines 148-299)

```python
Line 148: mcp_result = None  # Declare outside loop
Line 149: async for message in self.client.receive_response():
    ...
    Line 185: if event_type == "content_block_start":
        Line 187: if content.get("type") == "tool_use":
            Line 188: tool_name = content.get("name", "unknown")
            Line 189: current_tool_name = tool_name
            Line 190: current_tool_input = ""  # ← PROBLEM: Reset to empty
            Line 191: tool_input = content.get("input", {})  # ← Got the input!
            # BUT WE DON'T USE IT!

    Line 225: elif event_type == "content_block_stop":
        Line 227: if current_tool_input:  # ← Empty string is falsy!
            # This block NEVER RUNS because current_tool_input = ""
            Line 248: elif current_tool_name == "submit_extraction_results":
                Line 249: mcp_result = tool_input  # Never executed

Line 278: if mcp_result:  # Still None!
    Line 279: self._mcp_result = mcp_result
```

## The Bug

1. `content_block_start` provides `tool_input = content.get("input", {})`
2. But we IGNORE it and set `current_tool_input = ""`
3. We expect deltas to populate `current_tool_input`
4. **MCP tools don't send deltas** - they provide input immediately
5. `content_block_stop` checks `if current_tool_input:` - it's empty!
6. Result never gets captured
7. `mcp_result` stays None
8. Fallback JSON parsing is used

## Why Standard Tools (Read) Work

Standard tools like Read likely send their input via `input_json_delta` events:

- `content_block_start`: input is empty
- `content_block_delta` (multiple): Sends partial JSON
- Accumulated into `current_tool_input`
- `content_block_stop`: Parses accumulated string

## Why MCP Tools Don't Work

MCP tools provide full input immediately:

- `content_block_start`: input is a complete dict
- NO deltas sent
- `current_tool_input` never populated
- `content_block_stop`: Nothing to parse

## The Fix

We need to handle BOTH cases:

```python
if event_type == "content_block_start":
    content = event_data.get("content_block", {})
    if content.get("type") == "tool_use":
        tool_name = content.get("name", "unknown")
        current_tool_name = tool_name
        tool_input = content.get("input", {})

        # NEW: Check if input is available immediately
        if tool_input:
            # MCP tools provide input immediately - serialize it
            current_tool_input = json.dumps(tool_input)
        else:
            # Standard tools will send via deltas
            current_tool_input = ""
```

This way:

- MCP tools: `current_tool_input` contains serialized JSON immediately
- Standard tools: `current_tool_input` accumulates from deltas
- Both cases: `content_block_stop` can parse the JSON

## Verification Needed

We need to verify:

1. Does `content.get("input")` actually contain data for MCP tools?
2. Or is there a different event type for MCP tool results?

The fix assumes #1 is true based on standard Anthropic API behavior where tool
inputs CAN be provided immediately in the tool_use content block.
