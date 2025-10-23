"""LLM client interfaces and implementations."""

from kg_extractor.llm.anthropic_client import AnthropicClient
from kg_extractor.llm.protocol import LLMClient

__all__ = ["LLMClient", "AnthropicClient"]
