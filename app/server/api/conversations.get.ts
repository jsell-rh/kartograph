/**
 * GET /api/conversations
 *
 * List all conversations for the authenticated user
 * Sorted by lastMessageAt DESC (most recent first)
 */

import { db } from "../db";
import { conversations } from "../db/schema";
import { eq, desc } from "drizzle-orm";
import { getSession } from "../utils/auth";

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

  // Query conversations for this user
  const userConversations = await db
    .select({
      id: conversations.id,
      title: conversations.title,
      lastMessageAt: conversations.lastMessageAt,
      messageCount: conversations.messageCount,
      isArchived: conversations.isArchived,
      createdAt: conversations.createdAt,
      updatedAt: conversations.updatedAt,
    })
    .from(conversations)
    .where(eq(conversations.userId, userId))
    .orderBy(desc(conversations.lastMessageAt), desc(conversations.createdAt))
    .limit(100); // Limit to most recent 100 conversations

  return {
    conversations: userConversations,
    total: userConversations.length,
  };
});
