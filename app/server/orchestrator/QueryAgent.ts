/**
 * Query Agent Orchestrator
 *
 * Event-driven agent that orchestrates the agentic loop for query execution.
 * Manages turns, tool execution, context truncation, and streaming responses.
 *
 * Events Emitted:
 * - 'thinking': { text: string }
 * - 'text': { delta: string }
 * - 'tool_call': { id: string, name: string, description: string }
 * - 'tool_complete': { toolId: string, elapsedMs: number, error?: boolean }
 * - 'tool_error': { toolId: string, error: string }
 * - 'entities': { entities: Entity[] }
 * - 'retry': { attempt: number, delayMs: number, delaySeconds: number, message: string }
 * - 'context_truncated': { attempt: number, originalCount: number, newCount: number, droppedCount: number, message: string }
 * - 'done': { success: boolean, response?: string, usage?: Anthropic.Usage, turns?: number, error?: string }
 */

import { EventEmitter } from "events";
import type Anthropic from "@anthropic-ai/sdk";
import type AnthropicVertex from "@anthropic-ai/vertex-sdk";
import type { ContextTruncationStrategy } from "../strategies/ContextTruncationStrategy";
import { EntityExtractor, type Entity } from "../services/EntityExtractor";
import { withRetry } from "../lib/retry";
import { isContextLengthError } from "../utils/errorUtils";
import { executeTool } from "../lib/dgraph-tools";
import { truncateForLog } from "../lib/logger";

export interface QueryAgentConfig {
  maxTurns: number;
  maxContextTruncationAttempts: number;
  model: string;
  maxTokens: number;
}

export class QueryAgent extends EventEmitter {
  private entityExtractor: EntityExtractor;

  constructor(
    private anthropic: Anthropic | AnthropicVertex,
    private tools: any[],
    private config: QueryAgentConfig,
    private logger: any,
    private contextTruncationStrategy: ContextTruncationStrategy,
  ) {
    super();
    this.entityExtractor = new EntityExtractor();
  }

  /**
   * Execute the agentic loop
   *
   * @param systemPrompt - The system prompt
   * @param messages - The conversation messages (will be mutated)
   * @param initialHistoryLength - Length of initial history for context truncation
   * @param sanitizedHistory - Original conversation history for context truncation
   * @param currentPrompt - Current user prompt for context truncation
   */
  async execute(
    systemPrompt: string,
    messages: Anthropic.MessageParam[],
    initialHistoryLength: number,
    sanitizedHistory: Anthropic.MessageParam[],
    currentPrompt: string,
  ): Promise<void> {
    let turnCount = 0;
    let assistantResponseText = "";
    const allEntities: Entity[] = [];

    try {
      while (turnCount < this.config.maxTurns) {
        turnCount++;
        this.logger.info(
          {
            turn: turnCount,
            maxTurns: this.config.maxTurns,
            messageCount: messages.length,
          },
          "Starting turn",
        );

        // Execute turn with context truncation handling
        const result = await this.executeTurnWithRetry(
          systemPrompt,
          messages,
          turnCount,
          initialHistoryLength,
          sanitizedHistory,
          currentPrompt,
        );

        if (!result.success) {
          // Failed after all retries
          this.emit("done", {
            success: false,
            error: result.error || "Failed to execute turn",
            turns: turnCount,
            entities: allEntities,
          });
          return;
        }

        const { response, currentText, currentToolCalls } = result;

        // Handle text response and extract entities
        if (currentText) {
          this.logger.debug(
            {
              turn: turnCount,
              responseLength: currentText.length,
              responsePreview: truncateForLog(currentText, 200),
              hasToolCalls: currentToolCalls.length > 0,
            },
            "Assistant response received",
          );

          this.emit("thinking", { text: currentText });

          const entities = this.entityExtractor.extract(currentText);
          allEntities.push(...entities);

          if (entities.length > 0) {
            this.logger.info(
              {
                turn: turnCount,
                entitiesExtracted: entities.length,
                entityTypes: [...new Set(entities.map((e) => e.type))],
              },
              "Entities extracted from response",
            );
            this.emit("entities", { entities });
          }

          // Track final response if no tool calls
          if (currentToolCalls.length === 0) {
            assistantResponseText = currentText;
          }
        }

        // Add assistant message to history
        messages.push({
          role: "assistant",
          content: response!.content,
        });

        // If no tool calls, we're done
        if (currentToolCalls.length === 0) {
          this.logger.info(
            {
              turns: turnCount,
              totalEntities: allEntities.length,
              inputTokens: response!.usage.input_tokens,
              outputTokens: response!.usage.output_tokens,
              totalTokens:
                response!.usage.input_tokens + response!.usage.output_tokens,
            },
            "Conversation complete",
          );

          this.emit("done", {
            success: true,
            response: assistantResponseText,
            turns: turnCount,
            entities: allEntities,
            usage: response!.usage,
          });
          return;
        }

        // Execute tool calls
        const toolResults = await this.executeToolCalls(
          currentToolCalls,
          turnCount,
        );

        // Add tool results to conversation
        messages.push({
          role: "user",
          content: toolResults,
        });
      }

      // Hit max turns limit
      if (turnCount >= this.config.maxTurns) {
        this.logger.warn("Hit max turns limit");
        this.emit("done", {
          success: false,
          error: "Max turns reached",
          turns: turnCount,
          entities: allEntities,
        });
      }
    } catch (error) {
      this.logger.error(
        {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        },
        "Fatal error in agent execution",
      );

      this.emit("done", {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        turns: turnCount,
        entities: allEntities,
      });
    }
  }

  /**
   * Execute a turn with context truncation retry logic
   */
  private async executeTurnWithRetry(
    systemPrompt: string,
    messages: Anthropic.MessageParam[],
    turnCount: number,
    initialHistoryLength: number,
    sanitizedHistory: Anthropic.MessageParam[],
    currentPrompt: string,
  ): Promise<{
    success: boolean;
    response?: Anthropic.Message;
    currentText?: string;
    currentToolCalls: Anthropic.Messages.ToolUseBlock[];
    error?: string;
  }> {
    let contextTruncationAttempt = 0;

    while (
      contextTruncationAttempt <
      this.config.maxContextTruncationAttempts
    ) {
      try {
        // Call Claude with streaming (with retry on 429)
        const stream: any = await withRetry(
          () =>
            (this.anthropic as any).messages.create({
              model: this.config.model,
              max_tokens: this.config.maxTokens,
              system: systemPrompt,
              messages,
              tools: this.tools,
              stream: true,
            }),
          `anthropic-stream-turn-${turnCount}`,
          this.logger,
          async (attempt, delayMs) => {
            // Send retry event to frontend
            const delaySeconds = Math.ceil(delayMs / 1000);
            this.emit("retry", {
              attempt,
              delayMs,
              delaySeconds,
              message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
            });
          },
        );

        // Process stream
        let currentText = "";
        for await (const chunk of stream) {
          if (chunk.type === "content_block_start") {
            if (chunk.content_block.type === "text") {
              this.logger.debug("Text block started");
            } else if (chunk.content_block.type === "tool_use") {
              this.logger.debug(
                {
                  toolId: chunk.content_block.id,
                  toolName: chunk.content_block.name,
                },
                "Tool use block started",
              );
            }
          } else if (chunk.type === "content_block_delta") {
            if (chunk.delta.type === "text_delta") {
              const delta = chunk.delta.text;
              currentText += delta;
              this.emit("text", { delta });
            } else if (chunk.delta.type === "input_json_delta") {
              this.logger.debug(
                { partial: chunk.delta.partial_json },
                "Tool input delta",
              );
            }
          } else if (chunk.type === "content_block_stop") {
            this.logger.debug({ index: chunk.index }, "Content block stopped");
          } else if (chunk.type === "message_delta") {
            this.logger.debug(
              { stopReason: chunk.delta.stop_reason },
              "Message delta",
            );
          } else if (chunk.type === "message_stop") {
            this.logger.debug("Message stopped");
          }
        }

        // Make non-streaming call to get complete message with tool calls
        const response = await withRetry<Anthropic.Message>(
          () =>
            (this.anthropic as any).messages.create({
              model: this.config.model,
              max_tokens: this.config.maxTokens,
              system: systemPrompt,
              messages,
              tools: this.tools,
              stream: false,
            }),
          `anthropic-complete-turn-${turnCount}`,
          this.logger,
          async (attempt, delayMs) => {
            const delaySeconds = Math.ceil(delayMs / 1000);
            this.emit("retry", {
              attempt,
              delayMs,
              delaySeconds,
              message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
            });
          },
        );

        // Extract tool calls
        const currentToolCalls = response.content.filter(
          (
            block: Anthropic.Messages.ContentBlock,
          ): block is Anthropic.Messages.ToolUseBlock => block.type === "tool_use",
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

        return {
          success: true,
          response,
          currentText: fullText,
          currentToolCalls,
        };
      } catch (error: any) {
        // Check if this is a context length error
        const isContextError = isContextLengthError(error);

        if (
          isContextError &&
          contextTruncationAttempt <
            this.config.maxContextTruncationAttempts - 1
        ) {
          contextTruncationAttempt++;

          // Get trimmed history
          const trimmedHistory = this.contextTruncationStrategy.truncate(
            sanitizedHistory,
            contextTruncationAttempt,
          );

          this.logger.warn(
            {
              turn: turnCount,
              attempt: contextTruncationAttempt,
              originalHistoryLength: initialHistoryLength,
              trimmedHistoryLength: trimmedHistory.length,
              droppedMessages: initialHistoryLength - trimmedHistory.length,
            },
            "Context length exceeded, trimming history",
          );

          // Notify frontend of context truncation
          this.emit("context_truncated", {
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
          const sessionMessagesStart = initialHistoryLength + 1;
          const sessionMessages = messages.slice(sessionMessagesStart);

          // Rebuild messages array
          messages.length = 0;
          messages.push(...trimmedHistory);
          messages.push({ role: "user", content: currentPrompt });
          messages.push(...sessionMessages);

          this.logger.info(
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
          // Not a context error or exhausted retries
          return {
            success: false,
            currentToolCalls: [],
            error: error instanceof Error ? error.message : "Unknown error",
          };
        }
      }
    }

    // Exhausted all context truncation attempts
    return {
      success: false,
      currentToolCalls: [],
      error: "Failed to create stream after context truncation retries",
    };
  }

  /**
   * Execute tool calls
   */
  private async executeToolCalls(
    toolCalls: Anthropic.Messages.ToolUseBlock[],
    turnCount: number,
  ): Promise<Anthropic.Messages.ToolResultBlockParam[]> {
    this.logger.info(
      {
        toolCount: toolCalls.length,
        tools: toolCalls.map((t) => t.name),
      },
      "Executing tools",
    );

    const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

    for (const toolCall of toolCalls) {
      const toolStartTime = Date.now();
      const description =
        (toolCall.input as any).description || "Executing query...";

      this.logger.debug(
        {
          toolId: toolCall.id,
          toolName: toolCall.name,
          toolInput: toolCall.input,
          turn: turnCount,
        },
        "Tool call started",
      );

      this.emit("tool_call", {
        id: toolCall.id,
        name: toolCall.name,
        description,
      });

      try {
        const result = await executeTool(toolCall.name, toolCall.input);
        const toolElapsedMs = Date.now() - toolStartTime;

        this.logger.info(
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

        this.emit("tool_complete", {
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

        this.logger.error(
          {
            toolId: toolCall.id,
            toolName: toolCall.name,
            toolElapsedMs,
            error: errorMessage,
            errorStack: error instanceof Error ? error.stack : undefined,
          },
          "Tool execution failed",
        );

        this.emit("tool_complete", {
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

        this.emit("tool_error", {
          toolId: toolCall.id,
          error: errorMessage,
        });
      }
    }

    return toolResults;
  }
}
