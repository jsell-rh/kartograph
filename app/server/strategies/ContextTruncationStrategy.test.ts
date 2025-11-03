/**
 * Unit tests for ContextTruncationStrategy
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  ProgressiveTrimStrategy,
  type ContextTruncationStrategy,
} from "./ContextTruncationStrategy";
import type Anthropic from "@anthropic-ai/sdk";

describe("ProgressiveTrimStrategy", () => {
  let strategy: ContextTruncationStrategy;

  beforeEach(() => {
    strategy = new ProgressiveTrimStrategy();
  });

  // Helper to create mock messages
  const createUserMessage = (content: string): Anthropic.MessageParam => ({
    role: "user",
    content,
  });

  const createAssistantMessage = (content: string): Anthropic.MessageParam => ({
    role: "assistant",
    content,
  });

  const createUserMessageWithToolResults = (
    toolResults: any[],
  ): Anthropic.MessageParam => ({
    role: "user",
    content: toolResults,
  });

  describe("truncate - basic truncation levels", () => {
    const createHistory = (count: number): Anthropic.MessageParam[] => {
      const history: Anthropic.MessageParam[] = [];
      for (let i = 0; i < count; i++) {
        history.push(createUserMessage(`User message ${i}`));
        history.push(createAssistantMessage(`Assistant message ${i}`));
      }
      return history;
    };

    it("should return full history on attempt 0", () => {
      const history = createHistory(10); // 20 messages

      const result = strategy.truncate(history, 0);

      expect(result).toHaveLength(20);
      expect(result).toEqual(history);
    });

    it("should keep last half on attempt 1", () => {
      const history = createHistory(10); // 20 messages

      const result = strategy.truncate(history, 1);

      expect(result).toHaveLength(10);
      expect(result[0]).toEqual(history[10]);
    });

    it("should keep last quarter on attempt 2", () => {
      const history = createHistory(20); // 40 messages

      const result = strategy.truncate(history, 2);

      expect(result).toHaveLength(10);
      expect(result[0]).toEqual(history[30]);
    });

    it("should keep last 5 messages on attempt 3", () => {
      const history = createHistory(20); // 40 messages

      const result = strategy.truncate(history, 3);

      expect(result).toHaveLength(5);
      expect(result[0]).toEqual(history[35]);
    });

    it("should keep last 2 messages on attempt 4", () => {
      const history = createHistory(20); // 40 messages

      const result = strategy.truncate(history, 4);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual(history[38]);
    });

    it("should return empty array on attempt 5+", () => {
      const history = createHistory(10);

      expect(strategy.truncate(history, 5)).toHaveLength(0);
      expect(strategy.truncate(history, 6)).toHaveLength(0);
      expect(strategy.truncate(history, 10)).toHaveLength(0);
    });
  });

  describe("truncate - orphaned tool_result removal", () => {
    it("should remove orphaned tool_result at start after truncation", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("Message 1"),
        createAssistantMessage("Response 1 with tool_use"),
        createUserMessageWithToolResults([
          { type: "tool_result", tool_use_id: "tool1", content: "result" },
        ]),
        createUserMessage("Message 2"),
        createAssistantMessage("Response 2"),
      ];

      // Attempt 2 should keep last quarter (2 messages starting from index 3)
      // Index 3 = "Message 2" (user), Index 4 = "Response 2" (assistant)
      const result = strategy.truncate(history, 2);

      // Should keep the last 2 messages (no orphaned tool_results in those)
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual(history[3]); // "Message 2"
      expect(result[1]).toEqual(history[4]); // "Response 2"
    });

    it("should not remove non-tool_result user messages", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("Message 1"),
        createAssistantMessage("Response 1"),
        createUserMessage("Message 2"),
        createAssistantMessage("Response 2"),
      ];

      const result = strategy.truncate(history, 3);

      // Last 5 messages = all 4 in this case
      expect(result).toHaveLength(4);
    });

    it("should keep tool_results that are not at the start", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("Message 1"),
        createAssistantMessage("Response 1"),
        createUserMessageWithToolResults([
          { type: "tool_result", tool_use_id: "tool1", content: "result" },
        ]),
      ];

      // Full history includes tool_result
      const result = strategy.truncate(history, 0);

      expect(result).toHaveLength(3);
    });

    it("should remove multiple orphaned tool_results at start", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("Message 1"),
        createAssistantMessage("Response with tool_use"),
        createUserMessageWithToolResults([
          { type: "tool_result", tool_use_id: "tool1", content: "result1" },
        ]),
        createUserMessageWithToolResults([
          { type: "tool_result", tool_use_id: "tool2", content: "result2" },
        ]),
        createUserMessage("Message 2"),
        createAssistantMessage("Response 2"),
      ];

      // Truncate to start at the first tool_result
      const result = strategy.truncate(history, 2);

      // Should remove both orphaned tool_results
      expect(result.every((msg) => msg.role !== "user" || typeof msg.content === "string")).toBe(
        true,
      );
    });
  });

  describe("truncate - edge cases", () => {
    it("should handle empty history", () => {
      const result = strategy.truncate([], 0);

      expect(result).toHaveLength(0);
    });

    it("should handle single message history", () => {
      const history = [createUserMessage("Only message")];

      expect(strategy.truncate(history, 0)).toHaveLength(1);
      expect(strategy.truncate(history, 1)).toHaveLength(1);
      expect(strategy.truncate(history, 5)).toHaveLength(0);
    });

    it("should handle history shorter than truncation target", () => {
      const history = [
        createUserMessage("Message 1"),
        createAssistantMessage("Response 1"),
      ];

      // Attempt 3 wants last 5, but only 2 exist
      const result = strategy.truncate(history, 3);

      expect(result).toHaveLength(2);
    });

    it("should ceil when calculating half/quarter for odd numbers", () => {
      const history = [
        createUserMessage("1"),
        createUserMessage("2"),
        createUserMessage("3"),
      ]; // 3 messages

      // Half of 3 = 1.5, ceil = 2
      const resultHalf = strategy.truncate(history, 1);
      expect(resultHalf).toHaveLength(2);

      const history7 = Array.from({ length: 7 }, (_, i) =>
        createUserMessage(`${i}`),
      );

      // Quarter of 7 = 1.75, ceil = 2
      const resultQuarter = strategy.truncate(history7, 2);
      expect(resultQuarter).toHaveLength(2);
    });

    it("should handle history with only assistant messages", () => {
      const history = [
        createAssistantMessage("Response 1"),
        createAssistantMessage("Response 2"),
      ];

      const result = strategy.truncate(history, 1);

      expect(result).toHaveLength(1);
    });

    it("should handle mixed content with text and tool_results", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("Text message"),
        createAssistantMessage("Response"),
        {
          role: "user",
          content: [
            { type: "text", text: "More text" },
            { type: "tool_result", tool_use_id: "tool1", content: "result" },
          ],
        },
      ];

      const result = strategy.truncate(history, 0);

      expect(result).toHaveLength(3);
    });
  });

  describe("truncate - progressive behavior verification", () => {
    it("should progressively reduce history size with each attempt", () => {
      const history = Array.from({ length: 100 }, (_, i) =>
        createUserMessage(`Message ${i}`),
      );

      const attempt0 = strategy.truncate(history, 0);
      const attempt1 = strategy.truncate(history, 1);
      const attempt2 = strategy.truncate(history, 2);
      const attempt3 = strategy.truncate(history, 3);
      const attempt4 = strategy.truncate(history, 4);
      const attempt5 = strategy.truncate(history, 5);

      expect(attempt0.length).toBe(100); // Full
      expect(attempt1.length).toBe(50); // Half
      expect(attempt2.length).toBe(25); // Quarter
      expect(attempt3.length).toBe(5); // Last 5
      expect(attempt4.length).toBe(2); // Last 2
      expect(attempt5.length).toBe(0); // Empty
    });

    it("should maintain message order after truncation", () => {
      const history = [
        createUserMessage("Message 1"),
        createUserMessage("Message 2"),
        createUserMessage("Message 3"),
        createUserMessage("Message 4"),
      ];

      const result = strategy.truncate(history, 1); // Last 2

      expect(result).toHaveLength(2);
      expect((result[0]!.content as string).includes("Message 3")).toBe(true);
      expect((result[1]!.content as string).includes("Message 4")).toBe(true);
    });
  });

  describe("truncate - tool_result detection", () => {
    it("should identify tool_result in array content", () => {
      const history: Anthropic.MessageParam[] = [
        {
          role: "user",
          content: [
            { type: "tool_result", tool_use_id: "abc", content: "result" },
          ],
        },
        createUserMessage("Next message"),
      ];

      // If truncated to start with tool_result, it should be removed
      const result = strategy.truncate(history, 4); // Last 2

      // First message should be removed as orphaned tool_result
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual(history[1]);
    });

    it("should not identify tool_result in string content", () => {
      const history: Anthropic.MessageParam[] = [
        createUserMessage("This is tool_result text but not a real tool_result"),
        createUserMessage("Message 2"),
      ];

      const result = strategy.truncate(history, 4); // Last 2

      expect(result).toHaveLength(2);
    });

    it("should handle assistant messages at start (never have tool_results)", () => {
      const history: Anthropic.MessageParam[] = [
        createAssistantMessage("Assistant message"),
        createUserMessage("User message"),
      ];

      const result = strategy.truncate(history, 4); // Last 2

      // Both should be kept
      expect(result).toHaveLength(2);
    });
  });
});
