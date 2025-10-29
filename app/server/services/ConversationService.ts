/**
 * Conversation Service
 *
 * Handles all conversation-related database operations:
 * - Creating conversations
 * - Getting conversations with ownership validation
 * - Saving messages with metadata
 * - Generating conversation titles
 * - Updating conversation metadata
 */

import type Anthropic from "@anthropic-ai/sdk";
import type AnthropicVertex from "@anthropic-ai/vertex-sdk";
import { db } from "../db";
import {
  conversations,
  messages as messagesTable,
  type ThinkingStep,
} from "../db/schema";
import { eq, and } from "drizzle-orm";
import type { Entity } from "./EntityExtractor";

export interface ConversationMetadata {
  thinkingSteps?: ThinkingStep[];
  entities?: Entity[];
  elapsedSeconds?: number;
}

export class ConversationService {
  /**
   * Create a new ConversationService
   *
   * @param logger - Logger instance for debugging
   */
  constructor(private logger: any) {}

  /**
   * Create a new conversation
   *
   * @param userId - The user ID who owns the conversation
   * @returns The new conversation ID
   */
  async create(userId: string): Promise<string> {
    const conversationId = crypto.randomUUID();
    const now = new Date();

    await db.insert(conversations).values({
      id: conversationId,
      userId,
      title: "New Conversation", // Will be updated with auto-naming later
      messageCount: 0,
      isArchived: false,
      createdAt: now,
      updatedAt: now,
    });

    this.logger.info({ conversationId }, "Created new conversation");

    return conversationId;
  }

  /**
   * Get a conversation with ownership validation
   *
   * @param conversationId - The conversation ID
   * @param userId - The user ID to validate ownership
   * @returns The conversation if found and owned by user, null otherwise
   */
  async get(
    conversationId: string,
    userId: string,
  ): Promise<{ id: string } | null> {
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

    if (!existing || existing.length === 0 || !existing[0]) {
      return null;
    }

    this.logger.debug({ conversationId }, "Using existing conversation");
    return { id: existing[0].id };
  }

  /**
   * Save user and assistant messages to the conversation
   *
   * @param conversationId - The conversation ID
   * @param userMessage - The user's message content
   * @param assistantMessage - The assistant's response content
   * @param metadata - Optional metadata (thinking steps, entities, elapsed time)
   * @returns The user and assistant message IDs
   */
  async saveMessages(
    conversationId: string,
    userMessage: string,
    assistantMessage: string,
    metadata: ConversationMetadata = {},
  ): Promise<{ userMessageId: string; assistantMessageId: string }> {
    const messageTimestamp = new Date();

    // Save user message
    const userMessageId = crypto.randomUUID();
    await db.insert(messagesTable).values({
      id: userMessageId,
      conversationId,
      role: "user",
      content: userMessage,
      createdAt: messageTimestamp,
    });

    // Save assistant message
    const assistantMessageId = crypto.randomUUID();
    await db.insert(messagesTable).values({
      id: assistantMessageId,
      conversationId,
      role: "assistant",
      content: assistantMessage,
      thinkingSteps:
        metadata.thinkingSteps && metadata.thinkingSteps.length > 0
          ? metadata.thinkingSteps
          : undefined,
      entities:
        metadata.entities && metadata.entities.length > 0
          ? metadata.entities
          : undefined,
      elapsedSeconds: metadata.elapsedSeconds,
      createdAt: messageTimestamp,
    });

    // Update conversation metadata
    // Count messages in this conversation
    const messageCountResult = await db
      .select()
      .from(messagesTable)
      .where(eq(messagesTable.conversationId, conversationId));

    await db
      .update(conversations)
      .set({
        lastMessageAt: messageTimestamp,
        messageCount: messageCountResult.length,
        updatedAt: messageTimestamp,
      })
      .where(eq(conversations.id, conversationId));

    this.logger.info(
      {
        conversationId,
        messageCount: messageCountResult.length,
      },
      "Messages saved to database",
    );

    return { userMessageId, assistantMessageId };
  }

  /**
   * Generate a conversation title using AI
   *
   * @param prompt - The user's initial prompt
   * @param anthropic - The Anthropic client instance
   * @param model - The model identifier to use for title generation
   * @returns The generated title, or null if generation fails
   */
  async generateTitle(
    prompt: string,
    anthropic: Anthropic | AnthropicVertex,
    model: string,
  ): Promise<string | null> {
    try {
      this.logger.debug({ userPrompt: prompt }, "Generating conversation title");

      const titleResponse: Anthropic.Message = await (
        anthropic as any
      ).messages.create({
        model,
        max_tokens: 50,
        messages: [
          {
            role: "user",
            content: `Generate a concise, descriptive 3-5 word title for a conversation that starts with this question: "${prompt}"\n\nRespond with ONLY the title, no quotes or punctuation.`,
          },
        ],
      });

      const titleBlock = titleResponse.content.find(
        (
          block: Anthropic.Messages.ContentBlock,
        ): block is Anthropic.Messages.TextBlock => block.type === "text",
      );

      if (titleBlock && titleBlock.text) {
        const generatedTitle = titleBlock.text
          .trim()
          .replace(/^["']|["']$/g, "");

        this.logger.info({ generatedTitle }, "Auto-generated conversation title");
        return generatedTitle;
      }

      return null;
    } catch (error) {
      this.logger.warn(
        {
          error: error instanceof Error ? error.message : String(error),
        },
        "Failed to auto-generate conversation title",
      );
      return null;
    }
  }

  /**
   * Update conversation metadata (e.g., title)
   *
   * @param conversationId - The conversation ID
   * @param updates - The updates to apply
   */
  async updateMetadata(
    conversationId: string,
    updates: { title?: string },
  ): Promise<void> {
    await db
      .update(conversations)
      .set(updates)
      .where(eq(conversations.id, conversationId));

    this.logger.debug({ conversationId, updates }, "Updated conversation metadata");
  }
}
