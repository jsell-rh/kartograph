/**
 * GET /api/admin/changelog
 *
 * Fetches all changelog entries for admin management.
 * Includes admin-only entries and additional metadata.
 * Requires admin access.
 */

import { and, desc, eq, gte, like, or, sql } from "drizzle-orm";
import { changelogEntries } from "~/server/db/schema";
import { db } from "~/server/db/client";
import { requireAdmin } from "~/server/utils/admin";

export default defineEventHandler(async (event) => {
  // Require admin access
  await requireAdmin(event);

  // Parse query parameters
  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 100, 500);
  const offset = Number(query.offset) || 0;
  const type = (query.type as string) || "";
  const visibility = (query.visibility as string) || "";
  const search = (query.search as string) || "";
  const pinned = query.pinned ? query.pinned === "true" : undefined;

  // Build where conditions
  const conditions = [];

  // Filter by type if specified
  if (
    type &&
    ["code", "data", "maintenance", "config", "system"].includes(type)
  ) {
    conditions.push(eq(changelogEntries.type, type as any));
  }

  // Filter by visibility if specified
  if (visibility && ["public", "admin"].includes(visibility)) {
    conditions.push(eq(changelogEntries.visibility, visibility as any));
  }

  // Filter by pinned status if specified
  if (pinned !== undefined) {
    conditions.push(eq(changelogEntries.pinned, pinned));
  }

  // Search in title and description
  if (search) {
    conditions.push(
      or(
        like(changelogEntries.title, `%${search}%`),
        like(changelogEntries.description, `%${search}%`),
      ),
    );
  }

  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  // Fetch entries with pagination
  const entries = await db
    .select()
    .from(changelogEntries)
    .where(whereClause)
    .orderBy(desc(changelogEntries.pinned), desc(changelogEntries.timestamp))
    .limit(limit)
    .offset(offset);

  // Get total count for pagination
  const totalResult = await db
    .select({ count: sql<number>`count(*)` })
    .from(changelogEntries)
    .where(whereClause);

  const total = totalResult[0]?.count || 0;

  // Get counts by type for stats
  const typeCountsRaw = await db
    .select({
      type: changelogEntries.type,
      count: sql<number>`count(*)`,
    })
    .from(changelogEntries)
    .groupBy(changelogEntries.type);

  const typeCounts = typeCountsRaw.reduce(
    (acc, { type, count }) => {
      acc[type] = count;
      return acc;
    },
    {} as Record<string, number>,
  );

  return {
    entries,
    total,
    limit,
    offset,
    hasMore: offset + entries.length < total,
    stats: {
      typeCounts,
    },
  };
});
