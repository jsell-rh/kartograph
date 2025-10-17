/**
 * GET /api/admin/tokens
 *
 * Lists all API tokens across all users with usage statistics.
 * Requires admin access.
 */

import { eq, desc, asc, and, isNull, isNotNull, count, sql } from "drizzle-orm";
import { apiTokens, users, queryAuditLog } from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  await requireAdmin(event);

  // Parse query parameters
  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const status = (query.status as string) || "all"; // all | active | revoked | expired
  const sortBy = (query.sortBy as string) || "createdAt";
  const sortOrder = (query.sortOrder as string) || "desc";

  // Build where conditions
  const conditions = [];

  if (status === "active") {
    conditions.push(isNull(apiTokens.revokedAt));
    // Also check if not expired
    conditions.push(
      sql`${apiTokens.expiresAt} > ${Math.floor(Date.now() / 1000)}`,
    );
  } else if (status === "revoked") {
    conditions.push(isNotNull(apiTokens.revokedAt));
  } else if (status === "expired") {
    conditions.push(isNull(apiTokens.revokedAt));
    conditions.push(
      sql`${apiTokens.expiresAt} <= ${Math.floor(Date.now() / 1000)}`,
    );
  }

  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  // Determine sort column and order
  let orderByClause;
  if (sortBy === "name") {
    orderByClause =
      sortOrder === "desc" ? desc(apiTokens.name) : asc(apiTokens.name);
  } else if (sortBy === "lastUsedAt") {
    orderByClause =
      sortOrder === "desc"
        ? desc(apiTokens.lastUsedAt)
        : asc(apiTokens.lastUsedAt);
  } else if (sortBy === "totalQueries") {
    orderByClause =
      sortOrder === "desc"
        ? desc(apiTokens.totalQueries)
        : asc(apiTokens.totalQueries);
  } else {
    // Default to createdAt
    orderByClause =
      sortOrder === "desc"
        ? desc(apiTokens.createdAt)
        : asc(apiTokens.createdAt);
  }

  // Fetch all tokens with user information
  const allTokens = await db
    .select({
      token: apiTokens,
      user: {
        id: users.id,
        name: users.name,
        email: users.email,
      },
    })
    .from(apiTokens)
    .leftJoin(users, eq(users.id, apiTokens.userId))
    .where(whereClause)
    .orderBy(orderByClause);

  const total = allTokens.length;

  // Paginate
  const paginatedTokens = allTokens.slice(offset, offset + limit);

  // Calculate status for each token
  const now = Date.now();
  const result = paginatedTokens.map(({ token, user }) => {
    const isExpired = token.expiresAt.getTime() <= now;
    const isRevoked = token.revokedAt !== null;
    const isActive = !isExpired && !isRevoked;

    return {
      id: token.id,
      name: token.name,
      user: {
        id: user?.id ?? "",
        name: user?.name ?? "Unknown User",
        email: user?.email ?? "unknown@email.com",
      },
      totalQueries: token.totalQueries,
      lastUsedAt: token.lastUsedAt,
      expiresAt: token.expiresAt,
      createdAt: token.createdAt,
      revokedAt: token.revokedAt,
      status: isActive ? "active" : isRevoked ? "revoked" : "expired",
    };
  });

  // Calculate stats
  const statsData = await db
    .select({
      totalTokens: count(apiTokens.id),
      activeTokens: sql<number>`COUNT(CASE WHEN ${apiTokens.revokedAt} IS NULL AND ${apiTokens.expiresAt} > ${Math.floor(now / 1000)} THEN 1 END)`,
      revokedTokens: sql<number>`COUNT(CASE WHEN ${apiTokens.revokedAt} IS NOT NULL THEN 1 END)`,
      expiredTokens: sql<number>`COUNT(CASE WHEN ${apiTokens.revokedAt} IS NULL AND ${apiTokens.expiresAt} <= ${Math.floor(now / 1000)} THEN 1 END)`,
    })
    .from(apiTokens);

  const stats = statsData[0] ?? {
    totalTokens: 0,
    activeTokens: 0,
    revokedTokens: 0,
    expiredTokens: 0,
  };

  return {
    tokens: result,
    total,
    hasMore: offset + limit < total,
    stats,
  };
});
