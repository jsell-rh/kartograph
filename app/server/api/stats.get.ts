/**
 * GET /api/stats
 *
 * Returns statistics about the Dgraph knowledge graph:
 * - Total entity count
 * - Entity counts by type
 * - Available predicates (schema)
 */

import { createLogger } from "../lib/logger";

const log = createLogger("stats-api");

export default defineEventHandler(async (event) => {
  try {
    const config = useRuntimeConfig(event);
    const dgraphUrl = config.dgraphUrl;

    log.info({ dgraphUrl }, "Fetching graph statistics");

    // Query to get total entity count and counts by type
    const query = `
      {
        total(func: has(type)) {
          count(uid)
        }

        byType(func: has(type)) {
          type
          count(uid)
        }
      }
    `;

    const response = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: query,
    });

    if (!response.ok) {
      throw new Error(
        `Dgraph query failed: ${response.status} ${response.statusText}`,
      );
    }

    const data = await response.json();

    // Extract total count
    const totalCount = data.data?.total?.[0]?.count || 0;

    // Extract counts by type
    const typeCounts: Record<string, number> = {};

    if (data.data?.byType) {
      // Group by type and sum counts
      for (const item of data.data.byType) {
        const type = item["type"];
        if (type) {
          typeCounts[type] = (typeCounts[type] || 0) + 1;
        }
      }
    }

    // Get schema (all predicates)
    const schemaQuery = `schema {}`;

    const schemaResponse = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: schemaQuery,
    });

    if (!schemaResponse.ok) {
      throw new Error(
        `Dgraph schema query failed: ${schemaResponse.status} ${schemaResponse.statusText}`,
      );
    }

    const schemaData = await schemaResponse.json();

    // Extract predicates from schema
    const predicates: string[] = [];
    if (schemaData.data?.schema) {
      for (const predicate of schemaData.data.schema) {
        if (predicate.predicate) {
          predicates.push(predicate.predicate);
        }
      }
    }

    const stats = {
      totalEntities: totalCount,
      typeBreakdown: typeCounts,
      typeCount: Object.keys(typeCounts).length,
      predicates: predicates.sort(),
      predicateCount: predicates.length,
    };

    log.info(
      {
        totalEntities: stats.totalEntities,
        typeCount: stats.typeCount,
        predicateCount: stats.predicateCount,
      },
      "Graph statistics retrieved",
    );

    return stats;
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to fetch graph statistics",
    );

    throw createError({
      statusCode: 500,
      message: "Failed to fetch graph statistics",
    });
  }
});
