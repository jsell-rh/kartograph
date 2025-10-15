/**
 * GET /api/conversations/:id
 *
 * Get a specific conversation with all its messages
 * Verifies user owns the conversation
 */

import { db } from "../../db";
import { conversations, messages } from "../../db/schema";
import { eq, and, asc } from "drizzle-orm";
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

  // Get conversation and verify ownership
  const conversation = await db
    .select()
    .from(conversations)
    .where(
      and(
        eq(conversations.id, conversationId),
        eq(conversations.userId, userId),
      ),
    )
    .limit(1);

  if (!conversation || conversation.length === 0) {
    throw createError({
      statusCode: 404,
      message: "Conversation not found",
    });
  }

  // Get all messages for this conversation
  const conversationMessages = await db
    .select()
    .from(messages)
    .where(eq(messages.conversationId, conversationId))
    .orderBy(asc(messages.createdAt));

  return {
    ...conversation[0],
    messages: conversationMessages,
  };
});
