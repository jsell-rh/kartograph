/**
 * POST /api/feedback
 *
 * Submits user feedback for an assistant message.
 * Creates or updates feedback with rating and optional text.
 */

import { and, eq, asc } from "drizzle-orm";
import { messages, messageFeedback, conversations } from "~/server/db/schema";
import { db } from "~/server/db/client";
import { auth } from "~/server/lib/auth";

export default defineEventHandler(async (event) => {
  const session = await auth.api.getSession({ headers: event.headers });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      message: "Authentication required",
    });
  }

  const body = await readBody(event);
  const { messageId, rating, feedbackText } = body;

  // Validate input
  if (!messageId || !rating) {
    throw createError({
      statusCode: 400,
      message: "messageId and rating are required",
    });
  }

  if (!["helpful", "unhelpful"].includes(rating)) {
    throw createError({
      statusCode: 400,
      message: "rating must be 'helpful' or 'unhelpful'",
    });
  }

  // Get the message
  const message = await db.query.messages.findFirst({
    where: eq(messages.id, messageId),
  });

  if (!message) {
    throw createError({
      statusCode: 404,
      message: "Message not found",
    });
  }

  // Get the conversation to verify ownership
  const conversation = await db.query.conversations.findFirst({
    where: eq(conversations.id, message.conversationId),
  });

  if (!conversation) {
    throw createError({
      statusCode: 404,
      message: "Conversation not found",
    });
  }

  if (conversation.userId !== session.user.id) {
    throw createError({
      statusCode: 403,
      message: "You can only provide feedback on your own messages",
    });
  }

  // Only allow feedback on assistant messages
  if (message.role !== "assistant") {
    throw createError({
      statusCode: 400,
      message: "Feedback can only be submitted for assistant responses",
    });
  }

  // Get the user's query (previous message in conversation)
  // Get all messages in conversation, ordered chronologically
  const allMessages = await db.query.messages.findMany({
    where: eq(messages.conversationId, message.conversationId),
    orderBy: asc(messages.createdAt),
  });

  // Find the index of the current assistant message
  const currentIndex = allMessages.findIndex((m) => m.id === messageId);

  // Find the most recent user message before this assistant message
  let userQuery = "[No user query found]";
  if (currentIndex > 0) {
    for (let i = currentIndex - 1; i >= 0; i--) {
      const msg = allMessages[i];
      if (msg && msg.role === "user") {
        userQuery = msg.content;
        break;
      }
    }
  }

  // Check if feedback already exists for this message
  const existingFeedback = await db.query.messageFeedback.findFirst({
    where: and(
      eq(messageFeedback.messageId, messageId),
      eq(messageFeedback.userId, session.user.id),
    ),
  });

  let feedbackId: string;

  if (existingFeedback) {
    // Update existing feedback
    await db
      .update(messageFeedback)
      .set({
        rating: rating as "helpful" | "unhelpful",
        feedbackText: feedbackText ?? null,
        createdAt: new Date(), // Update timestamp
      })
      .where(eq(messageFeedback.id, existingFeedback.id));

    feedbackId = existingFeedback.id;
  } else {
    // Create new feedback
    feedbackId = crypto.randomUUID();

    await db.insert(messageFeedback).values({
      id: feedbackId,
      messageId,
      conversationId: message.conversationId,
      userId: session.user.id,
      rating: rating as "helpful" | "unhelpful",
      feedbackText: feedbackText ?? null,
      userQuery,
      assistantResponse: message.content,
      createdAt: new Date(),
    });
  }

  return {
    success: true,
    feedbackId,
  };
});
