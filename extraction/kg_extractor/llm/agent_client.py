"""Agent SDK-based LLM client implementation.

Uses Claude Agent SDK with built-in tools for file access and multi-step reasoning.
This is the recommended client for knowledge graph extraction.

Features rate limiting transparency:
- Semaphore-based concurrency control (limits parallel API calls)
- Global backoff on 429 errors (coordinates all instances)
- Automatic retry with exponential backoff (rate-aware)
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, ClassVar

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from kg_extractor.config import AuthConfig

logger = logging.getLogger(__name__)


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

    Rate Limiting (Transparent to Callers):
        - Semaphore limits concurrent API calls across ALL instances
        - Global backoff on 429 errors (one instance rate limited = all wait)
        - Automatic retry with rate-aware exponential backoff
    """

    # Class-level shared state for global rate limit coordination
    # These are shared across ALL AgentClient instances
    _rate_limit_semaphore: ClassVar[asyncio.Semaphore | None] = None
    _rate_limited_until: ClassVar[float | None] = (
        None  # Timestamp when rate limit expires
    )
    _semaphore_lock: ClassVar[asyncio.Lock | None] = None  # For lazy initialization
    _client_pool: ClassVar[asyncio.Queue | None] = (
        None  # Pool of ClaudeSDKClient instances
    )

    def __init__(
        self,
        auth_config: AuthConfig,
        model: str = "claude-sonnet-4-5@20250929",
        allowed_tools: list[str] | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        log_prompts: bool = False,
        max_concurrent: int = 3,
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
            max_concurrent: Maximum concurrent API calls (default: 3, shared across all instances)
        """
        import sys

        self.auth_config = auth_config
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.log_prompts = log_prompts
        self.max_concurrent = max_concurrent

        # Initialize class-level lock if needed (for semaphore initialization)
        if AgentClient._semaphore_lock is None:
            AgentClient._semaphore_lock = asyncio.Lock()

        # Store config for creating client instances in the pool
        self.allowed_tools = allowed_tools
        self._mcp_result = None  # Store result from MCP tool
        self.last_usage = None  # Store usage stats from last API call

    def _create_client_instance(self) -> ClaudeSDKClient:
        """Create a new ClaudeSDKClient instance for the pool."""
        import sys

        logger.debug("Creating new ClaudeSDKClient instance (will spawn MCP server)")

        # Configure MCP server
        mcp_config = {
            "extraction": {
                "command": sys.executable,
                "args": ["-m", "kg_extractor.llm.extraction_mcp_server"],
            }
        }

        # Configure agent options
        default_tools = [
            "Read",
            "Grep",
            "Glob",
            "mcp__extraction__submit_extraction_results",
        ]

        options = ClaudeAgentOptions(
            allowed_tools=self.allowed_tools or default_tools,
            permission_mode="acceptEdits",
            mcp_servers=mcp_config,
        )

        # Set API key if using API key auth
        if self.auth_config.auth_method == "api_key" and self.auth_config.api_key:
            import os

            os.environ["ANTHROPIC_API_KEY"] = self.auth_config.api_key

        client = ClaudeSDKClient(options=options)
        logger.debug("ClaudeSDKClient instance created successfully")
        return client

    def _build_tool_detail(self, tool_name: str, tool_input: dict) -> str | None:
        """
        Build detail string for tool usage display.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Detail string to show in dim/grey, or None
        """
        # Read tool - show file path
        if tool_name == "Read" and "file_path" in tool_input:
            return f"file: {tool_input['file_path']}"

        # Grep tool - show pattern and path
        elif tool_name == "Grep" and "pattern" in tool_input:
            pattern = tool_input["pattern"]
            path = tool_input.get("path", ".")
            return f"pattern: {pattern}, path: {path}"

        # Glob tool - show pattern
        elif tool_name == "Glob" and "pattern" in tool_input:
            return f"pattern: {tool_input['pattern']}"

        # Default - show nothing
        return None

    async def _get_semaphore_and_pool(self) -> tuple[asyncio.Semaphore, asyncio.Queue]:
        """
        Get or create the shared semaphore and client pool for rate limiting.

        Uses lazy initialization with a lock to ensure only one semaphore/pool is created
        across all AgentClient instances.

        Returns:
            Tuple of (semaphore, client_pool)
        """
        # Fast path: semaphore and pool already exist
        if (
            AgentClient._rate_limit_semaphore is not None
            and AgentClient._client_pool is not None
        ):
            return AgentClient._rate_limit_semaphore, AgentClient._client_pool

        # Slow path: need to create semaphore and pool (with lock)
        async with AgentClient._semaphore_lock:
            # Double-check (another instance may have created it while we waited for lock)
            if AgentClient._rate_limit_semaphore is None:
                AgentClient._rate_limit_semaphore = asyncio.Semaphore(
                    self.max_concurrent
                )

            if AgentClient._client_pool is None:
                # Create pool with N client instances
                # IMPORTANT: maxsize ensures pool CANNOT grow beyond this limit
                AgentClient._client_pool = asyncio.Queue(maxsize=self.max_concurrent)
                logger.info(
                    f"Creating client pool with {self.max_concurrent} ClaudeSDKClient instances"
                )
                for i in range(self.max_concurrent):
                    client = self._create_client_instance()
                    await AgentClient._client_pool.put(client)
                    logger.debug(f"Initialized client {i+1}/{self.max_concurrent}")

            return AgentClient._rate_limit_semaphore, AgentClient._client_pool

    async def _wait_for_rate_limit_clearance(self) -> None:
        """
        Wait if a global rate limit backoff is in effect.

        Checks the class-level _rate_limited_until timestamp. If set and not expired,
        waits until the backoff period completes.

        This ensures that when ANY instance hits a 429 error, ALL instances pause.
        """
        if AgentClient._rate_limited_until is not None:
            wait_time = AgentClient._rate_limited_until - time.time()
            if wait_time > 0:
                logger.warning(
                    f"Rate limit backoff in effect. Waiting {wait_time:.1f} seconds..."
                )
                await asyncio.sleep(wait_time)

    def _detect_rate_limit_error(self, error: Exception) -> bool:
        """
        Detect if an error is a rate limit (429) error.

        Checks exception message and type for common rate limit indicators.

        Args:
            error: Exception to check

        Returns:
            True if error appears to be a rate limit error
        """
        error_str = str(error).lower()
        patterns = [
            "429",
            "rate limit",
            "rate_limit",
            "ratelimit",
            "quota exceeded",
            "too many requests",
            "throttle",
            "throttling",
        ]
        return any(pattern in error_str for pattern in patterns)

    def _calculate_backoff(self, attempt: int, is_rate_limit: bool) -> float:
        """
        Calculate backoff duration based on attempt number and error type.

        Args:
            attempt: Retry attempt number (0-indexed)
            is_rate_limit: True if this is a rate limit error (429)

        Returns:
            Backoff duration in seconds
        """
        if is_rate_limit:
            # Aggressive backoff for rate limits: 5s → 10s → 20s → 40s
            return 5 * (2**attempt)
        else:
            # Standard backoff for other errors: 2s → 4s → 8s
            return 2 * (2**attempt)

    def _set_global_backoff(self, backoff_seconds: float) -> None:
        """
        Set global rate limit backoff timestamp.

        When ANY instance hits a rate limit, this sets a class-level timestamp
        that ALL instances will respect before making new API calls.

        Args:
            backoff_seconds: How long to wait before allowing new API calls
        """
        AgentClient._rate_limited_until = time.time() + backoff_seconds

        logger.warning(
            f"Global rate limit backoff set for {backoff_seconds:.1f} seconds. "
            f"All AgentClient instances will pause until {time.strftime('%H:%M:%S', time.localtime(AgentClient._rate_limited_until))}"
        )

    @classmethod
    def get_pool_stats(cls) -> dict[str, Any]:
        """
        Get current client pool statistics for monitoring memory leaks.

        Returns:
            Dictionary with pool_size, max_size, available_slots
        """
        if cls._client_pool is None:
            return {"initialized": False}

        return {
            "initialized": True,
            "current_size": cls._client_pool.qsize(),
            "max_size": cls._client_pool.maxsize,
            "available_slots": cls._client_pool.maxsize - cls._client_pool.qsize(),
        }

    async def _send_and_receive(self, prompt: str, event_callback: Any = None) -> str:
        """
        Send prompt and receive response from Agent SDK.

        Implements rate limiting transparency:
        - Waits if global rate limit backoff is in effect
        - Acquires semaphore to limit concurrent API calls
        - Transparent to callers - they don't need to know about rate limiting

        Args:
            prompt: Prompt to send
            event_callback: Optional callback for streaming events (for verbose mode)

        Returns:
            Text response from agent

        Raises:
            RuntimeError: If no response received
            Exception: Any API errors (will be caught by retry logic in calling methods)
        """
        from claude_agent_sdk.types import (
            AssistantMessage,
            ControlErrorResponse,
            ResultMessage,
            StreamEvent,
            ToolUseBlock,
        )

        # 1. Wait if globally rate limited (transparent coordination)
        await self._wait_for_rate_limit_clearance()

        # 2. Get semaphore and client pool
        semaphore, client_pool = await self._get_semaphore_and_pool()

        # 3. Acquire a client from the pool (blocks if pool is empty)
        client = await client_pool.get()

        try:
            # 4. Acquire semaphore to enforce rate limit
            async with semaphore:
                # Ensure client is connected
                try:
                    await client.connect()
                except:
                    pass  # Might already be connected

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
                await client.query(prompt)

            # Receive response stream (outside semaphore, but holding pool slot)
            result_text = None
            messages_received = []
            error_message = None
            current_tool_name = None  # Track current tool being used
            current_tool_input = ""  # Accumulate tool input from deltas
            mcp_result = None  # Store MCP submit_extraction_results arguments
            async for message in client.receive_response():
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

                # Handle AssistantMessage (contains tool use blocks with complete input)
                if isinstance(message, AssistantMessage):
                    # Check for tool use blocks in content
                    for content_block in message.content:
                        if isinstance(content_block, ToolUseBlock):
                            tool_name = content_block.name
                            tool_input = content_block.input

                            if self.log_prompts:
                                logger.debug(
                                    f"Tool use block: {tool_name}, input keys: {list(tool_input.keys())}"
                                )

                            # Capture MCP submit_extraction_results tool
                            if "submit_extraction_results" in tool_name:
                                # Warn if we already captured a result (multiple calls)
                                if mcp_result is not None:
                                    logger.warning(
                                        f"Multiple submit_extraction_results calls detected! "
                                        f"Previous result had {len(mcp_result.get('entities', []))} entities, "
                                        f"new result has {len(tool_input.get('entities', []))} entities. "
                                        f"Keeping the last one."
                                    )

                                mcp_result = tool_input
                                if self.log_prompts:
                                    logger.debug(
                                        f"  MCP result captured from {tool_name}: {len(tool_input.get('entities', []))} entities"
                                    )

                            # Report tool usage if callback provided
                            if event_callback:
                                if "submit_extraction_results" in tool_name:
                                    entity_count = len(tool_input.get("entities", []))
                                    event_callback(
                                        f"Submitted {entity_count} entities via MCP tool",
                                        activity_type="tool",
                                    )
                                else:
                                    # Build tool detail string for common tools
                                    detail = self._build_tool_detail(
                                        tool_name, tool_input
                                    )
                                    event_callback(
                                        f"Using tool: {tool_name}",
                                        activity_type="tool",
                                        detail=detail,
                                    )

                # Handle result message
                if isinstance(message, ResultMessage):
                    result_text = message.result

                    # Capture usage stats for cost tracking
                    # Per Agent SDK docs: https://docs.claude.com/en/api/agent-sdk/cost-tracking.md
                    # ResultMessage.usage contains CUMULATIVE usage across all turns, with fields:
                    # - input_tokens: Base input tokens
                    # - cache_creation_input_tokens: Tokens used to create cache
                    # - cache_read_input_tokens: Tokens read from cache
                    # - output_tokens: Output tokens
                    if message.usage:
                        # Sum all input token types (base + cache creation + cache read)
                        total_input_tokens = (
                            message.usage.get("input_tokens", 0)
                            + message.usage.get("cache_creation_input_tokens", 0)
                            + message.usage.get("cache_read_input_tokens", 0)
                        )
                        total_output_tokens = message.usage.get("output_tokens", 0)
                    else:
                        total_input_tokens = 0
                        total_output_tokens = 0

                    self.last_usage = {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_cost_usd": message.total_cost_usd or 0.0,
                        "duration_ms": message.duration_ms,
                        "duration_api_ms": message.duration_api_ms,
                        # Store breakdown for debugging
                        "usage_breakdown": message.usage if message.usage else {},
                    }

                    if self.log_prompts:
                        logger.debug(
                            f"Usage (cumulative): {self.last_usage['input_tokens']} input tokens, "
                            f"{self.last_usage['output_tokens']} output tokens, "
                            f"${self.last_usage['total_cost_usd']:.4f}"
                        )
                        # Show breakdown if available
                        if message.usage:
                            logger.debug(
                                f"  Input breakdown: "
                                f"base={message.usage.get('input_tokens', 0)}, "
                                f"cache_creation={message.usage.get('cache_creation_input_tokens', 0)}, "
                                f"cache_read={message.usage.get('cache_read_input_tokens', 0)}"
                            )

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
                            if event_type in [
                                "content_block_start",
                                "content_block_delta",
                            ]:
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

                                # Report tool usage (detail will be added when we parse the input)
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
                                            logger.debug(
                                                f"  File being read: {file_path}"
                                            )

                                    # Handle Grep tool - report pattern being searched
                                    elif (
                                        current_tool_name == "Grep"
                                        and "pattern" in tool_input
                                    ):
                                        pattern = tool_input["pattern"]
                                        path = tool_input.get("path", ".")
                                        detail = f"pattern: {pattern}, path: {path}"
                                        if event_callback:
                                            event_callback(
                                                f"Using tool: {current_tool_name}",
                                                activity_type="tool",
                                                detail=detail,
                                            )

                                    # Handle Glob tool - report glob pattern
                                    elif (
                                        current_tool_name == "Glob"
                                        and "pattern" in tool_input
                                    ):
                                        pattern = tool_input["pattern"]
                                        detail = f"pattern: {pattern}"
                                        if event_callback:
                                            event_callback(
                                                f"Using tool: {current_tool_name}",
                                                activity_type="tool",
                                                detail=detail,
                                            )

                                    # Handle MCP submit_extraction_results tool - capture result
                                    # Tool name includes MCP prefix: mcp__extraction__submit_extraction_results
                                    elif (
                                        "submit_extraction_results" in current_tool_name
                                    ):
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

        finally:
            # CRITICAL: Return client to pool immediately
            # DO NOT clear session - each chunk prompt is self-contained anyway
            # Any session clearing (disconnect, /clear) causes MCP process leaks
            try:
                await client_pool.put(client)
                logger.debug("Client returned to pool")
            except Exception as e:
                # Failed to return client - this is catastrophic
                logger.error(
                    f"CRITICAL: Failed to return client to pool: {e}. "
                    f"Client will leak. Pool may be depleted."
                )
                # Try to disconnect as last resort
                try:
                    await client.disconnect()
                except Exception:
                    pass  # Can't do anything more

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

        # Execute with retries (rate-aware backoff)
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                # Send and receive response
                response = await self._send_and_receive(full_prompt)
                return response

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Detect if this is a rate limit error
                    is_rate_limit = self._detect_rate_limit_error(e)

                    # Calculate backoff (aggressive for rate limits)
                    backoff = self._calculate_backoff(attempt, is_rate_limit)

                    # If rate limited, set global backoff so ALL instances wait
                    if is_rate_limit:
                        self._set_global_backoff(backoff)

                    logger.warning(
                        f"{'Rate limit' if is_rate_limit else 'Error'} on attempt {attempt + 1}/{self.max_retries}: {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )

                    await asyncio.sleep(backoff)
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

                    # Send corrective prompt but KEEP original context
                    # The agent may remember what it was extracting from session history
                    corrective_prompt = """
Your previous response included extra text around the JSON. I need ONLY the JSON object, nothing else.

Please provide the extraction results again as ONLY valid JSON in this exact format:

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

No explanatory text, no markdown formatting - just the JSON object you extracted before.
"""
                    # Keep original prompt in session by NOT replacing it
                    # Agent SDK maintains conversation history, so agent remembers context
                    # Just send the corrective instruction as a follow-up
                    prompt = corrective_prompt
                    # JSON parsing errors are not rate limits - use standard backoff
                    backoff = self._calculate_backoff(attempt, is_rate_limit=False)
                    await asyncio.sleep(backoff)
                    continue
                else:
                    raise

            except Exception as e:
                # General errors (including rate limits)
                if attempt < self.max_retries - 1:
                    # Detect if this is a rate limit error
                    is_rate_limit = self._detect_rate_limit_error(e)

                    # Calculate backoff (aggressive for rate limits)
                    backoff = self._calculate_backoff(attempt, is_rate_limit)

                    # If rate limited, set global backoff so ALL instances wait
                    if is_rate_limit:
                        self._set_global_backoff(backoff)

                    logger.warning(
                        f"{'Rate limit' if is_rate_limit else 'Error'} on attempt {attempt + 1}/{self.max_retries}: {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )

                    await asyncio.sleep(backoff)
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
        # Look for { positions and try parsing from each one (in case there are other { } in text)
        # Try all possible starting positions to find the actual JSON object
        pos = 0
        while pos < len(json_text):
            first_brace = json_text.find("{", pos)
            if first_brace == -1:
                break

            last_brace = json_text.rfind("}")
            if last_brace > first_brace:
                potential_json = json_text[first_brace : last_brace + 1]

                # Try parsing this potential JSON
                try:
                    result = json.loads(potential_json)

                    # Validate it has the expected structure before accepting
                    if "entities" in result:
                        json_text = potential_json
                        break  # Found valid JSON, stop searching
                except json.JSONDecodeError:
                    # Try next starting position
                    pos = first_brace + 1
                    continue
            else:
                break

            pos = first_brace + 1

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
