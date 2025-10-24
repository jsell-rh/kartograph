#!/usr/bin/env python3
"""Test script to inspect Agent SDK event structure for MCP tools.

This will help us understand exactly how tool inputs are provided in the event stream.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add extraction to path
sys.path.insert(0, str(Path(__file__).parent / "extraction"))

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import ResultMessage, StreamEvent


async def test_mcp_tool_events():
    """Test how MCP tool inputs are delivered in events."""
    print("=" * 80)
    print("Testing Agent SDK Event Structure for MCP Tools")
    print("=" * 80)

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    # Configure MCP server
    mcp_config = {
        "extraction": {
            "command": sys.executable,
            "args": ["-m", "kg_extractor.llm.extraction_mcp_server"],
        }
    }

    # Create client with MCP tool allowed
    options = ClaudeAgentOptions(
        allowed_tools=[
            "Read",
            "mcp__extraction__submit_extraction_results",
        ],
        permission_mode="acceptEdits",
        mcp_servers=mcp_config,
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()

    # Create a simple prompt that should trigger the MCP tool
    prompt = """
Please use the submit_extraction_results tool to submit these test entities:

```json
{
  "entities": [
    {
      "@id": "urn:TestEntity:test1",
      "@type": "TestEntity",
      "name": "Test Entity 1"
    }
  ],
  "metadata": {
    "entity_count": 1,
    "types_discovered": ["TestEntity"],
    "files_processed": 0
  }
}
```

Use the submit_extraction_results tool with the data above.
"""

    print("\nSending prompt...")
    await client.query(prompt)

    print("\nReceiving events...\n")

    # Track what we see
    events_seen = []
    tool_use_blocks = []
    current_tool = None
    current_input = ""

    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            print(f"\n[RESULT MESSAGE]")
            print(f"  Result: {message.result[:100]}...")
            break

        if isinstance(message, StreamEvent):
            event_data = message.event
            event_type = event_data.get("type", "unknown")
            events_seen.append(event_type)

            print(f"\n[EVENT: {event_type}]")

            # Detailed inspection for tool-related events
            if event_type == "content_block_start":
                content = event_data.get("content_block", {})
                if content.get("type") == "tool_use":
                    tool_name = content.get("name", "unknown")
                    tool_id = content.get("id", "unknown")
                    tool_input = content.get("input")

                    current_tool = tool_name
                    current_input = ""

                    print(f"  Tool Name: {tool_name}")
                    print(f"  Tool ID: {tool_id}")
                    print(f"  Input Field Present: {tool_input is not None}")

                    if tool_input is not None:
                        print(f"  Input Type: {type(tool_input)}")
                        print(
                            f"  Input Content: {json.dumps(tool_input, indent=2)[:200]}..."
                        )

                        tool_use_blocks.append(
                            {
                                "name": tool_name,
                                "id": tool_id,
                                "input": tool_input,
                                "source": "content_block_start",
                            }
                        )
                    else:
                        print(f"  Input: None (will come via deltas)")

            elif event_type == "content_block_delta":
                delta = event_data.get("delta", {})
                delta_type = delta.get("type", "unknown")

                print(f"  Delta Type: {delta_type}")

                if delta_type == "input_json_delta":
                    partial = delta.get("partial_json", "")
                    current_input += partial
                    print(f"  Partial JSON ({len(partial)} chars): {partial[:100]}...")

                elif delta_type == "text_delta":
                    text = delta.get("text", "")
                    print(f"  Text: {text[:100]}...")

            elif event_type == "content_block_stop":
                print(f"  Block stopped")
                if current_tool and current_input:
                    print(f"  Accumulated input for {current_tool}:")
                    print(f"    {current_input[:200]}...")

                    try:
                        parsed = json.loads(current_input)
                        tool_use_blocks.append(
                            {
                                "name": current_tool,
                                "input": parsed,
                                "source": "deltas",
                            }
                        )
                    except json.JSONDecodeError as e:
                        print(f"    Failed to parse: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nEvents seen ({len(events_seen)}):")
    from collections import Counter

    event_counts = Counter(events_seen)
    for event, count in event_counts.most_common():
        print(f"  {event}: {count}")

    print(f"\nTool use blocks captured ({len(tool_use_blocks)}):")
    for i, block in enumerate(tool_use_blocks):
        print(f"\n  Block {i + 1}:")
        print(f"    Name: {block['name']}")
        print(f"    Source: {block['source']}")
        print(
            f"    Input keys: {list(block['input'].keys()) if isinstance(block['input'], dict) else 'N/A'}"
        )
        if block["name"] == "submit_extraction_results":
            print(f"    Entities count: {len(block['input'].get('entities', []))}")

    # Key findings
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    mcp_blocks = [
        b for b in tool_use_blocks if "submit_extraction_results" in b["name"]
    ]
    if mcp_blocks:
        mcp_block = mcp_blocks[0]
        print(f"\n✓ MCP tool WAS called: {mcp_block['name']}")
        print(f"  Input source: {mcp_block['source']}")

        if mcp_block["source"] == "content_block_start":
            print(
                "  → Input provided IMMEDIATELY in content_block_start (no deltas needed)"
            )
            print("  → The fix IS CORRECT: we need to capture tool_input immediately")
        elif mcp_block["source"] == "deltas":
            print("  → Input provided via deltas (current code should work)")
            print("  → The fix may NOT be needed")
    else:
        print("\n✗ MCP tool was NOT called or not captured")

    print()


if __name__ == "__main__":
    asyncio.run(test_mcp_tool_events())
