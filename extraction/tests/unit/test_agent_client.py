"""Unit tests for Agent SDK client."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_agent_client_initialization():
    """Test AgentClient initializes with correct configuration."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="sk-ant-test-key",  # pragma: allowlist secret
    )

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        client = AgentClient(
            auth_config=auth,
            model="claude-sonnet-4-5@20250929",
            allowed_tools=["Read", "Grep"],
            max_retries=3,
        )

        # Should create ClaudeSDKClient
        MockClient.assert_called_once()
        assert client.model == "claude-sonnet-4-5@20250929"
        assert client.max_retries == 3


@pytest.mark.asyncio
async def test_agent_client_generate_basic():
    """Test AgentClient.generate() with basic prompt."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value="Test response from agent")
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        response = await client.generate(
            prompt="Test prompt",
            max_tokens=1024,
            temperature=0.0,
        )

        # Should call send_message
        mock_client.send_message.assert_called_once_with("Test prompt")
        assert response == "Test response from agent"


@pytest.mark.asyncio
async def test_agent_client_generate_with_system():
    """Test AgentClient.generate() with system prompt."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value="Response")
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        await client.generate(
            prompt="User prompt",
            system="You are a helpful assistant",
        )

        # Should combine system and user prompts
        call_args = mock_client.send_message.call_args[0][0]
        assert "You are a helpful assistant" in call_args
        assert "User prompt" in call_args


@pytest.mark.asyncio
async def test_agent_client_generate_retry_on_failure():
    """Test AgentClient retries on failures."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()

        # Fail twice, then succeed
        mock_client.send_message = AsyncMock(
            side_effect=[
                Exception("Agent Error 1"),
                Exception("Agent Error 2"),
                "Success after retries",
            ]
        )

        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=3)

        response = await client.generate(prompt="Test")

        # Should have retried 3 times total
        assert mock_client.send_message.call_count == 3
        assert response == "Success after retries"


@pytest.mark.asyncio
async def test_agent_client_extract_entities_basic():
    """Test AgentClient.extract_entities() with basic file list."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Mock agent response with JSON
    agent_response = """
```json
{
  "entities": [
    {
      "@id": "urn:Service:payment-api",
      "@type": "Service",
      "name": "Payment API"
    }
  ],
  "metadata": {
    "entity_count": 1,
    "types_discovered": ["Service"]
  }
}
```
"""

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=agent_response)
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(
            data_files=[Path("/test/file1.py"), Path("/test/file2.py")],
        )

        # Should return parsed entities
        assert "entities" in result
        assert "metadata" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["@id"] == "urn:Service:payment-api"
        assert result["metadata"]["entity_count"] == 1


@pytest.mark.asyncio
async def test_agent_client_extract_entities_with_schema():
    """Test AgentClient.extract_entities() with schema directory."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    agent_response = """
{
  "entities": [],
  "metadata": {"entity_count": 0}
}
"""

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=agent_response)
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(
            data_files=[Path("/test/file.py")],
            schema_dir=Path("/schemas"),
            system_instructions="Extract carefully",
        )

        # Should include schema and instructions in prompt
        call_args = mock_client.send_message.call_args[0][0]
        assert "/schemas" in call_args
        assert "Extract carefully" in call_args
        assert "/test/file.py" in call_args


@pytest.mark.asyncio
async def test_agent_client_extract_entities_parse_raw_json():
    """Test AgentClient parses raw JSON (no markdown block)."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Raw JSON response (no markdown)
    agent_response = '{"entities": [], "metadata": {}}'

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=agent_response)
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        assert "entities" in result
        assert "metadata" in result


@pytest.mark.asyncio
async def test_agent_client_extract_entities_invalid_json():
    """Test AgentClient raises error on invalid JSON response."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Invalid JSON
    agent_response = "This is not JSON at all!"

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=agent_response)
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        with pytest.raises(ValueError, match="Could not parse agent response"):
            await client.extract_entities(data_files=[Path("/test/file.py")])


@pytest.mark.asyncio
async def test_agent_client_extract_entities_missing_entities_field():
    """Test AgentClient raises error when response missing entities field."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Missing 'entities' field
    agent_response = '{"metadata": {}}'

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=agent_response)
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        with pytest.raises(ValueError, match="missing 'entities' field"):
            await client.extract_entities(data_files=[Path("/test/file.py")])


@pytest.mark.asyncio
async def test_agent_client_extract_entities_retry():
    """Test AgentClient retries extraction on failures."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    success_response = '{"entities": [], "metadata": {}}'

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = MagicMock()

        # Fail once, then succeed
        mock_client.send_message = AsyncMock(
            side_effect=[Exception("Temporary error"), success_response]
        )

        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=2)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        # Should have retried
        assert mock_client.send_message.call_count == 2
        assert "entities" in result
