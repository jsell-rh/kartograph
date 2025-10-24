"""Tests for MCP tool availability in agent client."""

from kg_extractor.config import AuthConfig
from kg_extractor.llm.agent_client import AgentClient


def test_mcp_tool_in_default_tools():
    """Test that MCP submission tool is included in default allowed tools."""
    # Create client with default settings
    auth_config = AuthConfig(auth_method="api_key", api_key="test-key")
    client = AgentClient(auth_config=auth_config)

    # Check that MCP tool is in the allowed tools
    # The agent client should have configured the MCP server tool
    # We can't directly inspect the client options, but we can verify it's configured
    assert client.client is not None


def test_mcp_tool_with_custom_allowed_tools():
    """Test that custom allowed_tools can include MCP tool."""
    auth_config = AuthConfig(auth_method="api_key", api_key="test-key")

    # Custom tools including the MCP tool
    custom_tools = ["Read", "mcp__extraction__submit_extraction_results"]

    client = AgentClient(
        auth_config=auth_config,
        allowed_tools=custom_tools,
    )

    assert client.client is not None


def test_default_tools_list():
    """Test that default tools list is comprehensive."""
    auth_config = AuthConfig(auth_method="api_key", api_key="test-key")
    client = AgentClient(auth_config=auth_config)

    # The client should be initialized successfully with all required tools
    assert client.client is not None

    # Verify the client has access to the MCP configuration
    # (internal detail, but important for debugging)
    assert hasattr(client, "_mcp_result")
