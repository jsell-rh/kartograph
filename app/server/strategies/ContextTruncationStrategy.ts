/**
 * Strategy for truncating conversation history when context length is exceeded.
 *
 * This is needed when the prompt becomes too long and results in a 413 error.
 * The strategy progressively removes older messages from history while preserving
 * tool_use/tool_result pairing.
 */

import type Anthropic from "@anthropic-ai/sdk";

/**
 * Interface for context truncation strategies.
 */
export interface ContextTruncationStrategy {
  /**
   * Truncate message history based on attempt number.
   *
   * @param originalHistory - The original conversation history
   * @param attempt - The truncation attempt number (0 = first attempt, 1+ = retries)
   * @returns Truncated message history
   */
  truncate(
    originalHistory: Anthropic.MessageParam[],
    attempt: number,
  ): Anthropic.MessageParam[];
}

/**
 * Progressive trimming strategy that removes older messages in stages.
 *
 * Truncation levels:
 * - Attempt 0: Full history
 * - Attempt 1: Last half of history
 * - Attempt 2: Last quarter of history
 * - Attempt 3: Last 5 messages
 * - Attempt 4: Last 2 messages
 * - Attempt 5+: Empty history (current prompt only)
 *
 * IMPORTANT: Ensures tool_use/tool_result pairing is preserved by removing
 * orphaned tool_result messages that would reference truncated tool_use blocks.
 */
export class ProgressiveTrimStrategy implements ContextTruncationStrategy {
  /**
   * Truncate message history progressively based on attempt number.
   */
  truncate(
    originalHistory: Anthropic.MessageParam[],
    attempt: number,
  ): Anthropic.MessageParam[] {
    const historyLength = originalHistory.length;

    let trimmed: Anthropic.MessageParam[];

    switch (attempt) {
      case 0:
        // First attempt: use full history
        trimmed = originalHistory;
        break;
      case 1:
        // Second attempt: keep last half
        trimmed = originalHistory.slice(-Math.ceil(historyLength / 2));
        break;
      case 2:
        // Third attempt: keep last quarter
        trimmed = originalHistory.slice(-Math.ceil(historyLength / 4));
        break;
      case 3:
        // Fourth attempt: keep last 5 messages
        trimmed = originalHistory.slice(-5);
        break;
      case 4:
        // Fifth attempt: keep last 2 messages
        trimmed = originalHistory.slice(-2);
        break;
      default:
        // Final attempt: no history, just current prompt
        return [];
    }

    // Remove orphaned tool_result messages at the start
    // If first message is a user message with tool_results, it references tool_use blocks
    // that were truncated, so we must remove it to avoid API errors
    while (trimmed.length > 0 && trimmed[0] && this.hasToolResults(trimmed[0])) {
      trimmed = trimmed.slice(1);
    }

    return trimmed;
  }

  /**
   * Check if a message contains tool_result blocks.
   *
   * @param message - The message to check
   * @returns True if the message contains tool_result blocks
   */
  private hasToolResults(message: Anthropic.MessageParam): boolean {
    if (message.role !== "user") return false;

    const content = message.content;
    if (typeof content === "string") return false;

    return (
      Array.isArray(content) &&
      content.some((block: any) => block.type === "tool_result")
    );
  }
}
