"""LLM client protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy mocking in tests without hitting real LLM APIs
- Transparent retry logic via decorators
- Cost tracking and observability
"""

from pathlib import Path
from typing import Any, Protocol


class LLMClient(Protocol):
    """
    Protocol for LLM client implementations.

    Implementations must support both Vertex AI and API key authentication.
    The protocol defines two levels of functionality:

    1. Basic: generate() for simple text completion
    2. Advanced: extract_entities() for agent-based KG extraction with tools

    Agent SDK implementations can provide both.
    Messages API implementations may only provide generate().
    """

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text completion from the LLM.

        Args:
            prompt: User prompt to send to the LLM
            system: Optional system prompt for instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Generated text response from the LLM

        Raises:
            Exception: On API errors after retries exhausted
        """
        ...

    async def extract_entities(
        self,
        data_files: list[Path],
        schema_dir: Path | None = None,
        system_instructions: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract entities from files using agent-based reasoning.

        For Agent SDK implementations: Uses tools (Read, Grep, Glob) to access files
        For Messages API implementations: Reads files and includes in prompts

        The method should return a dictionary with structure:
        {
            "entities": [...],  # List of extracted entities
            "metadata": {...}   # Extraction metadata
        }

        Args:
            data_files: List of data file paths to extract from
            schema_dir: Optional directory containing schema files
            system_instructions: Optional system-level instructions

        Returns:
            Dictionary containing extracted entities and metadata

        Raises:
            Exception: On extraction errors or invalid response format
        """
        ...
