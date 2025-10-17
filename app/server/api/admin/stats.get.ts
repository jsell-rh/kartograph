/**
 * GET /api/admin/stats
 *
 * Returns dashboard statistics for admin overview.
 * Requires admin access.
 */

import { eq, count, sql, gte } from "drizzle-orm";
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
  await requireAdmin(event);

  // Calculate timestamps for time-based queries
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  // Get user statistics
  const userStats = await db
    .select({
      totalUsers: count(users.id),
      activeUsers: sql<number>`COUNT(CASE WHEN ${users.isActive} = 1 THEN 1 END)`,
      disabledUsers: sql<number>`COUNT(CASE WHEN ${users.isActive} = 0 THEN 1 END)`,
      adminUsers: sql<number>`COUNT(CASE WHEN ${users.role} = 'admin' THEN 1 END)`,
      usersCreatedLast30Days: sql<number>`COUNT(CASE WHEN ${users.createdAt} >= ${thirtyDaysAgo} THEN 1 END)`,
    })
    .from(users);

  // Get conversation statistics
  const conversationStats = await db
    .select({
      totalConversations: count(conversations.id),
      conversationsLast30Days: sql<number>`COUNT(CASE WHEN ${conversations.createdAt} >= ${thirtyDaysAgo} THEN 1 END)`,
    })
    .from(conversations);

  // Get message statistics
  const messageStats = await db
    .select({
      totalMessages: count(messages.id),
      messagesLast30Days: sql<number>`COUNT(CASE WHEN ${messages.createdAt} >= ${thirtyDaysAgo} THEN 1 END)`,
    })
    .from(messages);

  // Get API token statistics
  const tokenStats = await db
    .select({
      totalApiTokens: count(apiTokens.id),
      activeApiTokens: sql<number>`COUNT(CASE WHEN ${apiTokens.revokedAt} IS NULL THEN 1 END)`,
    })
    .from(apiTokens);

  // Get API call statistics
  const apiCallStats = await db
    .select({
      totalApiCalls: count(queryAuditLog.id),
      apiCallsLast30Days: sql<number>`COUNT(CASE WHEN ${queryAuditLog.timestamp} >= ${thirtyDaysAgo} THEN 1 END)`,
    })
    .from(queryAuditLog);

  // Get feedback statistics
  const feedbackStatsData = await db
    .select({
      totalFeedback: count(messageFeedback.id),
      helpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'helpful' THEN 1 END)`,
      unhelpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'unhelpful' THEN 1 END)`,
      recentUnhelpfulCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.rating} = 'unhelpful' AND ${messageFeedback.createdAt} >= ${sevenDaysAgo} THEN 1 END)`,
      feedbackWithTextCount: sql<number>`COUNT(CASE WHEN ${messageFeedback.feedbackText} IS NOT NULL THEN 1 END)`,
    })
    .from(messageFeedback);

  const feedbackStats = feedbackStatsData[0] ?? {
    totalFeedback: 0,
    helpfulCount: 0,
    unhelpfulCount: 0,
    recentUnhelpfulCount: 0,
    feedbackWithTextCount: 0,
  };

  const helpfulPercentage =
    feedbackStats.totalFeedback > 0
      ? Math.round((feedbackStats.helpfulCount / feedbackStats.totalFeedback) * 100)
      : 0;

  return {
    totalUsers: userStats[0]?.totalUsers ?? 0,
    activeUsers: userStats[0]?.activeUsers ?? 0,
    disabledUsers: userStats[0]?.disabledUsers ?? 0,
    adminUsers: userStats[0]?.adminUsers ?? 0,
    totalConversations: conversationStats[0]?.totalConversations ?? 0,
    totalMessages: messageStats[0]?.totalMessages ?? 0,
    totalApiTokens: tokenStats[0]?.totalApiTokens ?? 0,
    activeApiTokens: tokenStats[0]?.activeApiTokens ?? 0,
    totalApiCalls: apiCallStats[0]?.totalApiCalls ?? 0,
    stats: {
      usersCreatedLast30Days: userStats[0]?.usersCreatedLast30Days ?? 0,
      conversationsLast30Days: conversationStats[0]?.conversationsLast30Days ?? 0,
      messagesLast30Days: messageStats[0]?.messagesLast30Days ?? 0,
      apiCallsLast30Days: apiCallStats[0]?.apiCallsLast30Days ?? 0,
    },
    feedback: {
      totalFeedback: feedbackStats.totalFeedback,
      helpfulCount: feedbackStats.helpfulCount,
      unhelpfulCount: feedbackStats.unhelpfulCount,
      helpfulPercentage,
      recentUnhelpfulCount: feedbackStats.recentUnhelpfulCount,
      feedbackWithTextCount: feedbackStats.feedbackWithTextCount,
    },
  };
});
