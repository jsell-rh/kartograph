/**
 * Query Validator
 *
 * Validates DQL queries to ensure they are read-only.
 * Prevents mutation operations (set, delete, upsert) via API tokens.
 */

import { createLogger } from "./logger";

const log = createLogger("query-validator");

/**
 * Regex pattern to detect mutation operations in DQL queries
 *
 * Matches:
 * - set { ... }
 * - delete { ... }
 * - upsert { ... }
 * - mutation keyword
 */
const MUTATION_PATTERN = /\b(set\s*\{|delete\s*\{|upsert\s*\{|mutation)/i;

/**
 * Validate that a DQL query is read-only
 *
 * @param dql - The DQL query to validate
 * @returns Validation result with error message if invalid
 */
export function validateReadOnlyQuery(dql: string): {
  valid: boolean;
  error?: string;
} {
  // Check for mutation keywords
  if (MUTATION_PATTERN.test(dql)) {
    const match = dql.match(MUTATION_PATTERN);
    const mutationType = match?.[1]?.trim() || "unknown";

    log.warn(
      {
        mutationType,
        queryPreview: dql.substring(0, 100),
      },
      "Mutation operation detected in query",
    );

    return {
      valid: false,
      error: `Mutation operations are not allowed. Detected: ${mutationType}. Only read-only queries permitted.`,
    };
  }

  // Additional validation could be added here:
  // - Max query length (prevent DOS)
  // - Banned predicates (sensitive data)
  // - Query complexity limits
  // - etc.

  return { valid: true };
}
