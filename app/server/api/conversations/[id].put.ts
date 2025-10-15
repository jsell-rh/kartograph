/**
 * PUT /api/conversations/:id
 *
 * Update conversation (rename, archive, etc.)
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

  // Parse request body
  const body = await readBody(event);
  const { title, isArchived } = body;

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

  // Update conversation
  const updates: any = {
    updatedAt: new Date(),
  };

  if (title !== undefined) {
    updates.title = title;
  }

  if (isArchived !== undefined) {
    updates.isArchived = isArchived;
  }

  await db
    .update(conversations)
    .set(updates)
    .where(eq(conversations.id, conversationId));

  // Return updated conversation
  const updated = await db
    .select()
    .from(conversations)
    .where(eq(conversations.id, conversationId))
    .limit(1);

  return updated[0];
});
