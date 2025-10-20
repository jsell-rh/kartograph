/**
 * Check if user has unseen changelog entries
 * Returns true if there are operational entries newer than user's lastSeenChangelogAt
 */

import { and, eq, gt, sql } from "drizzle-orm";
import { db } from "~/server/db/client";
import { users, changelogEntries } from "~/server/db/schema";
import { getSession } from "~/server/utils/auth";

export default defineEventHandler(async (event) => {
  const session = await getSession(event);

  if (!session?.user?.id) {
    // For non-authenticated users, check if there are any entries from last 14 days
    const fourteenDaysAgo = new Date();
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

    const countResult = await db
      .select({ count: sql<number>`count(*)` })
      .from(changelogEntries)
      .where(
        and(
          eq(changelogEntries.visibility, "public"),
          gt(changelogEntries.createdAt, fourteenDaysAgo)
        )
      );

    const count = countResult[0]?.count || 0;

    return {
      hasUnseen: count > 0,
      count,
    };
  }

  // Get user's lastSeenChangelogAt
  const userResult = await db
    .select({
      lastSeenChangelogAt: users.lastSeenChangelogAt,
    })
    .from(users)
    .where(eq(users.id, session.user.id))
    .limit(1);

  const user = userResult[0];

  if (!user) {
    throw createError({
      statusCode: 404,
      message: "User not found",
    });
  }

  // If user has never seen changelog, check for entries from last 14 days
  if (!user.lastSeenChangelogAt) {
    const fourteenDaysAgo = new Date();
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

    const countResult = await db
      .select({ count: sql<number>`count(*)` })
      .from(changelogEntries)
      .where(
        and(
          eq(changelogEntries.visibility, "public"),
          gt(changelogEntries.createdAt, fourteenDaysAgo)
        )
      );

    const count = countResult[0]?.count || 0;

    return {
      hasUnseen: count > 0,
      count,
      isFirstTime: true,
    };
  }

  // Check if there are entries created after lastSeenChangelogAt
  // Use createdAt instead of timestamp because timestamp can be manually set
  const countResult = await db
    .select({ count: sql<number>`count(*)` })
    .from(changelogEntries)
    .where(
      and(
        eq(changelogEntries.visibility, "public"),
        gt(changelogEntries.createdAt, user.lastSeenChangelogAt)
      )
    );

  const count = countResult[0]?.count || 0;

  return {
    hasUnseen: count > 0,
    count,
    lastSeenAt: user.lastSeenChangelogAt?.toISOString(),
  };
});
