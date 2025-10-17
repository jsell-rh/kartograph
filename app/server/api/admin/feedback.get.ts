/**
 * GET /api/admin/feedback
 *
 * Returns all user feedback with conversation context.
 * Requires admin access.
 */

import { eq, and, count, sql, desc, asc, isNotNull } from "drizzle-orm";
import { messageFeedback, users } from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  await requireAdmin(event);

  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const rating = (query.rating as string) || "all";
  const userId = (query.userId as string) || "";
  const hasText = query.hasText === "true";
  const sortOrder = (query.sortOrder as string) || "desc";

  // Build where conditions
  const conditions = [];

  if (rating !== "all" && (rating === "helpful" || rating === "unhelpful")) {
    conditions.push(eq(messageFeedback.rating, rating as "helpful" | "unhelpful"));
  }

  if (userId) {
    conditions.push(eq(messageFeedback.userId, userId));
  }

  if (hasText) {
    conditions.push(isNotNull(messageFeedback.feedbackText));
  }

  // Fetch feedback with user info
  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  const allFeedback = await db
    .select({
      feedback: messageFeedback,
      user: {
        id: users.id,
        name: users.name,
        email: users.email,
      },
    })
    .from(messageFeedback)
    .leftJoin(users, eq(users.id, messageFeedback.userId))
    .where(whereClause)
    .orderBy(
      sortOrder === "desc"
        ? desc(messageFeedback.createdAt)
        : asc(messageFeedback.createdAt),
    );

  const total = allFeedback.length;

  // Paginate
  const paginatedFeedback = allFeedback.slice(offset, offset + limit);

  // Calculate stats
  const statsData = await db
    .select({
      totalFeedback: count(messageFeedback.id),
      helpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'helpful' THEN 1 END)`,
      unhelpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'unhelpful' THEN 1 END)`,
      feedbackWithTextCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.feedbackText} IS NOT NULL THEN 1 END)`,
    })
    .from(messageFeedback);

  const stats = statsData[0] ?? {
    totalFeedback: 0,
    helpfulCount: 0,
    unhelpfulCount: 0,
    feedbackWithTextCount: 0,
  };

  const helpfulPercentage =
    stats.totalFeedback > 0
      ? Math.round((stats.helpfulCount / stats.totalFeedback) * 100)
      : 0;

  return {
    feedback: paginatedFeedback.map((row) => ({
      ...row.feedback,
      user: {
        id: row.user?.id ?? "",
        name: row.user?.name ?? "Unknown User",
        email: row.user?.email ?? "unknown@email.com",
      },
    })),
    total,
    hasMore: offset + limit < total,
    stats: {
      totalFeedback: stats.totalFeedback,
      helpfulCount: stats.helpfulCount,
      unhelpfulCount: stats.unhelpfulCount,
      helpfulPercentage,
      feedbackWithTextCount: stats.feedbackWithTextCount,
    },
  };
});
