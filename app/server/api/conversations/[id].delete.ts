/**
 * DELETE /api/conversations/:id
 *
 * Delete a conversation and all its messages
 * Verifies user owns the conversation
 */

import { db } from "../../db";
import { conversations } from "../../db/schema";
import { eq, and } from "drizzle-orm";
import { getSession } from "../../utils/auth";

export default defineEventHandler(async (event) => {
  // Get authenticated user
  const session = await getSession(event);
  if (!session?.user?.id) {
    throw createError({
      statusCode: 401,
      message: "Unauthorized",
    });
  }

  const userId = session.user.id;
  const conversationId = getRouterParam(event, "id");

  if (!conversationId) {
    throw createError({
      statusCode: 400,
      message: "Missing conversation ID",
    });
  }

  // Verify conversation exists and user owns it
  const existing = await db
    .select()
    .from(conversations)
    .where(
      and(
        eq(conversations.id, conversationId),
        eq(conversations.userId, userId),
      ),
    )
    .limit(1);

  if (!existing || existing.length === 0) {
    throw createError({
      statusCode: 404,
      message: "Conversation not found",
    });
  }

  // Delete conversation (messages cascade delete via FK)
  await db.delete(conversations).where(eq(conversations.id, conversationId));

  return {
    success: true,
    deletedId: conversationId,
  };
});
