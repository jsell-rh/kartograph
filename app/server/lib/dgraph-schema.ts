/**
 * Dgraph Schema Introspection
 *
 * Provides utilities for querying and caching Dgraph schema metadata,
 * particularly for discovering predicates with @reverse directive.
 */

import { createLogger } from "./logger";

const log = createLogger("dgraph-schema");

// Use NUXT_DGRAPH_URL for runtime override, fallback to DGRAPH_URL, then localhost
const DGRAPH_URL =
  process.env.NUXT_DGRAPH_URL ||
  process.env.DGRAPH_URL ||
  "http://localhost:8080";

/**
 * Cache for reverse predicates
 * TTL: 5 minutes (schema changes are rare)
 */
interface SchemaCache {
  reversePredicates: string[];
  lastFetched: number;
  ttl: number; // milliseconds
}

const schemaCache: SchemaCache = {
  reversePredicates: [],
  lastFetched: 0,
  ttl: 5 * 60 * 1000, // 5 minutes
};

/**
 * Query Dgraph schema to get all predicates with @reverse directive
 */
async function fetchReversePredicates(): Promise<string[]> {
  try {
    log.debug({ url: DGRAPH_URL }, "Fetching Dgraph schema");

    // Query the schema
    const schemaQuery = "schema {}";

    const response = await fetch(`${DGRAPH_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: schemaQuery,
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      throw new Error(
        `Schema query failed: ${response.status} ${response.statusText}`,
      );
    }

    const result = await response.json();

    if (result.errors) {
      throw new Error(`Schema query errors: ${JSON.stringify(result.errors)}`);
    }

    // Parse schema to find predicates with @reverse
    const reversePredicates: string[] = [];

    if (result.data && result.data.schema) {
      for (const predicate of result.data.schema) {
        // Check if predicate has @reverse directive
        if (predicate.reverse === true) {
          // Extract predicate name (without urn:predicate: prefix if present)
          const predicateName = predicate.predicate
            .replace(/^<?urn:predicate:/, "")
            .replace(/>?$/, "");

          reversePredicates.push(predicateName);
        }
      }
    }

    log.info(
      { count: reversePredicates.length, predicates: reversePredicates },
      "Reverse predicates discovered from schema",
    );

    return reversePredicates;
  } catch (error) {
    log.error(
      { error: error instanceof Error ? error.message : error },
      "Failed to fetch schema",
    );
    throw error;
  }
}

/**
 * Get all predicates with @reverse directive (with caching)
 *
 * Returns cached predicates if cache is still valid,
 * otherwise fetches fresh schema and updates cache.
 */
export async function getReversePredicates(): Promise<string[]> {
  const now = Date.now();
  const cacheAge = now - schemaCache.lastFetched;

  // Return cached predicates if cache is still valid
  if (
    schemaCache.reversePredicates.length > 0 &&
    cacheAge < schemaCache.ttl
  ) {
    log.debug(
      {
        cacheAge: `${Math.floor(cacheAge / 1000)}s`,
        count: schemaCache.reversePredicates.length,
      },
      "Using cached reverse predicates",
    );
    return schemaCache.reversePredicates;
  }

  // Cache is stale or empty, fetch fresh schema
  log.info("Schema cache expired or empty, fetching fresh schema");

  try {
    const predicates = await fetchReversePredicates();

    // Update cache
    schemaCache.reversePredicates = predicates;
    schemaCache.lastFetched = now;

    return predicates;
  } catch (error) {
    // If fetch fails but we have stale cache, use it as fallback
    if (schemaCache.reversePredicates.length > 0) {
      log.warn(
        {
          cacheAge: `${Math.floor(cacheAge / 1000)}s`,
          count: schemaCache.reversePredicates.length,
        },
        "Schema fetch failed, using stale cache as fallback",
      );
      return schemaCache.reversePredicates;
    }

    // No cache available, re-throw error
    throw error;
  }
}

/**
 * Get all relationship (uid-type) predicates from schema
 */
export async function getRelationshipPredicates(): Promise<string[]> {
  try {
    log.debug({ url: DGRAPH_URL }, "Fetching relationship predicates from schema");

    const schemaQuery = "schema {}";

    const response = await fetch(`${DGRAPH_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: schemaQuery,
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(
        `Schema query failed: ${response.status} ${response.statusText}`,
      );
    }

    const result = await response.json();

    if (result.errors) {
      throw new Error(`Schema query errors: ${JSON.stringify(result.errors)}`);
    }

    // Get all uid-type predicates (relationships)
    const relationshipPredicates: string[] = [];

    if (result.data && result.data.schema) {
      for (const predicate of result.data.schema) {
        // Only include uid-type predicates (relationships, not scalars)
        if (predicate.type === "uid") {
          const predicateName = predicate.predicate
            .replace(/^<?urn:predicate:/, "")
            .replace(/>?$/, "");

          relationshipPredicates.push(predicateName);
        }
      }
    }

    log.info(
      { count: relationshipPredicates.length, predicates: relationshipPredicates },
      "Relationship predicates discovered from schema",
    );

    return relationshipPredicates;
  } catch (error) {
    log.error(
      { error: error instanceof Error ? error.message : error },
      "Failed to fetch relationship predicates",
    );
    throw error;
  }
}

/**
 * Build a DQL query for outgoing relationships using all uid-type predicates
 *
 * @param entityType - The type of the entity
 * @param entityId - The ID/name of the entity
 * @param relationshipPredicates - List of uid-type predicates
 * @returns DQL query string
 */
export function buildOutgoingRelationshipsQuery(
  entityType: string,
  entityId: string,
  relationshipPredicates: string[],
): string {
  // Build field list for all relationship predicates
  const predicateFields = relationshipPredicates.map((predicate) => {
    return `    ${predicate} {
      uid
      name
      type
    }`;
  });

  return `
  {
    entity(func: eq(type, "${entityType}")) @filter(eq(name, "${entityId}")) {
      uid
      name
      type
${predicateFields.join("\n")}
    }
  }
`;
}

/**
 * Build a DQL query for incoming relationships using all reverse predicates
 *
 * @param sourceUid - The UID of the source entity
 * @param reversePredicates - List of predicates with @reverse directive
 * @returns DQL query string
 */
export function buildIncomingRelationshipsQuery(
  sourceUid: string,
  reversePredicates: string[],
): string {
  // Build query blocks for each reverse predicate
  const queryBlocks = reversePredicates.map((predicate) => {
    return `
    ${predicate}(func: uid(${sourceUid})) {
      ~${predicate} {
        uid
        name
        type
      }
    }`;
  });

  // Combine all blocks into single query
  return `
  {
${queryBlocks.join("\n")}
  }
`;
}

/**
 * Clear the schema cache (useful for testing or after schema updates)
 */
export function clearSchemaCache(): void {
  schemaCache.reversePredicates = [];
  schemaCache.lastFetched = 0;
  log.info("Schema cache cleared");
}

log.info(
  { url: DGRAPH_URL, cacheTTL: `${schemaCache.ttl / 1000}s` },
  "Dgraph schema introspection initialized",
);
