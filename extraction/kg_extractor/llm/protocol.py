"""LLM client protocol for structural subtyping.

This protocol enables:
- Clean separation between interface and implementation
- Easy mocking in tests without hitting real LLM APIs
- Transparent retry logic via decorators
- Cost tracking and observability
"""

from typing import Protocol


class LLMClient(Protocol):
    """
    Protocol for LLM client implementations.

    Implementations must support both Vertex AI and API key authentication.
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
