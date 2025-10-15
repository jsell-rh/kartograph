/**
 * POST /api/conversations
 *
 * Create a new conversation for the authenticated user
 */

import { db } from "../db";
import { conversations } from "../db/schema";
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

  // Parse request body
  const body = await readBody(event);
  const title = body.title || "New Conversation";

  // Create conversation
  const conversationId = crypto.randomUUID();
  const now = new Date();

  await db.insert(conversations).values({
    id: conversationId,
    userId,
    title,
    messageCount: 0,
    isArchived: false,
    createdAt: now,
    updatedAt: now,
  });

  // Return created conversation
  return {
    id: conversationId,
    title,
    messageCount: 0,
    isArchived: false,
    createdAt: now,
    updatedAt: now,
  };
});
