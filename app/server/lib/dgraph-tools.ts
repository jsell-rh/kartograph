/**
 * Dgraph Tools for Anthropic Messages API
 *
 * Provides tool definitions and execution functions for querying Dgraph
 * using the Messages API (not Agent SDK).
 */

import type { Tool } from "@anthropic-ai/sdk/resources/messages";
import { createLogger, truncateForLog } from "./logger";

// Use NUXT_DGRAPH_URL for runtime override, fallback to DGRAPH_URL, then localhost
const DGRAPH_URL =
  process.env.NUXT_DGRAPH_URL ||
  process.env.DGRAPH_URL ||
  "http://localhost:8080";
const log = createLogger("dgraph-tools");

/**
 * Health check for Dgraph connectivity
 */
async function checkDgraphHealth(): Promise<{
  healthy: boolean;
  error?: string;
}> {
  try {
    log.debug({ url: DGRAPH_URL }, "Running health check");

    const response = await fetch(`${DGRAPH_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000), // 5 second timeout for health check
    });

    if (response.ok) {
      log.info(
        { url: DGRAPH_URL, status: response.status },
        "Health check PASSED",
      );
      return { healthy: true };
    } else {
      const error = `HTTP ${response.status}: ${response.statusText}`;
      log.warn({ url: DGRAPH_URL, error }, "Health check FAILED");
      return { healthy: false, error };
    }
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    log.error(
      {
        url: DGRAPH_URL,
        error: errorMessage,
        suggestion: "Dgraph server may be down or DGRAPH_URL misconfigured",
      },
      "Health check FAILED - connectivity error",
    );
    return { healthy: false, error: errorMessage };
  }
}

// Run health check on module load
checkDgraphHealth().then((result) => {
  if (!result.healthy) {
    log.warn("Dgraph is not healthy at startup. Tool calls will likely fail.");
  }
});

/**
 * Execute a DQL query against Dgraph
 */
async function executeDQL(dql: string): Promise<any> {
  const startTime = Date.now();

  try {
    log.debug(
      {
        url: DGRAPH_URL,
        queryPreview: truncateForLog(dql, 200),
        fullQuery: dql,
      },
      "Executing DQL query",
    );

    const response = await fetch(`${DGRAPH_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: dql,
      signal: AbortSignal.timeout(30000), // 30 second timeout
    });

    const elapsed = Date.now() - startTime;

    if (!response.ok) {
      log.error(
        {
          status: response.status,
          statusText: response.statusText,
          url: DGRAPH_URL,
          elapsed: `${elapsed}ms`,
        },
        "HTTP error",
      );
      throw new Error(
        `Dgraph query failed: ${response.status} ${response.statusText}`,
      );
    }

    const result = await response.json();

    if (result.errors) {
      log.error(
        {
          errors: result.errors,
          query: dql,
          elapsed: `${elapsed}ms`,
        },
        "DQL errors",
      );
      throw new Error(`DQL errors: ${JSON.stringify(result.errors)}`);
    }

    log.info(
      {
        elapsed: `${elapsed}ms`,
        resultKeys: Object.keys(result.data || {}),
        resultPreview: truncateForLog(result.data, 300),
        fullResult: result.data,
      },
      "Query successful",
    );

    return result.data;
  } catch (error) {
    const elapsed = Date.now() - startTime;

    // Check if it's a network/timeout error
    if (error instanceof TypeError && error.message.includes("fetch")) {
      log.error(
        {
          error: "Network fetch failed - Dgraph may be unreachable",
          url: DGRAPH_URL,
          elapsed: `${elapsed}ms`,
          message: error.message,
          suggestion:
            "Check DGRAPH_URL environment variable and Dgraph server status",
        },
        "CONNECTIVITY ERROR",
      );
      throw new Error(
        `Dgraph connectivity error: Cannot reach ${DGRAPH_URL}. Server may be down or URL misconfigured.`,
      );
    }

    if (
      error instanceof Error &&
      (error.name === "AbortError" || error.name === "TimeoutError")
    ) {
      log.error(
        {
          error: "Query timed out after 30 seconds",
          url: DGRAPH_URL,
          queryPreview: truncateForLog(dql, 200),
          elapsed: `${elapsed}ms`,
        },
        "TIMEOUT ERROR",
      );
      throw new Error(
        "Dgraph query timeout: Query took longer than 30 seconds",
      );
    }

    // Re-throw other errors
    throw error;
  }
}

/**
 * Tool definitions in Messages API format
 */
export const dgraphTools: Tool[] = [
  {
    name: "query_dgraph",
    description:
      "Execute a raw DQL (Dgraph Query Language) query against the knowledge graph. Use this for complex ad-hoc queries that don't fit the semantic helpers. Always mention entities using their full URN format like <urn:service:telemeter>.",
    input_schema: {
      type: "object",
      properties: {
        dql: {
          type: "string",
          description: "The complete DQL query to execute",
        },
        description: {
          type: "string",
          description: "Brief description of what this query is trying to find",
        },
      },
      required: ["dql", "description"],
    },
  },
];

/**
 * Audit context for query logging
 */
export interface AuditContext {
  tokenId: string;
  userId: string;
}

/**
 * Intelligently truncate large query results to prevent context overflow
 * Returns truncated data with metadata about truncation
 */
function truncateLargeResults(data: any, maxSizeBytes: number = 50000): {
  data: any;
  wasTruncated: boolean;
  originalCount?: number;
  truncatedCount?: number;
  message?: string;
} {
  const fullJson = JSON.stringify(data);
  const fullSize = fullJson.length;

  // If within limit, return as-is
  if (fullSize <= maxSizeBytes) {
    return { data, wasTruncated: false };
  }

  // Data is too large, need to truncate intelligently
  log.warn(
    { fullSize, maxSize: maxSizeBytes, ratio: (fullSize / maxSizeBytes).toFixed(2) },
    "Query result too large, truncating"
  );

  // For object responses with array properties, truncate the arrays
  if (typeof data === "object" && data !== null && !Array.isArray(data)) {
    const truncatedData: any = {};
    let totalOriginalCount = 0;
    let totalTruncatedCount = 0;

    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value) && value.length > 0) {
        const originalCount = value.length;
        // Calculate how many items we can keep (aim for ~1/4 of max size per key)
        const targetSizePerKey = maxSizeBytes / (4 * Object.keys(data).length);
        const avgItemSize = JSON.stringify(value[0]).length;
        const maxItems = Math.max(10, Math.floor(targetSizePerKey / avgItemSize));

        if (value.length > maxItems) {
          truncatedData[key] = value.slice(0, maxItems);
          totalOriginalCount += originalCount;
          totalTruncatedCount += maxItems;
        } else {
          truncatedData[key] = value;
          totalTruncatedCount += value.length;
        }
      } else {
        truncatedData[key] = value;
      }
    }

    if (totalOriginalCount > totalTruncatedCount) {
      return {
        data: truncatedData,
        wasTruncated: true,
        originalCount: totalOriginalCount,
        truncatedCount: totalTruncatedCount,
        message: `⚠️ RESULTS TRUNCATED: Showing ${totalTruncatedCount} of ${totalOriginalCount} total items to prevent context overflow. To see all results, refine your query with:\n- More specific filters (e.g., @filter(regexp(name, /specific-pattern/i)))\n- Use first: N in your DQL query to explicitly limit results\n- Query by specific entity UIDs if known\n- Break the query into smaller chunks by type or other criteria`
      };
    }
  }

  // Fallback: if data is array or couldn't be truncated intelligently, slice it
  if (Array.isArray(data)) {
    const maxItems = 50; // Conservative limit for top-level arrays
    if (data.length > maxItems) {
      return {
        data: data.slice(0, maxItems),
        wasTruncated: true,
        originalCount: data.length,
        truncatedCount: maxItems,
        message: `⚠️ RESULTS TRUNCATED: Showing ${maxItems} of ${data.length} total items. Refine your query to see specific results.`
      };
    }
  }

  // Last resort: return first ~half of max size as raw JSON substring (not ideal but prevents crash)
  const truncatedJson = fullJson.substring(0, maxSizeBytes / 2);
  return {
    data: { truncated: true, partial_data: truncatedJson },
    wasTruncated: true,
    message: "⚠️ RESULTS SEVERELY TRUNCATED: Response was too large. Please refine your query significantly."
  };
}

/**
 * Execute a tool by name with given input
 *
 * @param toolName - Name of the tool to execute
 * @param input - Tool input parameters
 * @param auditContext - Optional audit context for logging (used by MCP server)
 */
export async function executeTool(
  toolName: string,
  input: any,
  auditContext?: AuditContext,
): Promise<string> {
  const toolCallId = Math.random().toString(36).substring(7);
  const toolLog = log.child({ toolCallId, tool: toolName });

  toolLog.info({ input: truncateForLog(input, 100) }, "Tool called");

  if (toolName === "query_dgraph") {
    const { dql, description } = input;
    const startTime = Date.now();

    try {
      const data = await executeDQL(dql);
      const executionTimeMs = Date.now() - startTime;

      // Check if results need truncation
      const { data: finalData, wasTruncated, originalCount, truncatedCount, message } =
        truncateLargeResults(data);

      toolLog.info(
        {
          description,
          resultSize: JSON.stringify(finalData).length,
          originalSize: JSON.stringify(data).length,
          wasTruncated,
          originalCount,
          truncatedCount,
          executionTimeMs,
        },
        "Tool execution successful",
      );

      // Audit log if context provided (MCP server calls)
      if (auditContext) {
        const { logQuery } = await import("./audit-logger");
        await logQuery(
          auditContext.tokenId,
          auditContext.userId,
          dql,
          executionTimeMs,
          true,
        );
      }

      // Build response with truncation notice if needed
      const response: any = { query: description, results: finalData };
      if (wasTruncated && message) {
        response.truncation_notice = message;
      }

      return JSON.stringify(response, null, 2);
    } catch (error) {
      const executionTimeMs = Date.now() - startTime;
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      toolLog.error(
        {
          description,
          error: errorMessage,
          stack: error instanceof Error ? error.stack : undefined,
          executionTimeMs,
        },
        "Tool execution FAILED",
      );

      // Audit log failure if context provided
      if (auditContext) {
        const { logQuery } = await import("./audit-logger");
        await logQuery(
          auditContext.tokenId,
          auditContext.userId,
          dql,
          executionTimeMs,
          false,
          errorMessage,
        );
      }

      throw error; // Let caller handle the error
    }
  }

  throw new Error(`Unknown tool: ${toolName}`);
}

log.info(
  { toolCount: dgraphTools.length, tools: dgraphTools.map((t) => t.name) },
  "Dgraph tools initialized",
);
