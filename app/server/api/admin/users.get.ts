/**
 * GET /api/admin/users
 *
 * Lists all users with activity statistics.
 * Requires admin access.
 */

import { eq, and, or, like, count, sql, desc, asc, inArray } from "drizzle-orm";
import {
  users,
  conversations,
  messages,
  apiTokens,
  queryAuditLog,
  messageFeedback,
} from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  // Require admin access
  await requireAdmin(event);

  // Parse query parameters
  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const status = (query.status as string) || "all";
  const role = (query.role as string) || "all";
  const search = (query.search as string) || "";
  const sortBy = (query.sortBy as string) || "createdAt";
  const sortOrder = (query.sortOrder as string) || "desc";

  // Build where conditions
  const conditions = [];

  if (status === "active") {
    conditions.push(eq(users.isActive, true));
  } else if (status === "disabled") {
    conditions.push(eq(users.isActive, false));
  }

  if (role !== "all" && (role === "user" || role === "admin")) {
    conditions.push(eq(users.role, role as "user" | "admin"));
  }

  if (search) {
    conditions.push(
      or(
        like(users.email, `%${search}%`),
        like(users.name, `%${search}%`),
      ),
    );
  }

  // Fetch all users matching filters
  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  // Determine sort column and order
  let orderByClause;
  if (sortBy === "email") {
    orderByClause = sortOrder === "desc" ? desc(users.email) : asc(users.email);
  } else if (sortBy === "lastLoginAt") {
    orderByClause = sortOrder === "desc" ? desc(users.lastLoginAt) : asc(users.lastLoginAt);
  } else {
    // Default to createdAt
    orderByClause = sortOrder === "desc" ? desc(users.createdAt) : asc(users.createdAt);
  }

  const allUsers = await db.query.users.findMany({
    where: whereClause,
    orderBy: orderByClause,
  });

  const total = allUsers.length;

  // Paginate
  const paginatedUsers = allUsers.slice(offset, offset + limit);
  const userIds = paginatedUsers.map((u) => u.id);

  if (userIds.length === 0) {
    return {
      users: [],
      total: 0,
      hasMore: false,
    };
  }

  // Get conversation counts per user
  const conversationStats = await db
    .select({
      userId: conversations.userId,
      conversationCount: count(conversations.id),
    })
    .from(conversations)
    .where(inArray(conversations.userId, userIds))
    .groupBy(conversations.userId);

  const conversationMap = new Map(
    conversationStats.map((stat) => [stat.userId, stat.conversationCount]),
  );

  // Get message counts per user (via conversations)
  const messageStats = await db
    .select({
      userId: conversations.userId,
      messageCount: count(messages.id),
    })
    .from(conversations)
    .leftJoin(messages, eq(messages.conversationId, conversations.id))
    .where(inArray(conversations.userId, userIds))
    .groupBy(conversations.userId);

  const messageMap = new Map(
    messageStats.map((stat) => [stat.userId, stat.messageCount]),
  );

  // Get API token stats per user
  const tokenStats = await db
    .select({
      userId: apiTokens.userId,
      apiTokenCount: count(apiTokens.id),
      activeApiTokenCount: sql<number>`COUNT(CASE WHEN ${apiTokens.revokedAt} IS NULL THEN 1 END)`,
    })
    .from(apiTokens)
    .where(inArray(apiTokens.userId, userIds))
    .groupBy(apiTokens.userId);

  const tokenMap = new Map(
    tokenStats.map((stat) => [
      stat.userId,
      {
        apiTokenCount: stat.apiTokenCount,
        activeApiTokenCount: stat.activeApiTokenCount,
      },
    ]),
  );

  // Get API usage stats per user
  const apiUsageStats = await db
    .select({
      userId: queryAuditLog.userId,
      totalApiCalls: count(queryAuditLog.id),
      lastQueryAt: sql<Date>`MAX(${queryAuditLog.timestamp})`,
    })
    .from(queryAuditLog)
    .where(inArray(queryAuditLog.userId, userIds))
    .groupBy(queryAuditLog.userId);

  const apiUsageMap = new Map(
    apiUsageStats.map((stat) => [
      stat.userId,
      {
        totalApiCalls: stat.totalApiCalls,
        lastQueryAt: stat.lastQueryAt,
      },
    ]),
  );

  // Get feedback stats per user
  const feedbackStats = await db
    .select({
      userId: messageFeedback.userId,
      feedbackCount: count(messageFeedback.id),
      helpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'helpful' THEN 1 END)`,
      unhelpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'unhelpful' THEN 1 END)`,
    })
    .from(messageFeedback)
    .where(inArray(messageFeedback.userId, userIds))
    .groupBy(messageFeedback.userId);

  const feedbackMap = new Map(
    feedbackStats.map((stat) => {
      const helpfulPercentage =
        stat.feedbackCount > 0
          ? Math.round((stat.helpfulCount / stat.feedbackCount) * 100)
          : 0;

      return [
        stat.userId,
        {
          feedbackCount: stat.feedbackCount,
          helpfulCount: stat.helpfulCount,
          unhelpfulCount: stat.unhelpfulCount,
          helpfulPercentage,
        },
      ];
    }),
  );

  // Combine all data
  const result = paginatedUsers.map((user) => {
    const tokens = tokenMap.get(user.id) || {
      apiTokenCount: 0,
      activeApiTokenCount: 0,
    };
    const apiUsage = apiUsageMap.get(user.id) || {
      totalApiCalls: 0,
      lastQueryAt: null,
    };
    const feedback = feedbackMap.get(user.id) || {
      feedbackCount: 0,
      helpfulCount: 0,
      unhelpfulCount: 0,
      helpfulPercentage: 0,
    };

    return {
      ...user,
      stats: {
        conversationCount: conversationMap.get(user.id) ?? 0,
        messageCount: messageMap.get(user.id) ?? 0,
        apiTokenCount: tokens.apiTokenCount,
        activeApiTokenCount: tokens.activeApiTokenCount,
        totalApiCalls: apiUsage.totalApiCalls,
        lastQueryAt: apiUsage.lastQueryAt,
        feedbackCount: feedback.feedbackCount,
        helpfulCount: feedback.helpfulCount,
        unhelpfulCount: feedback.unhelpfulCount,
        helpfulPercentage: feedback.helpfulPercentage,
      },
    };
  });

  return {
    users: result,
    total,
    hasMore: offset + limit < total,
  };
});
