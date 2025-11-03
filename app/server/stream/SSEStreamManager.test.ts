/**
 * Unit tests for SSEStreamManager
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { SSEStreamManager } from "./SSEStreamManager";

describe("SSEStreamManager", () => {
  let mockController: ReadableStreamDefaultController;
  let enqueuedData: Uint8Array[];
  let closeCalled: boolean;

  beforeEach(() => {
    enqueuedData = [];
    closeCalled = false;

    // Mock controller
    mockController = {
      enqueue: vi.fn((chunk: Uint8Array) => {
        enqueuedData.push(chunk);
      }),
      close: vi.fn(() => {
        closeCalled = true;
      }),
    } as any;
  });

  // Helper to decode enqueued data
  const getLastEnqueuedString = (): string => {
    if (enqueuedData.length === 0) return "";
    const lastChunk = enqueuedData[enqueuedData.length - 1];
    return new TextDecoder().decode(lastChunk);
  };

  const getAllEnqueuedStrings = (): string[] => {
    return enqueuedData.map((chunk) => new TextDecoder().decode(chunk));
  };

  describe("pushEvent", () => {
    it("should push event with correct SSE format", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("test_event", { message: "Hello" });

      const output = getLastEnqueuedString();
      expect(output).toBe(
        'event: test_event\ndata: {"message":"Hello"}\n\n',
      );
    });

    it("should push multiple events", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("event1", { data: "first" });
      manager.pushEvent("event2", { data: "second" });

      const outputs = getAllEnqueuedStrings();
      expect(outputs).toHaveLength(2);
      expect(outputs[0]).toContain("event: event1");
      expect(outputs[1]).toContain("event: event2");
    });

    it("should JSON stringify event data", () => {
      const manager = new SSEStreamManager(mockController);

      const complexData = {
        nested: { value: 42 },
        array: [1, 2, 3],
        string: "test",
      };

      manager.pushEvent("complex", complexData);

      const output = getLastEnqueuedString();
      expect(output).toContain(JSON.stringify(complexData));
    });

    it("should not push events after stream is closed", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();
      manager.pushEvent("should_not_send", { data: "test" });

      // Only close should be called, no enqueue for the event
      expect(mockController.enqueue).toHaveBeenCalledTimes(0);
    });

    it("should handle empty data object", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("empty", {});

      const output = getLastEnqueuedString();
      expect(output).toBe("event: empty\ndata: {}\n\n");
    });

    it("should handle null data", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("null_event", null);

      const output = getLastEnqueuedString();
      expect(output).toBe("event: null_event\ndata: null\n\n");
    });

    it("should handle array data", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("array_event", [1, 2, 3]);

      const output = getLastEnqueuedString();
      expect(output).toBe("event: array_event\ndata: [1,2,3]\n\n");
    });

    it("should handle string data", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("string_event", "plain string");

      const output = getLastEnqueuedString();
      expect(output).toBe('event: string_event\ndata: "plain string"\n\n');
    });

    it("should handle numeric data", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("number_event", 42);

      const output = getLastEnqueuedString();
      expect(output).toBe("event: number_event\ndata: 42\n\n");
    });

    it("should handle boolean data", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("bool_event", true);

      const output = getLastEnqueuedString();
      expect(output).toBe("event: bool_event\ndata: true\n\n");
    });

    it("should properly encode special characters", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("special", { message: "Line 1\nLine 2\tTab" });

      const output = getLastEnqueuedString();
      // JSON.stringify should escape newlines and tabs
      expect(output).toContain("\\n");
      expect(output).toContain("\\t");
    });
  });

  describe("keepalive", () => {
    it("should send SSE comment for keepalive", () => {
      const manager = new SSEStreamManager(mockController);

      manager.keepalive();

      const output = getLastEnqueuedString();
      expect(output).toBe(":\n\n");
    });

    it("should send multiple keepalives", () => {
      const manager = new SSEStreamManager(mockController);

      manager.keepalive();
      manager.keepalive();
      manager.keepalive();

      expect(mockController.enqueue).toHaveBeenCalledTimes(3);
      expect(getAllEnqueuedStrings()).toEqual([":\n\n", ":\n\n", ":\n\n"]);
    });

    it("should not send keepalive after stream is closed", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();
      manager.keepalive();

      expect(mockController.enqueue).toHaveBeenCalledTimes(0);
    });
  });

  describe("close", () => {
    it("should close the stream", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();

      expect(closeCalled).toBe(true);
    });

    it("should only close once even if called multiple times", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();
      manager.close();
      manager.close();

      expect(mockController.close).toHaveBeenCalledTimes(1);
    });

    it("should prevent events after close", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();
      manager.pushEvent("after_close", { data: "test" });

      expect(mockController.enqueue).toHaveBeenCalledTimes(0);
    });

    it("should prevent keepalive after close", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();
      manager.keepalive();

      expect(mockController.enqueue).toHaveBeenCalledTimes(0);
    });
  });

  describe("isClosed", () => {
    it("should return false initially", () => {
      const manager = new SSEStreamManager(mockController);

      expect(manager.isClosed()).toBe(false);
    });

    it("should return true after close", () => {
      const manager = new SSEStreamManager(mockController);

      manager.close();

      expect(manager.isClosed()).toBe(true);
    });

    it("should allow checking closed state without side effects", () => {
      const manager = new SSEStreamManager(mockController);

      manager.isClosed();
      manager.isClosed();
      manager.isClosed();

      // Should not affect controller
      expect(mockController.enqueue).toHaveBeenCalledTimes(0);
      expect(mockController.close).toHaveBeenCalledTimes(0);
    });
  });

  describe("integration scenarios", () => {
    it("should handle typical event stream lifecycle", () => {
      const manager = new SSEStreamManager(mockController);

      // Initial keepalive
      manager.keepalive();

      // Send some events
      manager.pushEvent("start", { status: "starting" });
      manager.pushEvent("progress", { percent: 50 });
      manager.pushEvent("done", { status: "complete" });

      // Close stream
      manager.close();

      // Verify all were sent
      expect(mockController.enqueue).toHaveBeenCalledTimes(4);
      expect(closeCalled).toBe(true);
    });

    it("should handle event/keepalive interleaving", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("event1", { data: 1 });
      manager.keepalive();
      manager.pushEvent("event2", { data: 2 });
      manager.keepalive();
      manager.pushEvent("event3", { data: 3 });

      const outputs = getAllEnqueuedStrings();
      expect(outputs).toHaveLength(5);
      expect(outputs[0]).toContain("event1");
      expect(outputs[1]).toBe(":\n\n");
      expect(outputs[2]).toContain("event2");
      expect(outputs[3]).toBe(":\n\n");
      expect(outputs[4]).toContain("event3");
    });

    it("should gracefully handle close in middle of operations", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("before_close", { data: "sent" });
      manager.close();
      manager.pushEvent("after_close", { data: "not sent" });

      // Only 1 event + close
      expect(mockController.enqueue).toHaveBeenCalledTimes(1);
      expect(mockController.close).toHaveBeenCalledTimes(1);
    });
  });

  describe("encoding", () => {
    it("should use TextEncoder for UTF-8 encoding", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("emoji", { message: "Hello 🌍" });

      const output = getLastEnqueuedString();
      expect(output).toContain("Hello 🌍");
    });

    it("should handle unicode characters", () => {
      const manager = new SSEStreamManager(mockController);

      manager.pushEvent("unicode", { text: "Ñoño - 中文 - العربية" });

      const output = getLastEnqueuedString();
      expect(output).toContain("Ñoño");
      expect(output).toContain("中文");
      expect(output).toContain("العربية");
    });
  });
});
