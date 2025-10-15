/**
 * Audit Logger
 *
 * Logs all query executions to database for security monitoring,
 * usage analytics, and debugging.
 */

import { db } from "../db";
import { queryAuditLog, apiTokens } from "../db/schema";
import { eq } from "drizzle-orm";
import { sql } from "drizzle-orm";
import { createLogger } from "./logger";

const log = createLogger("audit-logger");

/**
 * Log a query execution to the audit log and update token metrics
 *
 * @param tokenId - API token ID
 * @param userId - User ID who owns the token
 * @param query - DQL query that was executed
 * @param executionTimeMs - Query execution time in milliseconds
 * @param success - Whether the query succeeded
 * @param errorMessage - Error message if query failed
 */
export async function logQuery(
  tokenId: string,
  userId: string,
  query: string,
  executionTimeMs: number,
  success: boolean,
  errorMessage?: string,
): Promise<void> {
  try {
    const now = new Date();

    // Insert audit log entry
    await db.insert(queryAuditLog).values({
      id: crypto.randomUUID(),
      tokenId,
      userId,
      query,
      executionTimeMs,
      success,
      errorMessage: errorMessage || null,
      timestamp: now,
    });

    // Update token metrics (increment total queries, update last used timestamp)
    await db
      .update(apiTokens)
      .set({
        totalQueries: sql`${apiTokens.totalQueries} + 1`,
        lastUsedAt: now,
      })
      .where(eq(apiTokens.id, tokenId));

    log.debug(
      {
        tokenId,
        executionTimeMs,
        success,
        queryLength: query.length,
      },
      "Query logged to audit log",
    );
  } catch (error) {
    // Don't throw - audit logging failure shouldn't break queries
    log.error(
      {
        tokenId,
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to log query to audit log",
    );
  }
}

/**
 * Get audit log entries for a token
 *
 * @param tokenId - API token ID
 * @param limit - Maximum number of entries to return
 * @returns Array of audit log entries
 */
export async function getTokenAuditLog(
  tokenId: string,
  limit: number = 100,
): Promise<
  Array<{
    id: string;
    query: string;
    executionTimeMs: number;
    success: boolean;
    errorMessage: string | null;
    timestamp: Date;
  }>
> {
  const entries = await db
    .select({
      id: queryAuditLog.id,
      query: queryAuditLog.query,
      executionTimeMs: queryAuditLog.executionTimeMs,
      success: queryAuditLog.success,
      errorMessage: queryAuditLog.errorMessage,
      timestamp: queryAuditLog.timestamp,
    })
    .from(queryAuditLog)
    .where(eq(queryAuditLog.tokenId, tokenId))
    .orderBy(queryAuditLog.timestamp)
    .limit(limit);

  return entries.map((entry) => ({
    ...entry,
    timestamp: entry.timestamp,
  }));
}

/**
 * Clean up old audit log entries based on retention policy
 *
 * @param retentionDays - Number of days to retain logs
 * @returns Number of entries deleted
 */
export async function cleanupOldAuditLogs(
  retentionDays: number,
): Promise<number> {
  try {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    // SQLite doesn't support DELETE with RETURNING, so count first
    const entriesToDelete = await db
      .select({ id: queryAuditLog.id })
      .from(queryAuditLog)
      .where(sql`${queryAuditLog.timestamp} < ${cutoffDate}`);

    if (entriesToDelete.length === 0) {
      log.debug({ retentionDays }, "No old audit logs to clean up");
      return 0;
    }

    // Delete old entries
    await db
      .delete(queryAuditLog)
      .where(sql`${queryAuditLog.timestamp} < ${cutoffDate}`);

    log.info(
      {
        deletedCount: entriesToDelete.length,
        retentionDays,
        cutoffDate: cutoffDate.toISOString(),
      },
      "Old audit logs cleaned up",
    );

    return entriesToDelete.length;
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
        retentionDays,
      },
      "Failed to clean up old audit logs",
    );
    return 0;
  }
}
