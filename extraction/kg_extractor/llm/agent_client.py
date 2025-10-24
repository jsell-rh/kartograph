"""Agent SDK-based LLM client implementation.

Uses Claude Agent SDK with built-in tools for file access and multi-step reasoning.
This is the recommended client for knowledge graph extraction.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from kg_extractor.config import AuthConfig


class AgentClient:
    """
    Agent SDK client for knowledge graph extraction.

    Implements: LLMClient protocol (via structural subtyping)

    Uses Claude Agent SDK with tools (Read, Grep, Glob) for file-based extraction.
    The agent can read schema files, analyze data files, and extract entities using
    multi-step reasoning.

    Protocol Methods:
        - generate(): Simple text completion
        - extract_entities(): Tool-based KG extraction with file access

    The Agent SDK approach enables:
        - Tool-based file reading (Read, Grep, Glob)
        - Multi-step reasoning and validation
        - Session-based context preservation
        - Incremental processing without loading all files into prompts
    """

    def __init__(
        self,
        auth_config: AuthConfig,
        model: str = "claude-sonnet-4-5@20250929",
        allowed_tools: list[str] | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        log_prompts: bool = False,
    ):
        """
        Initialize Agent SDK client.

        Args:
            auth_config: Authentication configuration
            model: Model identifier (e.g., claude-sonnet-4-5@20250929)
            allowed_tools: List of tools agent can use (default: Read, Grep, Glob)
            max_retries: Maximum retry attempts on failures
            timeout_seconds: Timeout for agent operations in seconds
            log_prompts: Log full prompts and responses for debugging
        """
        import sys

        self.auth_config = auth_config
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.log_prompts = log_prompts

        # Configure MCP server for structured result submission
        # This provides the submit_extraction_results tool
        mcp_config = {
            "extraction": {
                "command": sys.executable,
                "args": ["-m", "kg_extractor.llm.extraction_mcp_server"],
            }
        }

        # Configure agent options
        # Default tools include file access tools + MCP submission tool
        default_tools = [
            "Read",
            "Grep",
            "Glob",
            "mcp__extraction__submit_extraction_results",  # MCP tool for structured submission
        ]

        options = ClaudeAgentOptions(
            allowed_tools=allowed_tools or default_tools,
            permission_mode="acceptEdits",  # Auto-accept tool use for automation
            mcp_servers=mcp_config,
        )

        # Note: Agent SDK authentication is handled via environment variables
        # ANTHROPIC_API_KEY for API key auth
        # For Vertex AI, we'd need to check Agent SDK documentation
        if auth_config.auth_method == "api_key" and auth_config.api_key:
            import os

            os.environ["ANTHROPIC_API_KEY"] = auth_config.api_key

        self.client = ClaudeSDKClient(options=options)
        self._connected = False
        self._mcp_result = None  # Store result from MCP tool

    async def _ensure_connected(self) -> None:
        """Ensure client is connected to Claude Agent SDK."""
        if not self._connected:
            await self.client.connect()
            self._connected = True

    async def _send_and_receive(self, prompt: str, event_callback: Any = None) -> str:
        """
        Send prompt and receive response from Agent SDK.

        Args:
            prompt: Prompt to send
            event_callback: Optional callback for streaming events (for verbose mode)

        Returns:
            Text response from agent

        Raises:
            RuntimeError: If no response received
        """
        import logging

        from claude_agent_sdk.types import (
            ControlErrorResponse,
            ResultMessage,
            StreamEvent,
        )

        logger = logging.getLogger("kg_extractor.llm")

        await self._ensure_connected()

        # Log prompt if enabled
        if self.log_prompts:
            logger.debug(
                "=" * 80
                + "\n"
                + "PROMPT TO AGENT SDK:\n"
                + "=" * 80
                + "\n"
                + prompt
                + "\n"
                + "=" * 80
            )

        # Send query
        await self.client.query(prompt)

        # Receive response stream
        result_text = None
        messages_received = []
        error_message = None
        current_tool_name = None  # Track current tool being used
        current_tool_input = ""  # Accumulate tool input from deltas
        mcp_result = None  # Store MCP submit_extraction_results arguments
        async for message in self.client.receive_response():
            # Track message types for debugging
            message_type = type(message).__name__
            messages_received.append(message_type)

            # Debug: Log ALL message types when log_prompts enabled
            if self.log_prompts:
                logger.debug(f"Received message type: {message_type}")

            # Handle error response (ControlErrorResponse is a TypedDict, can't use isinstance)
            if isinstance(message, dict) and message.get("subtype") == "error":
                error_message = str(message)
                logger.error(f"Agent SDK returned error: {error_message}")
                break

            # Handle result message
            if isinstance(message, ResultMessage):
                result_text = message.result
                break

            # Handle streaming events (tool usage, etc.)
            # IMPORTANT: Process ALL StreamEvents, not just when event_callback exists
            # We need to capture MCP tool results from the event stream
            if isinstance(message, StreamEvent):
                try:
                    event_data = message.event
                    event_type = event_data.get("type", "unknown")

                    # Log event for debugging (only if log_prompts enabled)
                    if self.log_prompts:
                        logger.debug(f"Agent SDK Event: {event_type}")
                        if event_type in ["content_block_start", "content_block_delta"]:
                            logger.debug(f"  Event data: {event_data}")

                    # Extract useful information based on event type
                    if event_type == "content_block_start":
                        content = event_data.get("content_block", {})
                        if content.get("type") == "tool_use":
                            tool_name = content.get("name", "unknown")
                            current_tool_name = tool_name
                            current_tool_input = ""  # Reset for new tool

                            # Log tool start
                            if self.log_prompts:
                                logger.debug(
                                    f"  Tool: {tool_name}, awaiting input via deltas"
                                )

                            # Report tool usage
                            if event_callback:
                                event_callback(
                                    f"Using tool: {tool_name}", activity_type="tool"
                                )

                    elif event_type == "content_block_delta":
                        delta = event_data.get("delta", {})

                        # Check for input_json_delta (tool input being built)
                        if delta.get("type") == "input_json_delta":
                            # Accumulate the partial JSON
                            partial = delta.get("partial_json", "")
                            current_tool_input += partial
                            if self.log_prompts:
                                logger.debug(
                                    f"  Input JSON delta for {current_tool_name}: +{len(partial)} chars, total: {len(current_tool_input)}"
                                )
                                logger.debug(f"    Partial: {partial[:100]}")

                        elif delta.get("type") == "text_delta":
                            # Agent is thinking/responding
                            text = delta.get("text", "")
                            if text.strip():
                                event_callback(
                                    f"Thinking: {text[:50]}...",
                                    activity_type="thinking",
                                )

                    elif event_type == "content_block_stop":
                        # Tool input is complete - parse and handle based on tool type
                        if self.log_prompts:
                            logger.debug(
                                f"  content_block_stop: tool={current_tool_name}, input_length={len(current_tool_input)}"
                            )

                        if current_tool_input:
                            try:
                                import json

                                tool_input = json.loads(current_tool_input)

                                # Handle Read tool - report file being read
                                if (
                                    current_tool_name == "Read"
                                    and "file_path" in tool_input
                                ):
                                    file_path = tool_input["file_path"]
                                    if event_callback:
                                        event_callback(
                                            f"Reading file: {file_path}",
                                            activity_type="file",
                                        )
                                    if self.log_prompts:
                                        logger.debug(f"  File being read: {file_path}")

                                # Handle MCP submit_extraction_results tool - capture result
                                # Tool name includes MCP prefix: mcp__extraction__submit_extraction_results
                                elif "submit_extraction_results" in current_tool_name:
                                    mcp_result = tool_input
                                    if self.log_prompts:
                                        logger.debug(
                                            f"  MCP result captured from {current_tool_name}: {len(tool_input.get('entities', []))} entities"
                                        )
                                    if event_callback:
                                        entity_count = len(
                                            tool_input.get("entities", [])
                                        )
                                        event_callback(
                                            f"Submitted {entity_count} entities via MCP tool",
                                            activity_type="tool",
                                        )
                            except json.JSONDecodeError:
                                if self.log_prompts:
                                    logger.debug(
                                        f"  Failed to parse tool input for {current_tool_name}: {current_tool_input[:100]}"
                                    )

                except Exception:
                    # Silently ignore parsing errors for events
                    pass

        # Check if we received a response
        if result_text is None:
            messages_summary = (
                ", ".join(messages_received) if messages_received else "none"
            )
            error_detail = f" Error: {error_message}" if error_message else ""
            raise RuntimeError(
                f"No response received from Agent SDK. "
                f"The agent stream ended without returning a ResultMessage. "
                f"Messages received: {messages_summary}.{error_detail} "
                f"This may indicate a connection issue, timeout, or agent error."
            )

        # Store MCP result for extraction methods to use
        if mcp_result:
            self._mcp_result = mcp_result
            if self.log_prompts:
                logger.debug(
                    f"MCP result stored: {len(mcp_result.get('entities', []))} entities, "
                    f"{len(mcp_result.get('metadata', {}).get('types_discovered', []))} types"
                )

        # Log response if enabled
        if self.log_prompts:
            logger.debug(
                "=" * 80
                + "\n"
                + "RESPONSE FROM AGENT SDK:\n"
                + "=" * 80
                + "\n"
                + result_text
                + "\n"
                + "=" * 80
            )

        return result_text

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text completion using Agent SDK.

        Args:
            prompt: User prompt to send to the agent
            system: Optional system prompt for instructions (prepended to user prompt)
            max_tokens: Maximum tokens in response (not directly supported by Agent SDK)
            temperature: Sampling temperature (not directly supported by Agent SDK)

        Returns:
            Generated text response from the agent

        Raises:
            Exception: On agent errors after retries exhausted
        """
        # Build full prompt
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        # Execute with retries
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                # Send and receive response
                response = await self._send_and_receive(full_prompt)
                return response

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    raise

        # This should never be reached, but for type safety
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in retry logic")

    async def extract_entities(
        self,
        prompt: str | None = None,
        data_files: list[Path] | None = None,
        schema_dir: Path | None = None,
        system_instructions: str | None = None,
        event_callback: Any = None,
    ) -> dict[str, Any]:
        """
        Extract entities using agent-based reasoning with tools.

        The agent will:
        1. Read schema files (if provided) using Read tool to understand structure
        2. Read data files using Read tool to extract entities
        3. Use multi-step reasoning to validate and refine extraction
        4. Submit results via submit_extraction_results MCP tool

        Args:
            prompt: Pre-rendered prompt (preferred). If not provided, will build from data_files/schema_dir.
            data_files: List of data file paths (only used if prompt not provided)
            schema_dir: Optional directory containing schema files (only used if prompt not provided)
            system_instructions: Optional system-level instructions (only used if prompt not provided)
            event_callback: Optional callback for streaming events

        Returns:
            Dictionary with structure:
            {
                "entities": [...],  # List of extracted entities
                "metadata": {...}   # Extraction metadata
            }

        Raises:
            Exception: On agent errors or invalid response format
        """
        import logging

        logger = logging.getLogger("kg_extractor.llm")

        # Use provided prompt or build one (for backward compatibility)
        if prompt is None:
            if data_files is None:
                raise ValueError("Either 'prompt' or 'data_files' must be provided")
            prompt = self._build_extraction_prompt(
                data_files=data_files,
                schema_dir=schema_dir,
                instructions=system_instructions,
            )

        # Execute agent workflow with retries
        for attempt in range(self.max_retries):
            try:
                # Reset MCP result before sending
                self._mcp_result = None

                # Send extraction request to agent
                response = await self._send_and_receive(prompt, event_callback)

                # Check if agent used MCP tool to submit results
                if self._mcp_result:
                    # Use MCP result directly (already structured and validated)
                    logger.debug("Using MCP tool result (structured submission)")
                    return self._mcp_result

                # Fall back to JSON parsing if no MCP result
                logger.debug("MCP tool not used, falling back to JSON parsing")
                result = self._parse_extraction_result(response)

                return result

            except ValueError as e:
                # JSON parsing failed - send corrective prompt
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Failed to parse JSON (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )

                    # Send corrective prompt asking for JSON only
                    corrective_prompt = """
I need the extraction results in valid JSON format only. No explanatory text, no markdown formatting.

Please respond with ONLY a JSON object in this exact format:

```json
{
  "entities": [
    {
      "@id": "urn:Type:identifier",
      "@type": "Type",
      "name": "Entity Name",
      "description": "Optional description",
      ...other predicates...
    }
  ],
  "metadata": {
    "entity_count": 0,
    "types_discovered": [],
    "files_processed": 0
  }
}
```

Do not include any text before or after the JSON. Just the JSON object.
"""
                    prompt = corrective_prompt
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    raise

            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    raise

        raise RuntimeError("Unexpected error in retry logic")

    def _build_extraction_prompt(
        self,
        data_files: list[Path],
        schema_dir: Path | None,
        instructions: str | None,
    ) -> str:
        """Build extraction prompt for agent with tool usage guidance."""
        prompt_parts = []

        # Add custom instructions if provided
        if instructions:
            prompt_parts.append(instructions)
            prompt_parts.append("")

        # Main extraction task
        prompt_parts.append(
            """
# Knowledge Graph Entity Extraction Task

You are an expert at extracting structured knowledge from codebases and documentation.

## Your Tools

You have access to these tools:
- **Read**: Read file contents
- **Grep**: Search for patterns in files
- **Glob**: Find files matching patterns

## Data Files to Process
"""
        )

        for file_path in data_files:
            prompt_parts.append(f"- `{file_path}`")

        prompt_parts.append("")

        # Schema guidance
        if schema_dir:
            prompt_parts.append(
                f"""
## Schema Reference

Schema files are located in: `{schema_dir}`

**Step 1**: Use the Read tool to examine schema files and understand expected entity types.
"""
            )
        else:
            prompt_parts.append(
                """
## Schema Discovery

No schema provided. You should discover entity types through pattern analysis.
"""
            )

        # Extraction instructions
        prompt_parts.append(
            """
## Extraction Process

**Step 2**: Use the Read tool to load and analyze each data file.

**Step 3**: Extract ALL entities with maximum fidelity. For each entity:
- Generate a valid URN identifier: `urn:type:identifier` (e.g., `urn:Service:payment-api`)
- Determine the entity type (e.g., Service, Team, API, Database)
- Extract the name and description
- Capture ALL relationships as predicates with `{"@id": "urn:..."}` references

**Step 4**: Validate all entities:
- Every entity must have `@id`, `@type`, and `name` fields
- All URNs must follow format: `urn:type:identifier`
- All types must be valid identifiers (alphanumeric, start with capital letter)
- Relationships should use predicates, NOT separate Relationship entities

**Step 5**: Return results as JSON **ONLY** - no explanations, summaries, or other text.

Your FINAL response must be ONLY valid JSON in this exact format:

```json
{
  "entities": [
    {
      "@id": "urn:Service:payment-api",
      "@type": "Service",
      "name": "Payment API",
      "description": "Handles payment processing",
      "language": "Python",
      "ownedBy": {"@id": "urn:Team:payments"}
    }
  ],
  "metadata": {
    "entity_count": 1,
    "types_discovered": ["Service", "Team"],
    "files_processed": 3
  }
}
```

## Critical Rules

1. **Use Tools**: Use Read tool to access files - don't ask me to provide file contents
2. **No Relationship Entities**: Express relationships as predicates only
3. **Valid URNs**: All @id must be `urn:type:identifier` format
4. **Valid Types**: All @type must be alphanumeric, start with capital letter
5. **Complete Extraction**: Extract ALL entities, don't truncate or skip
6. **JSON-ONLY OUTPUT**: Your final response MUST be ONLY the JSON object (in a ```json code block or raw).
   DO NOT include explanatory text like "I've extracted..." or "Complete!".
   ONLY the JSON structure above.

Begin the extraction now by reading the files. When complete, respond with ONLY the JSON output.
"""
        )

        return "\n".join(prompt_parts)

    def _parse_extraction_result(self, response: str) -> dict[str, Any]:
        """
        Parse agent response into structured result.

        Args:
            response: Raw text response from agent

        Returns:
            Parsed dictionary with entities and metadata

        Raises:
            PromptTooLongError: If the response indicates a 413 error
            ValueError: If response cannot be parsed as valid JSON
        """
        from kg_extractor.exceptions import PromptTooLongError

        # Check for 413 error (prompt too long)
        if (
            "API Error: 413" in response
            or '"error":{"type":"invalid_request_error","message":"Prompt is too long"'
            in response
        ):
            raise PromptTooLongError(
                "Prompt exceeds model context window. Chunk needs to be split into smaller pieces.",
                chunk_size=None,  # Will be filled in by orchestrator
            )

        # Agent may return JSON in markdown code block, raw JSON, or with surrounding text
        json_text = response.strip()

        # Strategy 1: Try to extract from markdown code block
        if "```json" in json_text:
            json_start = json_text.find("```json") + 7
            json_end = json_text.find("```", json_start)
            if json_end > json_start:
                json_text = json_text[json_start:json_end].strip()
        elif "```" in json_text:
            # Generic code block
            json_start = json_text.find("```") + 3
            json_end = json_text.find("```", json_start)
            if json_end > json_start:
                json_text = json_text[json_start:json_end].strip()

        # Strategy 2: Try to find JSON object boundaries
        # Look for the first { and last } to extract JSON from surrounding text
        first_brace = json_text.find("{")
        last_brace = json_text.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            potential_json = json_text[first_brace : last_brace + 1]

            # Try parsing this potential JSON
            try:
                result = json.loads(potential_json)

                # Validate it has the expected structure before accepting
                if "entities" in result:
                    json_text = potential_json
            except json.JSONDecodeError:
                # If it doesn't parse, we'll try the original text
                pass

        # Parse JSON
        try:
            result = json.loads(json_text)
        except json.JSONDecodeError as e:
            # More detailed error message
            lines = response.split("\n")
            first_lines = "\n".join(lines[:10])  # Show first 10 lines
            raise ValueError(
                f"Could not parse agent response as JSON.\n"
                f"JSON Error: {e}\n"
                f"Response start:\n{first_lines}\n"
                f"...\n"
                f"Expected response to be valid JSON with 'entities' and 'metadata' fields."
            ) from e

        # Validate structure
        if "entities" not in result:
            raise ValueError(
                "Agent response missing 'entities' field. "
                f"Response structure: {list(result.keys())}"
            )

        return result
