"""MCP server providing extraction result submission tool.

This server provides a custom tool that enforces structured JSON output from the agent.
Instead of returning free-form text, the agent must call the submit_extraction_results
tool with properly structured entities and metadata.
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class ExtractionResultServer:
    """
    MCP server for extraction result submission.

    Provides a single tool: submit_extraction_results
    This tool enforces the JSON structure by requiring structured parameters.
    """

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("extraction-results")
        self.result: dict[str, Any] | None = None
        self.result_event = asyncio.Event()

        # Register tool
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="submit_extraction_results",
                    description=(
                        "Submit extraction results with entities and metadata. "
                        "This is the ONLY way to return extraction results. "
                        "You MUST use this tool to submit your findings."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "description": "List of extracted entities with @id, @type, name, and predicates",
                                "items": {
                                    "type": "object",
                                    "required": ["@id", "@type", "name"],
                                    "properties": {
                                        "@id": {
                                            "type": "string",
                                            "pattern": "^urn:[A-Z][a-zA-Z0-9_]*:.+$",
                                            "description": "URN identifier (format: urn:Type:identifier)",
                                        },
                                        "@type": {
                                            "type": "string",
                                            "pattern": "^[A-Z][a-zA-Z0-9_]*$",
                                            "description": "Entity type (must start with capital letter)",
                                        },
                                        "name": {
                                            "type": "string",
                                            "description": "Entity name",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Optional entity description",
                                        },
                                    },
                                    "additionalProperties": True,
                                },
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Extraction metadata (entity_count, types_discovered, etc.)",
                                "properties": {
                                    "entity_count": {
                                        "type": "integer",
                                        "description": "Total number of entities extracted",
                                    },
                                    "types_discovered": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of entity types found",
                                    },
                                    "files_processed": {
                                        "type": "integer",
                                        "description": "Number of files processed",
                                    },
                                },
                                "additionalProperties": True,
                            },
                        },
                        "required": ["entities", "metadata"],
                    },
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            if name != "submit_extraction_results":
                raise ValueError(f"Unknown tool: {name}")

            # Validate and store the result
            entities = arguments.get("entities", [])
            metadata = arguments.get("metadata", {})

            # Store result for retrieval
            self.result = {
                "entities": entities,
                "metadata": metadata,
            }

            # Signal that result is ready
            self.result_event.set()

            # Return confirmation
            entity_count = len(entities)
            types_found = set(e.get("@type", "Unknown") for e in entities)

            return [
                TextContent(
                    type="text",
                    text=f"✓ Successfully submitted {entity_count} entities of {len(types_found)} types. Results recorded.",
                )
            ]

    async def get_result(self, timeout: float = 300.0) -> dict[str, Any]:
        """
        Wait for and retrieve the extraction result.

        Args:
            timeout: Maximum time to wait for result in seconds

        Returns:
            The extraction result with entities and metadata

        Raises:
            TimeoutError: If no result received within timeout
            ValueError: If no result was submitted
        """
        try:
            await asyncio.wait_for(self.result_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No extraction result submitted within {timeout} seconds. "
                "The agent must call submit_extraction_results tool."
            )

        if self.result is None:
            raise ValueError("No result available")

        return self.result

    def reset(self) -> None:
        """Reset result state for next extraction."""
        self.result = None
        self.result_event.clear()

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Main entry point for standalone server."""
    server = ExtractionResultServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
