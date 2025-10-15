/**
 * POST /api/mcp
 *
 * HTTP transport for MCP (Model Context Protocol) server
 * Handles JSON-RPC 2.0 requests for tool listing and execution
 *
 * Security layers:
 * 1. Token authentication (via middleware)
 * 2. Rate limiting (sliding window per token)
 * 3. Query validation (read-only enforcement)
 * 4. Audit logging (all queries logged to database)
 */

import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMCPServer } from "../lib/mcp-server.js";
import { validateReadOnlyQuery } from "../lib/query-validator.js";
import { checkRateLimit } from "../lib/rate-limiter.js";
import { createLogger } from "../lib/logger.js";

const log = createLogger("mcp-http");

export default defineEventHandler(async (event) => {
  // Token already validated by middleware (tokenAuth.ts)
  const { tokenId, userId, tokenName } = event.context.tokenAuth;

  const config = useRuntimeConfig(event);

  try {
    // Parse request body
    const body = await readBody(event);

    log.info(
      {
        tokenId,
        tokenName,
        method: body.method,
        requestId: body.id,
      },
      "MCP request received",
    );

    // SECURITY LAYER 1: Rate Limiting
    const rateLimit = checkRateLimit(tokenId, config.apiTokenRateLimit);
    if (!rateLimit.allowed) {
      setResponseStatus(event, 429);
      setHeader(event, "Retry-After", rateLimit.retryAfter || 60);

      log.warn(
        {
          tokenId,
          tokenName,
          retryAfter: rateLimit.retryAfter,
          currentCount: rateLimit.currentCount,
        },
        "Rate limit exceeded",
      );

      // Return JSON-RPC error for rate limit
      return {
        jsonrpc: "2.0",
        id: body.id || null,
        error: {
          code: 429,
          message: `Rate limit exceeded. You have made ${rateLimit.currentCount} queries in the last hour. Please retry after ${rateLimit.retryAfter} seconds.`,
          data: {
            retryAfter: rateLimit.retryAfter,
            limit: config.apiTokenRateLimit,
          },
        },
      };
    }

    // SECURITY LAYER 2: Query Validation (read-only enforcement)
    if (body.method === "tools/call" && body.params?.name === "query_dgraph") {
      const dql = body.params.arguments?.dql;

      if (dql) {
        const validation = validateReadOnlyQuery(dql);
        if (!validation.valid) {
          log.warn(
            {
              tokenId,
              tokenName,
              error: validation.error,
              queryPreview: dql.substring(0, 100),
            },
            "Query validation failed - mutation detected",
          );

          // Return JSON-RPC error for validation failure
          return {
            jsonrpc: "2.0",
            id: body.id || null,
            error: {
              code: 403,
              message: validation.error,
            },
          };
        }
      }
    }

    // Create per-request MCP server with audit context
    // The audit context flows through to executeTool via closure
    const server = createMCPServer({ tokenId, userId });

    // Create per-request HTTP transport instance
    const transport = new StreamableHTTPServerTransport({
      enableJsonResponse: true,
    } as any); // SDK type compatibility

    // Connect server to transport
    await server.connect(transport);

    // Handle the request
    // IMPORTANT: This writes directly to event.node.res
    // Mark the response as already handled so Nuxt doesn't try to send another response
    event._handled = true;

    await transport.handleRequest(event.node.req, event.node.res, body);

    log.info(
      {
        tokenId,
        tokenName,
        method: body.method,
        requestId: body.id,
      },
      "MCP request completed",
    );

    // Query audit logging happens inside executeTool via auditContext

    // Return nothing - response already sent by transport
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);

    log.error(
      {
        tokenId: event.context.tokenAuth?.tokenId,
        error: errorMessage,
        stack: error instanceof Error ? error.stack : undefined,
      },
      "MCP request failed",
    );

    throw createError({
      statusCode: 500,
      message: "Internal server error",
    });
  }
});
