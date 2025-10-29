/**
 * Server-Sent Events (SSE) Stream Manager
 *
 * Encapsulates SSE stream operations for sending events to the client.
 * Manages stream lifecycle and ensures events are not sent after stream closes.
 */

export class SSEStreamManager {
  private streamClosed = false;
  private encoder = new TextEncoder();

  /**
   * Create a new SSE stream manager
   *
   * @param controller - The ReadableStream controller to write to
   */
  constructor(private controller: ReadableStreamDefaultController) {}

  /**
   * Push an SSE event to the client
   *
   * @param eventType - The event type (e.g., "thinking", "tool_call", "done")
   * @param data - The event data (will be JSON.stringify'd)
   */
  pushEvent(eventType: string, data: any): void {
    if (this.streamClosed) return;
    const message = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
    this.controller.enqueue(this.encoder.encode(message));
  }

  /**
   * Send a keepalive comment to prevent timeout
   */
  keepalive(): void {
    if (this.streamClosed) return;
    this.controller.enqueue(this.encoder.encode(":\n\n"));
  }

  /**
   * Close the stream
   * Marks stream as closed and calls controller.close()
   */
  close(): void {
    if (!this.streamClosed) {
      this.streamClosed = true;
      this.controller.close();
    }
  }

  /**
   * Check if the stream has been closed
   *
   * @returns True if the stream is closed
   */
  isClosed(): boolean {
    return this.streamClosed;
  }
}
