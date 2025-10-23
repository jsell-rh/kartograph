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
        self.auth_config = auth_config
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.log_prompts = log_prompts

        # Configure agent options
        options = ClaudeAgentOptions(
            allowed_tools=allowed_tools or ["Read", "Grep", "Glob"],
            permission_mode="acceptEdits",  # Auto-accept tool use for automation
        )

        # Note: Agent SDK authentication is handled via environment variables
        # ANTHROPIC_API_KEY for API key auth
        # For Vertex AI, we'd need to check Agent SDK documentation
        if auth_config.auth_method == "api_key" and auth_config.api_key:
            import os

            os.environ["ANTHROPIC_API_KEY"] = auth_config.api_key

        self.client = ClaudeSDKClient(options=options)
        self._connected = False

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

        from claude_agent_sdk.types import ResultMessage, StreamEvent

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
        async for message in self.client.receive_response():
            # Handle result message
            if isinstance(message, ResultMessage):
                result_text = message.result
                break

            # Handle streaming events (tool usage, etc.) in verbose mode
            if isinstance(message, StreamEvent) and event_callback:
                try:
                    event_data = message.event
                    event_type = event_data.get("type", "unknown")

                    # Extract useful information based on event type
                    if event_type == "content_block_start":
                        content = event_data.get("content_block", {})
                        if content.get("type") == "tool_use":
                            tool_name = content.get("name", "unknown")
                            event_callback(
                                f"Using tool: {tool_name}", activity_type="tool"
                            )

                    elif event_type == "content_block_delta":
                        delta = event_data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            # Agent is thinking/responding
                            text = delta.get("text", "")
                            if text.strip():
                                event_callback(
                                    f"Thinking: {text[:50]}...",
                                    activity_type="thinking",
                                )

                except Exception:
                    # Silently ignore parsing errors for events
                    pass

        if result_text is None:
            raise RuntimeError("No response received from agent")

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
        data_files: list[Path],
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
        4. Return structured results as JSON

        Args:
            data_files: List of data file paths to extract from
            schema_dir: Optional directory containing schema files
            system_instructions: Optional system-level instructions

        Returns:
            Dictionary with structure:
            {
                "entities": [...],  # List of extracted entities
                "metadata": {...}   # Extraction metadata
            }

        Raises:
            Exception: On agent errors or invalid response format
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(
            data_files=data_files,
            schema_dir=schema_dir,
            instructions=system_instructions,
        )

        # Execute agent workflow with retries
        for attempt in range(self.max_retries):
            try:
                # Send extraction request to agent
                response = await self._send_and_receive(prompt, event_callback)

                # Parse and validate response
                result = self._parse_extraction_result(response)

                return result

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

**Step 5**: Return results as JSON with this exact structure:

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
6. **JSON Output**: Final response must be valid JSON

Begin the extraction now by reading the files.
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
            ValueError: If response cannot be parsed as valid JSON
        """
        # Agent may return JSON in markdown code block or raw JSON
        json_text = response.strip()

        # Try to extract from markdown code block
        if "```json" in json_text:
            json_start = json_text.find("```json") + 7
            json_end = json_text.find("```", json_start)
            json_text = json_text[json_start:json_end].strip()
        elif "```" in json_text:
            # Generic code block
            json_start = json_text.find("```") + 3
            json_end = json_text.find("```", json_start)
            json_text = json_text[json_start:json_end].strip()

        # Parse JSON
        try:
            result = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse agent response as JSON. Error: {e}\n"
                f"Response preview: {response[:500]}..."
            ) from e

        # Validate structure
        if "entities" not in result:
            raise ValueError(
                "Agent response missing 'entities' field. "
                f"Response: {response[:500]}..."
            )

        return result
