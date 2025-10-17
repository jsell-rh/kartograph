/**
 * GET /api/admin/usage-stats
 *
 * Returns time-series usage data for charts.
 * Supports web usage (conversations/messages) and API usage (queries).
 */

import { sql, gte, and } from "drizzle-orm";
import { conversations, messages, queryAuditLog, users } from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  await requireAdmin(event);

  const query = getQuery(event);
  const timeRange = Number(query.timeRange) || 30; // days
  const granularity = (query.granularity as string) || "daily"; // daily or hourly

  // Calculate time boundaries
  const now = Date.now();
  const startTime = now - timeRange * 24 * 60 * 60 * 1000;
  const startTimestamp = Math.floor(startTime / 1000);

  // Helper to format timestamp based on granularity
  const getTimeBucket = (timestampField: any) => {
    if (granularity === "hourly") {
      // Group by hour: YYYY-MM-DD HH:00:00
      return sql<string>`datetime(${timestampField}, 'unixepoch', 'start of hour')`;
    } else {
      // Group by day: YYYY-MM-DD
      return sql<string>`date(${timestampField}, 'unixepoch')`;
    }
  };

  // Fetch web usage - conversations created over time
  const conversationStats = await db
    .select({
      timeBucket: getTimeBucket(conversations.createdAt),
      count: sql<number>`COUNT(*)`,
    })
    .from(conversations)
    .where(gte(conversations.createdAt, sql`${startTimestamp}`))
    .groupBy(getTimeBucket(conversations.createdAt))
    .orderBy(getTimeBucket(conversations.createdAt));

  // Fetch web usage - messages created over time
  const messageStats = await db
    .select({
      timeBucket: getTimeBucket(messages.createdAt),
      count: sql<number>`COUNT(*)`,
    })
    .from(messages)
    .where(gte(messages.createdAt, sql`${startTimestamp}`))
    .groupBy(getTimeBucket(messages.createdAt))
    .orderBy(getTimeBucket(messages.createdAt));

  // Fetch API usage - queries over time
  const apiQueryStats = await db
    .select({
      timeBucket: getTimeBucket(queryAuditLog.timestamp),
      count: sql<number>`COUNT(*)`,
    })
    .from(queryAuditLog)
    .where(gte(queryAuditLog.timestamp, sql`${startTimestamp}`))
    .groupBy(getTimeBucket(queryAuditLog.timestamp))
    .orderBy(getTimeBucket(queryAuditLog.timestamp));

  // Generate complete time series (fill gaps with zeros)
  const timeLabels: string[] = [];
  const conversationData: number[] = [];
  const messageData: number[] = [];
  const apiQueryData: number[] = [];

  // Create map for quick lookup
  const conversationMap = new Map(
    conversationStats.map((s) => [s.timeBucket, s.count]),
  );
  const messageMap = new Map(messageStats.map((s) => [s.timeBucket, s.count]));
  const apiQueryMap = new Map(apiQueryStats.map((s) => [s.timeBucket, s.count]));

  // Generate time buckets
  const bucketSize = granularity === "hourly" ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
  for (let t = startTime; t <= now; t += bucketSize) {
    const date = new Date(t);
    let label: string;

    if (granularity === "hourly") {
      // Format: YYYY-MM-DD HH:00:00
      const year = date.getUTCFullYear();
      const month = String(date.getUTCMonth() + 1).padStart(2, "0");
      const day = String(date.getUTCDate()).padStart(2, "0");
      const hour = String(date.getUTCHours()).padStart(2, "0");
      label = `${year}-${month}-${day} ${hour}:00:00`;
    } else {
      // Format: YYYY-MM-DD
      const year = date.getUTCFullYear();
      const month = String(date.getUTCMonth() + 1).padStart(2, "0");
      const day = String(date.getUTCDate()).padStart(2, "0");
      label = `${year}-${month}-${day}`;
    }

    timeLabels.push(label);
    conversationData.push(conversationMap.get(label) || 0);
    messageData.push(messageMap.get(label) || 0);
    apiQueryData.push(apiQueryMap.get(label) || 0);
  }

  return {
    timeRange,
    granularity,
    labels: timeLabels,
    webUsage: {
      conversations: conversationData,
      messages: messageData,
    },
    apiUsage: {
      queries: apiQueryData,
    },
  };
});
