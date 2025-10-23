"""Anthropic LLM client implementation.

Supports both Vertex AI (Google Cloud) and API key authentication.

NOTE: This is a Messages API implementation. For production use,
consider using AgentClient with the Agent SDK for tool-based extraction.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import anthropic

from kg_extractor.config import AuthConfig


class AnthropicClient:
    """
    Anthropic LLM client with retry logic and error handling.

    Implements the LLMClient protocol using Anthropic's Python SDK.
    """

    def __init__(
        self,
        auth_config: AuthConfig,
        model: str,
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ):
        """
        Initialize Anthropic client.

        Args:
            auth_config: Authentication configuration
            model: Model identifier (e.g., claude-sonnet-4-5@20250929)
            max_retries: Maximum retry attempts on failures
            timeout_seconds: Timeout for API calls in seconds
        """
        self.auth_config = auth_config
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        # Create appropriate client based on auth method
        if auth_config.auth_method == "vertex_ai":
            self.client = anthropic.AnthropicVertex(
                project_id=auth_config.vertex_project_id,
                region=auth_config.vertex_region,
            )
        else:  # api_key
            self.client = anthropic.Anthropic(
                api_key=auth_config.api_key,
            )

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text completion from Claude.

        Args:
            prompt: User prompt to send to Claude
            system: Optional system prompt for instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Generated text response from Claude

        Raises:
            Exception: On API errors after retries exhausted
        """
        # Build messages array
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        # Retry loop
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                # Call Anthropic API (synchronously, but we wrap in async)
                response = self.client.messages.create(**kwargs)

                # Extract text from response
                if not response.content or len(response.content) == 0:
                    raise ValueError("Empty response from LLM")

                return response.content[0].text

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, ...
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    # Max retries exceeded, raise the last exception
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
    ) -> dict[str, Any]:
        """
        Extract entities using Messages API (reads files and includes in prompt).

        NOTE: This implementation reads all files and includes content in the prompt.
        For large codebases, consider using AgentClient with the Agent SDK instead,
        which can use tools to read files incrementally.

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
            Exception: On extraction errors or invalid response format
        """
        # Read all files into memory
        file_contents = {}
        for file_path in data_files:
            try:
                file_contents[str(file_path)] = file_path.read_text(encoding="utf-8")
            except Exception as e:
                # Skip files that can't be read
                file_contents[str(file_path)] = f"[Error reading file: {e}]"

        # Read schema files if provided
        schema_contents = {}
        if schema_dir and schema_dir.exists():
            for schema_file in schema_dir.glob("**/*"):
                if schema_file.is_file():
                    try:
                        schema_contents[str(schema_file)] = schema_file.read_text(
                            encoding="utf-8"
                        )
                    except Exception:
                        pass

        # Build extraction prompt
        prompt = self._build_extraction_prompt(
            file_contents=file_contents,
            schema_contents=schema_contents,
            instructions=system_instructions,
        )

        # Use generate() to get response
        response = await self.generate(
            prompt=prompt,
            system="You are an expert at extracting structured knowledge graphs.",
            max_tokens=4096,
            temperature=0.0,
        )

        # Parse response as JSON
        return self._parse_extraction_result(response)

    def _build_extraction_prompt(
        self,
        file_contents: dict[str, str],
        schema_contents: dict[str, str],
        instructions: str | None,
    ) -> str:
        """Build extraction prompt with file contents."""
        prompt_parts = []

        if instructions:
            prompt_parts.append(instructions)
            prompt_parts.append("")

        prompt_parts.append("# Knowledge Graph Entity Extraction Task")
        prompt_parts.append("")

        # Include schema if provided
        if schema_contents:
            prompt_parts.append("## Schema Files")
            for path, content in schema_contents.items():
                prompt_parts.append(f"\n### {path}\n```\n{content}\n```")
            prompt_parts.append("")

        # Include data files
        prompt_parts.append("## Data Files to Extract From")
        for path, content in file_contents.items():
            prompt_parts.append(f"\n### {path}\n```\n{content}\n```")
        prompt_parts.append("")

        # Extraction instructions
        prompt_parts.append(
            """
## Task

Extract ALL entities from the data files with maximum fidelity.

For each entity:
- Generate URN: `urn:type:identifier` (e.g., `urn:Service:payment-api`)
- Determine type (e.g., Service, Team, API)
- Extract name and description
- Capture relationships as predicates with `{"@id": "urn:..."}` references

## Output Format

Return ONLY valid JSON with this structure:

```json
{
  "entities": [
    {
      "@id": "urn:Service:payment-api",
      "@type": "Service",
      "name": "Payment API",
      "description": "...",
      "ownedBy": {"@id": "urn:Team:payments"}
    }
  ],
  "metadata": {
    "entity_count": 1,
    "types_discovered": ["Service", "Team"]
  }
}
```

## Rules

1. All @id must be valid URNs (urn:type:identifier)
2. All @type must start with capital letter, alphanumeric only
3. All entities must have @id, @type, and name
4. Use predicates for relationships, NOT Relationship entities
5. Return ONLY the JSON, no explanatory text

Begin extraction now.
"""
        )

        return "\n".join(prompt_parts)

    def _parse_extraction_result(self, response: str) -> dict[str, Any]:
        """Parse extraction response as JSON."""
        json_text = response.strip()

        # Try to extract from markdown code block
        if "```json" in json_text:
            json_start = json_text.find("```json") + 7
            json_end = json_text.find("```", json_start)
            json_text = json_text[json_start:json_end].strip()
        elif "```" in json_text:
            json_start = json_text.find("```") + 3
            json_end = json_text.find("```", json_start)
            json_text = json_text[json_start:json_end].strip()

        try:
            result = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse response as JSON. Error: {e}\n"
                f"Response preview: {response[:500]}..."
            ) from e

        if "entities" not in result:
            raise ValueError(
                f"Response missing 'entities' field. Response: {response[:500]}..."
            )

        return result
