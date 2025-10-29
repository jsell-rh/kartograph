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
    let activeConversationId = conversationId;

    if (conversationId) {
      // Verify user owns the conversation
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

      log.debug({ conversationId }, "Using existing conversation");
    } else {
      // Create new conversation
      activeConversationId = crypto.randomUUID();
      const now = new Date();

      await db.insert(conversations).values({
        id: activeConversationId,
        userId,
        title: "New Conversation", // Will be updated with auto-naming later
        messageCount: 0,
        isArchived: false,
        createdAt: now,
        updatedAt: now,
      });

      log.info(
        { conversationId: activeConversationId },
        "Created new conversation",
      );
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

          // Track all extracted entities
          const allEntities: Entity[] = [];
          const entityExtractor = new EntityExtractor();
          const contextTruncationStrategy = new ProgressiveTrimStrategy();

          // Track assistant's response text for database persistence
          let assistantResponseText = "";
          let assistantThinkingSteps: ThinkingStep[] = [];
          let currentToolCallStep: ThinkingStep | null = null;

          // Conversation history (messages back and forth with Claude)
          // Include previous conversation context + new prompt
          // Keep track of initial history length for context truncation on 413 errors
          let currentHistoryTrimLevel = 0; // 0 = full history, increases on 413 errors
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

          // Agentic loop - keep calling Claude until it stops requesting tools
          let turnCount = 0;
          const maxTurns = 50;

          while (turnCount < maxTurns) {
            turnCount++;
            log.info(
              {
                turn: turnCount,
                maxTurns,
                messageCount: messages.length,
              },
              "Starting turn",
            );

            // Determine model identifier
            const model = hasVertexAI
              ? "claude-sonnet-4-5@20250929"
              : "claude-sonnet-4-20250514";

            // Wrap API call with context length error handling
            let stream: any;
            let contextTruncationAttempt = 0;
            const maxContextTruncationAttempts = 6;

            while (contextTruncationAttempt < maxContextTruncationAttempts) {
              try {
                // Call Claude with streaming (with retry on 429)
                stream = await withRetry(
                  () =>
                    (anthropic as any).messages.create({
                      model,
                      max_tokens: 8000,
                      system: fullSystemPrompt,
                      messages,
                      tools: dgraphTools,
                      stream: true,
                    }),
                  `anthropic-stream-turn-${turnCount}`,
                  log,
                  async (attempt, delayMs) => {
                    // Send retry event to frontend
                    const delaySeconds = Math.ceil(delayMs / 1000);
                    sse.pushEvent("retry", {
                      attempt,
                      delayMs,
                      delaySeconds,
                      message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
                    });
                  },
                );
                break; // Success, exit retry loop
              } catch (error: any) {
                // Check if this is a context length error (413 or "prompt is too long")
                const isContextError = isContextLengthError(error);

                if (
                  isContextError &&
                  contextTruncationAttempt < maxContextTruncationAttempts - 1
                ) {
                  contextTruncationAttempt++;
                  currentHistoryTrimLevel = contextTruncationAttempt;

                  // Get trimmed history
                  const trimmedHistory = contextTruncationStrategy.truncate(
                    sanitizedHistory,
                    contextTruncationAttempt,
                  );

                  log.warn(
                    {
                      turn: turnCount,
                      attempt: contextTruncationAttempt,
                      originalHistoryLength: initialHistoryLength,
                      trimmedHistoryLength: trimmedHistory.length,
                      droppedMessages:
                        initialHistoryLength - trimmedHistory.length,
                    },
                    "Context length exceeded, trimming history",
                  );

                  // Notify frontend of context truncation
                  sse.pushEvent("context_truncated", {
                    attempt: contextTruncationAttempt,
                    originalCount: initialHistoryLength,
                    newCount: trimmedHistory.length,
                    droppedCount: initialHistoryLength - trimmedHistory.length,
                    message:
                      trimmedHistory.length === 0
                        ? "Conversation too long. Using only current message (history cleared)."
                        : `Conversation too long. Dropped ${initialHistoryLength - trimmedHistory.length} older messages to fit context.`,
                  });

                  // Rebuild messages array with trimmed history
                  // Keep: trimmed history + current prompt + accumulated session messages
                  const sessionMessagesStart = initialHistoryLength + 1; // After original history + prompt
                  const sessionMessages = messages.slice(sessionMessagesStart);

                  // Rebuild messages array
                  messages.length = 0; // Clear array
                  messages.push(...trimmedHistory);
                  messages.push({ role: "user", content: prompt });
                  messages.push(...sessionMessages);

                  log.info(
                    {
                      rebuiltMessageCount: messages.length,
                      historyCount: trimmedHistory.length,
                      sessionMessageCount: sessionMessages.length,
                    },
                    "Rebuilt messages with trimmed history",
                  );

                  // Continue to next retry attempt
                  continue;
                } else {
                  // Not a context error or exhausted retries, rethrow
                  throw error;
                }
              }
            }

            if (!stream) {
              throw new Error(
                "Failed to create stream after context truncation retries",
              );
            }

            let currentText = "";
            let currentToolCalls: Anthropic.Messages.ToolUseBlock[] = [];

            // Process stream
            for await (const chunk of stream) {
              if (chunk.type === "content_block_start") {
                if (chunk.content_block.type === "text") {
                  // Text block starting
                  log.debug("Text block started");
                } else if (chunk.content_block.type === "tool_use") {
                  // Tool use block starting
                  log.debug(
                    {
                      toolId: chunk.content_block.id,
                      toolName: chunk.content_block.name,
                    },
                    "Tool use block started",
                  );
                }
              } else if (chunk.type === "content_block_delta") {
                if (chunk.delta.type === "text_delta") {
                  // Stream text to client
                  const delta = chunk.delta.text;
                  currentText += delta;
                  sse.pushEvent("text", { delta });
                } else if (chunk.delta.type === "input_json_delta") {
                  // Tool input is being streamed (we'll handle complete tool call later)
                  log.debug(
                    { partial: chunk.delta.partial_json },
                    "Tool input delta",
                  );
                }
              } else if (chunk.type === "content_block_stop") {
                log.debug({ index: chunk.index }, "Content block stopped");
              } else if (chunk.type === "message_delta") {
                log.debug(
                  { stopReason: chunk.delta.stop_reason },
                  "Message delta",
                );
              } else if (chunk.type === "message_stop") {
                log.debug("Message stopped");
              }
            }

            // After stream completes, get the complete message
            // We need to reconstruct it from what we know
            // OR we can make a non-streaming call to get the complete message
            // For now, let's use non-streaming to get tool calls

            // Make non-streaming call to get complete message with tool calls (with retry on 429)
            // Note: Context truncation already handled in streaming call above,
            // so this call should succeed with the same trimmed messages array
            const response = await withRetry<Anthropic.Message>(
              () =>
                (anthropic as any).messages.create({
                  model,
                  max_tokens: 8000,
                  system: fullSystemPrompt,
                  messages,
                  tools: dgraphTools,
                  stream: false,
                }),
              `anthropic-complete-turn-${turnCount}`,
              log,
              async (attempt, delayMs) => {
                // Send retry event to frontend
                const delaySeconds = Math.ceil(delayMs / 1000);
                sse.pushEvent("retry", {
                  attempt,
                  delayMs,
                  delaySeconds,
                  message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
                });
              },
            );

            // Extract tool calls
            currentToolCalls = response.content.filter(
              (
                block: Anthropic.Messages.ContentBlock,
              ): block is Anthropic.Messages.ToolUseBlock =>
                block.type === "tool_use",
            );

            // Extract text content
            const textBlocks = response.content.filter(
              (
                block: Anthropic.Messages.ContentBlock,
              ): block is Anthropic.Messages.TextBlock => block.type === "text",
            );
            const fullText = textBlocks
              .map((b: Anthropic.Messages.TextBlock) => b.text)
              .join("");

            // Log assistant response
            if (fullText) {
              log.debug(
                {
                  turn: turnCount,
                  responseLength: fullText.length,
                  responsePreview: truncateForLog(fullText, 200),
                  hasToolCalls: currentToolCalls.length > 0,
                },
                "Assistant response received",
              );

              // Track thinking steps and final response
              if (currentToolCalls.length > 0) {
                // This is a thinking step (has tool calls)
                assistantThinkingSteps.push({
                  type: "thinking",
                  content: fullText,
                });
              } else {
                // This is the final response (no tool calls)
                assistantResponseText = fullText;
              }

              sse.pushEvent("thinking", { text: fullText });
              const entities = entityExtractor.extract(fullText);
              allEntities.push(...entities);

              if (entities.length > 0) {
                log.info(
                  {
                    turn: turnCount,
                    entitiesExtracted: entities.length,
                    entityTypes: [...new Set(entities.map((e) => e.type))],
                  },
                  "Entities extracted from response",
                );
                sse.pushEvent("entities", { entities });
              }
            }

            // Add assistant message to history
            messages.push({
              role: "assistant",
              content: response.content,
            });

            // If no tool calls, we're done
            if (currentToolCalls.length === 0) {
              const elapsedSeconds = Math.floor(
                (Date.now() - startTime) / 1000,
              );

              log.info(
                {
                  turns: turnCount,
                  totalEntities: allEntities.length,
                  inputTokens: response.usage.input_tokens,
                  outputTokens: response.usage.output_tokens,
                  totalTokens:
                    response.usage.input_tokens + response.usage.output_tokens,
                  elapsedSeconds,
                },
                "Conversation complete",
              );

              // Save messages to database
              let savedUserMessageId: string | undefined;
              let savedAssistantMessageId: string | undefined;

              try {
                const messageTimestamp = new Date();

                // Save user message
                const userMessageId = crypto.randomUUID();
                savedUserMessageId = userMessageId;
                await db.insert(messagesTable).values({
                  id: userMessageId,
                  conversationId: activeConversationId,
                  role: "user",
                  content: prompt,
                  createdAt: messageTimestamp,
                });

                // Save assistant message
                const assistantMessageId = crypto.randomUUID();
                savedAssistantMessageId = assistantMessageId;
                await db.insert(messagesTable).values({
                  id: assistantMessageId,
                  conversationId: activeConversationId,
                  role: "assistant",
                  content: assistantResponseText,
                  thinkingSteps:
                    assistantThinkingSteps.length > 0
                      ? assistantThinkingSteps
                      : undefined,
                  entities: allEntities.length > 0 ? allEntities : undefined,
                  elapsedSeconds,
                  createdAt: messageTimestamp,
                });

                // Update conversation metadata
                // Count messages in this conversation (should be 2 after we just added user + assistant)
                const messageCountResult = await db
                  .select()
                  .from(messagesTable)
                  .where(
                    eq(messagesTable.conversationId, activeConversationId),
                  );

                await db
                  .update(conversations)
                  .set({
                    lastMessageAt: messageTimestamp,
                    messageCount: messageCountResult.length,
                    updatedAt: messageTimestamp,
                  })
                  .where(eq(conversations.id, activeConversationId));

                log.info(
                  {
                    conversationId: activeConversationId,
                    messageCount: messageCountResult.length,
                  },
                  "Messages saved to database",
                );

                // Auto-generate conversation title after first exchange
                if (messageCountResult.length === 2) {
                  try {
                    log.debug(
                      {
                        conversationId: activeConversationId,
                        userPrompt: prompt,
                      },
                      "Generating conversation title",
                    );

                    const titleResponse: Anthropic.Message = await (
                      anthropic as any
                    ).messages.create({
                      model: hasVertexAI
                        ? "claude-3-5-haiku@20241022"
                        : "claude-3-5-haiku-20241022",
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
                      ): block is Anthropic.Messages.TextBlock =>
                        block.type === "text",
                    );

                    if (titleBlock && titleBlock.text) {
                      const generatedTitle = titleBlock.text
                        .trim()
                        .replace(/^["']|["']$/g, "");

                      await db
                        .update(conversations)
                        .set({ title: generatedTitle })
                        .where(eq(conversations.id, activeConversationId));

                      log.info(
                        {
                          conversationId: activeConversationId,
                          generatedTitle,
                        },
                        "Auto-generated conversation title",
                      );
                    }
                  } catch (titleError) {
                    // Gracefully fail - keep "New Conversation" title
                    log.warn(
                      {
                        conversationId: activeConversationId,
                        error:
                          titleError instanceof Error
                            ? titleError.message
                            : String(titleError),
                      },
                      "Failed to auto-generate conversation title",
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
                turns: turnCount,
                entities: allEntities,
                usage: response.usage,
                conversationId: activeConversationId,
                userMessageId: savedUserMessageId,
                assistantMessageId: savedAssistantMessageId,
              });
              break;
            }

            // Execute tool calls
            log.info(
              {
                toolCount: currentToolCalls.length,
                tools: currentToolCalls.map((t) => t.name),
              },
              "Executing tools",
            );
            const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

            for (const toolCall of currentToolCalls) {
              const toolStartTime = Date.now();
              const description =
                (toolCall.input as any).description || "Executing query...";

              // Log tool call details
              log.debug(
                {
                  toolId: toolCall.id,
                  toolName: toolCall.name,
                  toolInput: toolCall.input,
                  turn: turnCount,
                },
                "Tool call started",
              );

              // Create thinking step for this tool call
              const toolStep: ThinkingStep = {
                type: "tool_call",
                content: description,
                metadata: {
                  toolName: toolCall.name,
                  description,
                },
              };
              assistantThinkingSteps.push(toolStep);

              sse.pushEvent("tool_call", {
                id: toolCall.id,
                name: toolCall.name,
                description,
              });

              try {
                const result = await executeTool(toolCall.name, toolCall.input);
                const toolElapsedMs = Date.now() - toolStartTime;

                // Log successful tool result
                log.info(
                  {
                    toolId: toolCall.id,
                    toolName: toolCall.name,
                    toolElapsedMs,
                    resultLength:
                      typeof result === "string"
                        ? result.length
                        : JSON.stringify(result).length,
                    resultPreview: truncateForLog(result, 200),
                  },
                  "Tool execution succeeded",
                );

                // Update tool step with timing
                toolStep.metadata!.timing = toolElapsedMs;

                // Send completion event with timing
                sse.pushEvent("tool_complete", {
                  toolId: toolCall.id,
                  elapsedMs: toolElapsedMs,
                });

                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolCall.id,
                  content: result,
                });
              } catch (error) {
                const toolElapsedMs = Date.now() - toolStartTime;
                const errorMessage =
                  error instanceof Error ? error.message : "Unknown error";

                log.error(
                  {
                    toolId: toolCall.id,
                    toolName: toolCall.name,
                    toolElapsedMs,
                    error: errorMessage,
                    errorStack:
                      error instanceof Error ? error.stack : undefined,
                  },
                  "Tool execution failed",
                );

                // Update tool step with error
                toolStep.metadata!.timing = toolElapsedMs;
                toolStep.metadata!.error = errorMessage;

                // Send completion event with timing even on error
                sse.pushEvent("tool_complete", {
                  toolId: toolCall.id,
                  elapsedMs: toolElapsedMs,
                  error: true,
                });

                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolCall.id,
                  content: `Error: ${errorMessage}`,
                  is_error: true,
                });
                sse.pushEvent("tool_error", {
                  toolId: toolCall.id,
                  error: errorMessage,
                });
              }
            }

            // Add tool results to conversation
            messages.push({
              role: "user",
              content: toolResults,
            });
          }

          if (turnCount >= maxTurns) {
            log.warn("Hit max turns limit");
            sse.pushEvent("done", {
              success: false,
              error: "Max turns reached",
              turns: turnCount,
              entities: allEntities,
            });
          }

          log.info(
            { turns: turnCount, elapsed: `${Date.now() - startTime}ms` },
            "Stream complete",
          );
          sse.close();
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
