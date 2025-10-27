"""Shared test fixtures for unit tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.fixture(autouse=True)
def reset_agent_client_state():
    """Reset AgentClient class-level state between tests to prevent pollution."""
    from kg_extractor.llm.agent_client import AgentClient

    # Reset class-level state before each test
    AgentClient._rate_limit_semaphore = None
    AgentClient._rate_limited_until = None
    AgentClient._semaphore_lock = None
    AgentClient._client_pool = None
    AgentClient._shared_mcp_server = None

    yield

    # Clean up after test
    AgentClient._rate_limit_semaphore = None
    AgentClient._rate_limited_until = None
    AgentClient._semaphore_lock = None
    AgentClient._client_pool = None
    AgentClient._shared_mcp_server = None


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server for testing."""
    mock_server = MagicMock()
    mock_server.server = MagicMock()
    mock_server.server.name = "test-extraction-server"
    return mock_server


@pytest.fixture
async def mock_client_pool(mock_mcp_server):
    """
    Create a mock client pool with a single mock client.

    This fixture handles the complex setup of mocking the new client pool architecture:
    - Shared MCP server
    - asyncio.Queue-based client pool
    - Mock ClaudeSDKClient that returns predictable responses
    """
    # Create mock client
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.query = AsyncMock()

    # Mock receive_response to return nothing by default (tests override this)
    async def default_receive_response():
        if False:  # Make this a generator
            yield
        return

    mock_client.receive_response = default_receive_response

    # Create a real asyncio.Queue with the mock client
    queue = asyncio.Queue(maxsize=1)
    await queue.put(mock_client)

    return {
        "queue": queue,
        "mock_client": mock_client,
        "mock_mcp_server": mock_mcp_server,
    }


@pytest.fixture
def mock_agent_sdk_infrastructure():
    """
    Mock the Agent SDK infrastructure for testing.

    Returns a context manager that mocks both the MCP server and ClaudeSDKClient.
    Tests can customize the mock_client's behavior before calling agent methods.
    """
    from unittest.mock import patch

    class MockContext:
        def __init__(self):
            self.mock_mcp = None
            self.mock_client = None
            self.MockMCPServer = None
            self.MockClient = None

        def __enter__(self):
            # Patch the MCP server
            self.mcp_patcher = patch(
                "kg_extractor.llm.extraction_mcp_server.ExtractionResultServer"
            )
            self.MockMCPServer = self.mcp_patcher.__enter__()

            # Patch ClaudeSDKClient
            self.client_patcher = patch("kg_extractor.llm.agent_client.ClaudeSDKClient")
            self.MockClient = self.client_patcher.__enter__()

            # Setup mock MCP server
            self.mock_mcp = MagicMock()
            self.mock_mcp.server = MagicMock()
            self.MockMCPServer.return_value = self.mock_mcp

            # Setup mock client
            self.mock_client = AsyncMock()
            self.mock_client.connect = AsyncMock()
            self.mock_client.query = AsyncMock()
            self.MockClient.return_value = self.mock_client

            return self

        def __exit__(self, *args):
            self.client_patcher.__exit__(*args)
            self.mcp_patcher.__exit__(*args)

    return MockContext()
