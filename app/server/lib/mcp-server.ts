/**
 * MCP Server Instance
 *
 * Exposes query_dgraph tool and kartograph-init prompt via Model Context Protocol
 * for remote access from Claude Code and other MCP clients.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { executeTool, type AuditContext } from "./dgraph-tools.js";
import { createLogger } from "./logger.js";
import { buildMCPInitPrompt } from "./system-prompt.js";

const log = createLogger("mcp-server");

/**
 * Create and configure MCP server instance
 *
 * @param auditContext - Audit context for query logging (tokenId, userId)
 * @param serverName - Server name for identification
 * @param version - Server version
 * @returns Configured MCP server
 */
export function createMCPServer(
  auditContext?: AuditContext,
  serverName: string = "kartograph-dgraph",
  version: string = "1.0.0",
) {
  const server = new Server(
    {
      name: serverName,
      version,
    },
    {
      capabilities: {
        tools: {},
        prompts: {},
      },
    },
  );

  log.info({ serverName, version }, "MCP server created");

  /**
   * Handle tools/list request
   *
   * Returns list of available tools (just query_dgraph)
   */
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    log.debug("Received tools/list request");

    return {
      tools: [
        {
          name: "query_dgraph",
          description:
            "Execute a DQL (Dgraph Query Language) query against the knowledge graph. Use this to explore entities, relationships, and metadata in the Red Hat service topology. Always reference entities using their full URN format like <urn:Service:telemeter-server>.",
          inputSchema: {
            type: "object",
            properties: {
              dql: {
                type: "string",
                description:
                  "The complete DQL query to execute. Must be a read-only query (no mutations).",
              },
              description: {
                type: "string",
                description:
                  "Brief description of what this query is trying to find (helps with logging and debugging)",
              },
            },
            required: ["dql", "description"],
          },
        },
      ],
    };
  });

  /**
   * Handle tools/call request
   *
   * Executes the requested tool and returns results
   */
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    log.info(
      {
        toolName: name,
        description: args?.description || "No description",
        hasAuditContext: !!auditContext,
      },
      "Received tools/call request",
    );

    if (name !== "query_dgraph") {
      log.error({ toolName: name }, "Unknown tool requested");
      throw new Error(`Unknown tool: ${name}`);
    }

    try {
      // Execute the tool with audit context (handles logging internally)
      const result = await executeTool("query_dgraph", args, auditContext);

      log.info(
        {
          toolName: name,
          resultLength: result.length,
        },
        "Tool execution successful",
      );

      return {
        content: [
          {
            type: "text",
            text: result,
          },
        ],
        isError: false,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      log.error(
        {
          toolName: name,
          error: errorMessage,
        },
        "Tool execution failed",
      );

      // Return error as MCP tool result
      return {
        content: [
          {
            type: "text",
            text: `Error executing query: ${errorMessage}`,
          },
        ],
        isError: true,
      };
    }
  });

  /**
   * Handle prompts/list request
   *
   * Returns list of available prompts (kartograph-init)
   */
  server.setRequestHandler(ListPromptsRequestSchema, async () => {
    log.debug("Received prompts/list request");

    return {
      prompts: [
        {
          name: "kartograph-init",
          description:
            "Initialize Claude Code with essential context about the Kartograph knowledge graph. Provides graph statistics, entity types, predicates, query best practices, and formatting guidelines optimized for CLI interaction.",
          arguments: [],
        },
      ],
    };
  });

  /**
   * Handle prompts/get request
   *
   * Returns the MCP initialization prompt for kartograph-init
   */
  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const { name } = request.params;

    log.info({ promptName: name }, "Received prompts/get request");

    if (name !== "kartograph-init") {
      log.error({ promptName: name }, "Unknown prompt requested");
      throw new Error(`Unknown prompt: ${name}`);
    }

    try {
      // Build MCP-specific initialization prompt with current graph stats
      const initPrompt = await buildMCPInitPrompt();

      log.info(
        {
          promptName: name,
          promptLength: initPrompt.length,
        },
        "Prompt generated successfully",
      );

      return {
        description: "Kartograph initialization context for Claude Code",
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: "Initialize context for the Kartograph knowledge graph.",
            },
          },
          {
            role: "assistant",
            content: {
              type: "text",
              text: initPrompt,
            },
          },
        ],
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      log.error(
        {
          promptName: name,
          error: errorMessage,
        },
        "Prompt generation failed",
      );

      throw new Error(`Failed to generate prompt: ${errorMessage}`);
    }
  });

  log.info("MCP server request handlers configured");

  return server;
}
