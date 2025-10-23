"""Unit tests for LLM client interface."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock LLM response structure
class MockMessage:
    """Mock Anthropic message response."""

    def __init__(self, content: str):
        self.content = [MagicMock(text=content)]
        self.stop_reason = "end_turn"
        self.usage = MagicMock(input_tokens=100, output_tokens=50)


@pytest.mark.asyncio
async def test_llm_client_protocol():
    """Test LLMClient protocol defines required methods."""
    from kg_extractor.llm.protocol import LLMClient

    # Protocol should define generate method
    assert hasattr(LLMClient, "generate")


@pytest.mark.asyncio
async def test_anthropic_client_vertex_ai():
    """Test AnthropicClient with Vertex AI authentication."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="vertex_ai",
        vertex_project_id="test-project",
        vertex_region="us-central1",
    )

    with patch("anthropic.AnthropicVertex") as MockVertex:
        mock_client = MagicMock()
        MockVertex.return_value = mock_client

        client = AnthropicClient(auth_config=auth, model="claude-sonnet-4-5@20250929")

        # Should create AnthropicVertex client
        MockVertex.assert_called_once_with(
            project_id="test-project",
            region="us-central1",
        )


@pytest.mark.asyncio
async def test_anthropic_client_api_key():
    """Test AnthropicClient with API key authentication."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="sk-ant-test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        client = AnthropicClient(auth_config=auth, model="claude-sonnet-4-5@20250929")

        # Should create Anthropic client with API key
        MockAnthropic.assert_called_once_with(
            api_key="sk-ant-test-key"  # pragma: allowlist secret
        )


@pytest.mark.asyncio
async def test_anthropic_client_generate_basic():
    """Test AnthropicClient.generate() with basic prompt."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages

        # Mock the create response
        mock_messages.create.return_value = MockMessage("Test response from Claude")

        MockAnthropic.return_value = mock_client

        client = AnthropicClient(auth_config=auth, model="claude-sonnet-4-5@20250929")

        response = await client.generate(
            prompt="Test prompt",
            max_tokens=1024,
            temperature=0.0,
        )

        # Should call messages.create with correct parameters
        mock_messages.create.assert_called_once()
        call_kwargs = mock_messages.create.call_args.kwargs

        assert call_kwargs["model"] == "claude-sonnet-4-5@20250929"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["temperature"] == 0.0
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"

        # Should return response text
        assert response == "Test response from Claude"


@pytest.mark.asyncio
async def test_anthropic_client_generate_with_system():
    """Test AnthropicClient.generate() with system prompt."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages
        mock_messages.create.return_value = MockMessage("Response")

        MockAnthropic.return_value = mock_client

        client = AnthropicClient(auth_config=auth, model="claude-sonnet-4-5@20250929")

        await client.generate(
            prompt="User prompt",
            system="You are a helpful assistant",
            max_tokens=1024,
            temperature=0.0,
        )

        # Should include system parameter
        call_kwargs = mock_messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are a helpful assistant"


@pytest.mark.asyncio
async def test_anthropic_client_retry_on_failure():
    """Test AnthropicClient retries on API errors."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages

        # Fail twice, then succeed
        mock_messages.create.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            MockMessage("Success after retries"),
        ]

        MockAnthropic.return_value = mock_client

        client = AnthropicClient(
            auth_config=auth,
            model="claude-sonnet-4-5@20250929",
            max_retries=3,
        )

        response = await client.generate(
            prompt="Test",
            max_tokens=1024,
            temperature=0.0,
        )

        # Should have retried 3 times total
        assert mock_messages.create.call_count == 3
        assert response == "Success after retries"


@pytest.mark.asyncio
async def test_anthropic_client_max_retries_exceeded():
    """Test AnthropicClient raises error after max retries."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages

        # Always fail
        mock_messages.create.side_effect = Exception("Persistent API Error")

        MockAnthropic.return_value = mock_client

        client = AnthropicClient(
            auth_config=auth,
            model="claude-sonnet-4-5@20250929",
            max_retries=2,
        )

        with pytest.raises(Exception, match="Persistent API Error"):
            await client.generate(
                prompt="Test",
                max_tokens=1024,
                temperature=0.0,
            )

        # Should have tried max_retries times
        assert mock_messages.create.call_count == 2


@pytest.mark.asyncio
async def test_anthropic_client_timeout():
    """Test AnthropicClient respects timeout setting."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        client = AnthropicClient(
            auth_config=auth,
            model="claude-sonnet-4-5@20250929",
            timeout_seconds=60,
        )

        # The timeout should be passed to the Anthropic client during initialization
        # Check that timeout was configured (implementation detail)
        assert client.timeout_seconds == 60


@pytest.mark.asyncio
async def test_anthropic_client_validates_response():
    """Test AnthropicClient validates API response structure."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.anthropic_client import AnthropicClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages

        # Return invalid response (missing content)
        invalid_response = MagicMock()
        invalid_response.content = []
        mock_messages.create.return_value = invalid_response

        MockAnthropic.return_value = mock_client

        client = AnthropicClient(
            auth_config=auth,
            model="claude-sonnet-4-5@20250929",
        )

        with pytest.raises((ValueError, IndexError)):
            await client.generate(
                prompt="Test",
                max_tokens=1024,
                temperature=0.0,
            )
