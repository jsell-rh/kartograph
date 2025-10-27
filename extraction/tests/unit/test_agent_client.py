"""Unit tests for Agent SDK client."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk.types import ResultMessage


@pytest.mark.asyncio
async def test_agent_client_initialization():
    """Test AgentClient initializes with correct configuration."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="sk-ant-test-key",  # pragma: allowlist secret
    )

    client = AgentClient(
        auth_config=auth,
        model="claude-sonnet-4-5@20250929",
        allowed_tools=["Read", "Grep"],
        max_retries=3,
    )

    # Client pool is lazy-initialized, so ClaudeSDKClient not created yet
    # Just verify configuration is stored correctly
    assert client.model == "claude-sonnet-4-5@20250929"
    assert client.max_retries == 3
    assert client.allowed_tools == ["Read", "Grep"]


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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result="Test response from agent",
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        response = await client.generate(
            prompt="Test prompt",
            max_tokens=1024,
            temperature=0.0,
        )

        # Should call query with prompt and disconnect/connect for cleanup
        mock_client.query.assert_called_once_with("Test prompt")
        mock_client.disconnect.assert_called()
        mock_client.connect.assert_called()
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result="Response",
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        await client.generate(
            prompt="User prompt",
            system="You are a helpful assistant",
        )

        # Should combine system and user prompts
        call_args = mock_client.query.call_args[0][0]
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

    call_count = 0

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Fail twice, then succeed on third try
        async def mock_query(prompt):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Agent Error {call_count}")

        mock_client.query = AsyncMock(side_effect=mock_query)

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result="Success after retries",
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=3)

        response = await client.generate(prompt="Test")

        # Should have retried 3 times total
        assert call_count == 3
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(
            data_files=[Path("/test/file.py")],
            schema_dir=Path("/schemas"),
            system_instructions="Extract carefully",
        )

        # Should include schema and instructions in prompt
        call_args = mock_client.query.call_args[0][0]
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
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
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
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
    call_count = 0

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Fail once, then succeed on second try
        async def mock_query(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary error")

        mock_client.query = AsyncMock(side_effect=mock_query)

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=success_response,
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=2)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        # Should have retried
        assert call_count == 2
        assert "entities" in result


def test_agent_client_parse_json_with_surrounding_text():
    """Test AgentClient._parse_extraction_result extracts JSON from response with surrounding text (fixes the reported bug)."""
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Simulate the actual error case - conversational response with JSON embedded
    agent_response = """Complete! I've successfully extracted all 16 User entities from the RHOBS team YAML files with maximum fidelity:

**Entity Summary:**
- **16 User entities** extracted
- **URN format**: `urn:User:{org_username}` (e.g., `urn:User:anli`)
- **Role relationships**: Expressed as predicates using `hasRole` with URN references to Role entities

Here's the data:

{
  "entities": [
    {
      "@id": "urn:User:testuser",
      "@type": "User",
      "name": "Test User"
    }
  ],
  "metadata": {
    "entity_count": 1,
    "types_discovered": ["User"],
    "files_processed": 1
  }
}

All entities have been extracted successfully!"""

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient"):
        client = AgentClient(auth_config=auth)

        # Test the parsing method directly
        result = client._parse_extraction_result(agent_response)

        # Should successfully extract JSON despite surrounding text
        assert "entities" in result
        assert "metadata" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["@id"] == "urn:User:testuser"
        assert result["metadata"]["entity_count"] == 1


@pytest.mark.asyncio
async def test_agent_client_retry_with_corrective_prompt():
    """Test AgentClient retries with corrective prompt when JSON parsing fails."""
    from claude_agent_sdk.types import ResultMessage
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # First response: invalid (just text, no JSON)
    invalid_response = "I've extracted entities successfully. All done!"

    # Second response: valid JSON after corrective prompt
    valid_response = '{"entities": [{"@id": "urn:Test:1", "@type": "Test", "name": "Test"}], "metadata": {}}'

    call_count = 0
    queries = []

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_query(prompt):
            queries.append(prompt)

        mock_client.query = AsyncMock(side_effect=mock_query)

        # Create response stream that returns different responses
        async def mock_receive_response():
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                yield ResultMessage(
                    subtype="result",
                    duration_ms=100,
                    duration_api_ms=50,
                    is_error=False,
                    num_turns=1,
                    session_id="test-session",
                    result=invalid_response,
                )
            else:
                yield ResultMessage(
                    subtype="result",
                    duration_ms=100,
                    duration_api_ms=50,
                    is_error=False,
                    num_turns=1,
                    session_id="test-session",
                    result=valid_response,
                )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=2)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        # Should have called twice (initial + retry)
        assert len(queries) == 2

        # Second call should have corrective prompt asking for JSON only
        second_prompt = queries[1]
        assert "JSON" in second_prompt
        assert (
            "no explanatory text" in second_prompt.lower()
            or "only" in second_prompt.lower()
        )

        # Should successfully parse after retry
        assert "entities" in result
        assert len(result["entities"]) == 1


@pytest.mark.asyncio
async def test_agent_client_parse_json_in_generic_code_block():
    """Test AgentClient parses JSON from generic code blocks (```)."""
    from claude_agent_sdk.types import ResultMessage
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # JSON in generic code block
    agent_response = """Here's the extraction result:

```
{
  "entities": [
    {
      "@id": "urn:Service:api",
      "@type": "Service",
      "name": "API Service"
    }
  ],
  "metadata": {"entity_count": 1}
}
```
"""

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        assert "entities" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["@id"] == "urn:Service:api"


@pytest.mark.asyncio
async def test_agent_client_parse_json_with_text_before_and_after():
    """Test AgentClient extracts JSON even with text before and after."""
    from claude_agent_sdk.types import ResultMessage
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    agent_response = """Starting extraction...

Processing files...

{"entities": [{"@id": "urn:Test:1", "@type": "Test", "name": "Test"}], "metadata": {"entity_count": 1}}

Extraction complete!"""

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=agent_response,
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth)

        result = await client.extract_entities(data_files=[Path("/test/file.py")])

        assert "entities" in result
        assert result["metadata"]["entity_count"] == 1


@pytest.mark.asyncio
async def test_agent_client_max_retries_exhausted():
    """Test AgentClient raises error after max retries exhausted."""
    from claude_agent_sdk.types import ResultMessage
    from kg_extractor.config import AuthConfig
    from kg_extractor.llm.agent_client import AgentClient

    auth = AuthConfig(
        auth_method="api_key",
        api_key="test-key",  # pragma: allowlist secret
    )

    # Always return invalid response
    invalid_response = "This is never valid JSON no matter how many times you try!"

    queries = []

    with patch("kg_extractor.llm.agent_client.ClaudeSDKClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_query(prompt):
            queries.append(prompt)

        mock_client.query = AsyncMock(side_effect=mock_query)

        async def mock_receive_response():
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                result=invalid_response,
            )

        mock_client.receive_response = mock_receive_response
        MockClient.return_value = mock_client

        client = AgentClient(auth_config=auth, max_retries=3)

        with pytest.raises(ValueError, match="Could not parse agent response"):
            await client.extract_entities(data_files=[Path("/test/file.py")])

        # Should have tried max_retries times
        assert len(queries) == 3
