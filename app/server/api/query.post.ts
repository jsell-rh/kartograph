/**
 * POST /api/query
 *
 * Natural language query endpoint using Anthropic Messages API
 * to translate questions into Dgraph queries via custom tools.
 *
 * Streams responses via Server-Sent Events (SSE).
 */

import Anthropic from "@anthropic-ai/sdk";
import AnthropicVertex from "@anthropic-ai/vertex-sdk";
import { dgraphTools, executeTool } from "../lib/dgraph-tools";
import { setResponseStatus, setHeader, sendStream } from "h3";
import { createRequestLogger, truncateForLog } from "../lib/logger";
import { withRetry } from "../lib/retry";
import { getSession } from "../utils/auth";
import { extractErrorMessage, isContextLengthError } from "../utils/errorUtils";
import { EntityExtractor, type Entity } from "../services/EntityExtractor";
import { ProgressiveTrimStrategy } from "../strategies/ContextTruncationStrategy";
import { SSEStreamManager } from "../stream/SSEStreamManager";
import { SystemPromptBuilder } from "../services/SystemPromptBuilder";
import { ConversationService } from "../services/ConversationService";
import { QueryAgent } from "../orchestrator/QueryAgent";
import { db } from "../db";
import {
  conversations,
  messages as messagesTable,
  type ThinkingStep,
} from "../db/schema";
import { eq, and } from "drizzle-orm";

export default defineEventHandler(async (event) => {
  const startTime = Date.now();

  // Create request-scoped logger with correlation ID
  const { logger: log, correlationId } = createRequestLogger("query-api");

  try {
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
    const { prompt, conversationHistory = [], conversationId } = body;

    log.info(
      {
        promptLength: prompt?.length || 0,
        promptPreview: truncateForLog(prompt, 100),
        historyLength: conversationHistory?.length || 0,
        conversationId: conversationId || "new",
        userId,
        correlationId,
      },
      "Received query request",
    );

    if (!prompt || typeof prompt !== "string") {
      throw createError({
        statusCode: 400,
        message: "Missing or invalid prompt",
      });
    }

    // Handle conversation persistence
    const conversationService = new ConversationService(log);
    let activeConversationId = conversationId;

    if (conversationId) {
      // Verify user owns the conversation
      const existing = await conversationService.get(conversationId, userId);

      if (!existing) {
        throw createError({
          statusCode: 404,
          message: "Conversation not found",
        });
      }
    } else {
      // Create new conversation
      activeConversationId = await conversationService.create(userId);
    }

    // Validate and sanitize conversation history
    const MAX_HISTORY_MESSAGES = 20; // Limit to prevent token overflow
    const sanitizedHistory: Anthropic.MessageParam[] = (
      conversationHistory || []
    )
      .slice(-MAX_HISTORY_MESSAGES) // Keep last N messages
      .filter(
        (msg: any) =>
          msg.role && msg.content && typeof msg.content === "string",
      )
      .map((msg: any) => ({
        role: msg.role,
        content: msg.content,
      }));

    // Log full user message
    log.debug(
      {
        userMessage: prompt,
        messageLength: prompt.length,
        historyMessages: sanitizedHistory.length,
      },
      "User message content",
    );

    // Get runtime config
    const config = useRuntimeConfig(event);

    // Check for either VertexAI or Anthropic configuration
    const hasVertexAI = config.vertexProjectId && config.vertexRegion;
    const hasAnthropic = config.anthropicApiKey;

    if (!hasVertexAI && !hasAnthropic) {
      throw createError({
        statusCode: 500,
        message:
          "Neither VertexAI (VERTEX_PROJECT_ID, VERTEX_REGION) nor ANTHROPIC_API_KEY configured",
      });
    }

    log.info(
      {
        hasVertexAI,
        hasAnthropic,
        vertexProjectId: hasVertexAI ? config.vertexProjectId : "not set",
        vertexRegion: hasVertexAI ? config.vertexRegion : "not set",
      },
      "AI provider configuration",
    );

    // Initialize Anthropic client with VertexAI or direct API
    const anthropic: Anthropic | AnthropicVertex = hasVertexAI
      ? new AnthropicVertex({
          projectId: config.vertexProjectId,
          region: config.vertexRegion,
        })
      : new Anthropic({
          apiKey: config.anthropicApiKey,
        });

    // Set up SSE headers
    log.debug("Setting up SSE headers");
    setResponseStatus(event, 200);
    setHeader(event, "Content-Type", "text/event-stream");
    setHeader(event, "Cache-Control", "no-cache");
    setHeader(event, "Connection", "keep-alive");

    log.debug("Creating response stream");

    // Create a manual event stream
    const stream = new ReadableStream({
      async start(controller) {
        // Initialize SSE stream manager
        const sse = new SSEStreamManager(controller);

        try {
          // Send keepalive
          sse.keepalive();
          log.info("SSE connection established");

          // Build system prompt with current graph stats
          const systemPromptBuilder = new SystemPromptBuilder(
            config.dgraphUrl,
            log,
          );
          const fullSystemPrompt = await systemPromptBuilder.build();

          log.debug(
            {
              systemPromptLength: fullSystemPrompt.length,
              systemPromptPreview: fullSystemPrompt.substring(0, 200),
            },
            "System prompt built",
          );

          // Track all extracted entities and thinking steps
          const allEntities: Entity[] = [];
          let assistantThinkingSteps: ThinkingStep[] = [];
          let assistantResponseText = "";

          // Setup context truncation strategy
          const contextTruncationStrategy = new ProgressiveTrimStrategy();

          // Conversation history (messages back and forth with Claude)
          const initialHistoryLength = sanitizedHistory.length;
          const messages: Anthropic.MessageParam[] = [
            ...sanitizedHistory,
            {
              role: "user",
              content: prompt,
            },
          ];

          log.debug(
            {
              initialMessageCount: messages.length,
              historyCount: sanitizedHistory.length,
              conversationStart: sanitizedHistory.length === 0,
            },
            "Starting conversation with history",
          );

          // Determine model identifier
          const model = hasVertexAI
            ? "claude-sonnet-4-5@20250929"
            : "claude-sonnet-4-20250514";

          // Create Query Agent
          const queryAgent = new QueryAgent(
            anthropic,
            dgraphTools,
            {
              maxTurns: 50,
              maxContextTruncationAttempts: 6,
              model,
              maxTokens: 8000,
            },
            log,
            contextTruncationStrategy,
          );
          // Setup Query Agent event listeners
          queryAgent.on("text", ({ delta }) => {
            sse.pushEvent("text", { delta });
          });

          queryAgent.on("thinking", ({ text }) => {
            sse.pushEvent("thinking", { text });
            assistantThinkingSteps.push({
              type: "thinking",
              content: text,
            });
          });

          queryAgent.on("entities", ({ entities }) => {
            allEntities.push(...entities);
            sse.pushEvent("entities", { entities });
          });

          queryAgent.on("retry", (data) => {
            sse.pushEvent("retry", data);
          });

          queryAgent.on("context_truncated", (data) => {
            sse.pushEvent("context_truncated", data);
          });

          queryAgent.on("tool_call", (data) => {
            sse.pushEvent("tool_call", data);
            assistantThinkingSteps.push({
              type: "tool_call",
              content: data.description,
              metadata: {
                toolName: data.name,
                description: data.description,
              },
            });
          });

          queryAgent.on("tool_complete", (data) => {
            sse.pushEvent("tool_complete", data);
          });

          queryAgent.on("tool_error", (data) => {
            sse.pushEvent("tool_error", data);
          });

          queryAgent.on("done", async (result) => {
            if (result.success && result.response) {
              assistantResponseText = result.response;

              // Save messages to database
              let savedUserMessageId: string | undefined;
              let savedAssistantMessageId: string | undefined;

              try {
                const elapsedSeconds = Math.floor(
                  (Date.now() - startTime) / 1000,
                );

                const { userMessageId, assistantMessageId } =
                  await conversationService.saveMessages(
                    activeConversationId,
                    prompt,
                    assistantResponseText,
                    {
                      thinkingSteps: assistantThinkingSteps,
                      entities: allEntities,
                      elapsedSeconds,
                    },
                  );

                savedUserMessageId = userMessageId;
                savedAssistantMessageId = assistantMessageId;

                // Auto-generate conversation title after first exchange
                const messageCountResult = await db
                  .select()
                  .from(messagesTable)
                  .where(
                    eq(messagesTable.conversationId, activeConversationId),
                  );

                if (messageCountResult.length === 2) {
                  const titleModel = hasVertexAI
                    ? "claude-3-5-haiku@20241022"
                    : "claude-3-5-haiku-20241022";

                  const generatedTitle = await conversationService.generateTitle(
                    prompt,
                    anthropic,
                    titleModel,
                  );

                  if (generatedTitle) {
                    await conversationService.updateMetadata(
                      activeConversationId,
                      { title: generatedTitle },
                    );
                  }
                }
              } catch (dbError) {
                log.error(
                  {
                    error:
                      dbError instanceof Error
                        ? dbError.message
                        : String(dbError),
                    conversationId: activeConversationId,
                  },
                  "Failed to save messages to database",
                );
              }

              sse.pushEvent("done", {
                success: true,
                turns: result.turns,
                entities: allEntities,
                usage: result.usage,
                conversationId: activeConversationId,
                userMessageId: savedUserMessageId,
                assistantMessageId: savedAssistantMessageId,
              });
            } else {
              sse.pushEvent("done", {
                success: false,
                error: result.error,
                turns: result.turns,
                entities: allEntities,
              });
            }
          });

          // Execute the agent
          await queryAgent.execute(
            fullSystemPrompt,
            messages,
            initialHistoryLength,
            sanitizedHistory,
            prompt,
          );

        } catch (error) {
          // Extract clean error message for user display
          const userMessage = extractErrorMessage(error);

          log.error(
            {
              error: error instanceof Error ? error.message : String(error),
              stack: error instanceof Error ? error.stack : undefined,
              elapsed: `${Date.now() - startTime}ms`,
              userMessage,
            },
            "Fatal error",
          );

          if (!sse.isClosed()) {
            // Provide helpful context for common errors
            let enhancedMessage = userMessage;
            if (userMessage.toLowerCase().includes("prompt is too long")) {
              enhancedMessage = "The conversation context became too large. This usually happens when queries return too much data. Please try:\n- Starting a new conversation\n- Using more specific filters in your query\n- Asking about fewer entities at once";
            }

            sse.pushEvent("done", {
              success: false,
              error: enhancedMessage,
              entities: [],
            });
          }

          sse.close();
        }
      },
    });

    log.debug("Returning stream to client");
    return sendStream(event, stream);
  } catch (setupError) {
    log.error(
      {
        error:
          setupError instanceof Error ? setupError.message : String(setupError),
        stack: setupError instanceof Error ? setupError.stack : undefined,
      },
      "Setup error",
    );
    throw createError({
      statusCode: 500,
      message:
        setupError instanceof Error
          ? setupError.message
          : "Failed to initialize query",
    });
  }
});
