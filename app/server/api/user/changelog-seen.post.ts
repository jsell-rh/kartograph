/**
 * Update user's lastSeenChangelogAt timestamp
 * Called when user dismisses the WhatsNewDialog
 */

import { eq } from "drizzle-orm";
import { db } from "~/server/db/client";
import { users } from "~/server/db/schema";
import { getSession } from "~/server/utils/auth";

export default defineEventHandler(async (event) => {
  const session = await getSession(event);

  if (!session?.user?.id) {
    throw createError({
      statusCode: 401,
      message: "Unauthorized",
    });
  }

  try {
    // Update user's lastSeenChangelogAt to current timestamp
    await db
      .update(users)
      .set({
        lastSeenChangelogAt: new Date(),
      })
      .where(eq(users.id, session.user.id));

    return {
      success: true,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error("Failed to update lastSeenChangelogAt:", error);
    throw createError({
      statusCode: 500,
      message: "Failed to update changelog timestamp",
    });
  }
});
