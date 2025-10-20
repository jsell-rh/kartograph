/**
 * GET /api/changelog
 *
 * Fetches unified changelog entries (operational + git releases).
 * Public endpoint - filters visibility based on user auth.
 */

import { and, desc, eq, gte, or, sql } from "drizzle-orm";
import { changelogEntries } from "~/server/db/schema";
import { db } from "~/server/db/client";
import { auth } from "~/server/lib/auth";

export default defineEventHandler(async (event) => {
  // Check if user is authenticated (optional - public can see public entries)
  const session = await auth.api.getSession({ headers: event.headers });
  const isAdmin = session?.user?.role === "admin";

  // Parse query parameters
  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const type = (query.type as string) || "";
  const since = query.since ? new Date(query.since as string) : undefined;

  // Build where conditions
  const conditions = [];

  // Filter by visibility (admins see all, others see only public)
  if (!isAdmin) {
    conditions.push(eq(changelogEntries.visibility, "public"));
  }

  // Filter by type if specified
  if (
    type &&
    ["code", "data", "maintenance", "config", "system"].includes(type)
  ) {
    conditions.push(eq(changelogEntries.type, type as any));
  }

  // Filter by timestamp if specified
  if (since) {
    conditions.push(gte(changelogEntries.timestamp, since));
  }

  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  // Fetch entries with pagination
  // Pinned entries first, then sorted by timestamp DESC
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

  return {
    entries,
    total,
    limit,
    offset,
    hasMore: offset + entries.length < total,
  };
});
