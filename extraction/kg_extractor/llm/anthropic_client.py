"""Anthropic LLM client implementation.

Supports both Vertex AI (Google Cloud) and API key authentication.
"""

import asyncio
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
