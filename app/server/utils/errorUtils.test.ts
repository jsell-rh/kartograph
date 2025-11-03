/**
 * Unit tests for error utility functions
 */

import { describe, it, expect } from "vitest";
import { extractErrorMessage, isContextLengthError } from "./errorUtils";

describe("extractErrorMessage", () => {
  it("should extract message from triple-nested error structure", () => {
    const error = {
      error: {
        error: {
          message: "Nested error message",
        },
      },
    };

    expect(extractErrorMessage(error)).toBe("Nested error message");
  });

  it("should extract message from double-nested error structure", () => {
    const error = {
      error: {
        message: "Double nested error",
      },
    };

    expect(extractErrorMessage(error)).toBe("Double nested error");
  });

  it("should extract message from direct error structure", () => {
    const error = {
      message: "Direct error message",
    };

    expect(extractErrorMessage(error)).toBe("Direct error message");
  });

  it("should extract message from Error instance", () => {
    const error = new Error("Error instance message");

    expect(extractErrorMessage(error)).toBe("Error instance message");
  });

  it("should return fallback message for error without message", () => {
    const error = {
      code: 500,
    };

    expect(extractErrorMessage(error)).toBe(
      "An error occurred while processing your request",
    );
  });

  it("should return fallback message for null", () => {
    expect(extractErrorMessage(null)).toBe(
      "An error occurred while processing your request",
    );
  });

  it("should return fallback message for undefined", () => {
    expect(extractErrorMessage(undefined)).toBe(
      "An error occurred while processing your request",
    );
  });

  it("should handle empty string message", () => {
    const error = {
      message: "",
    };

    // Empty string is falsy, so should return fallback
    expect(extractErrorMessage(error)).toBe(
      "An error occurred while processing your request",
    );
  });
});

describe("isContextLengthError", () => {
  it("should return true for 413 status code", () => {
    const error = {
      status: 413,
    };

    expect(isContextLengthError(error)).toBe(true);
  });

  it('should return true for "prompt is too long" in nested error message', () => {
    const error = {
      error: {
        message: "The prompt is too long for processing",
      },
    };

    expect(isContextLengthError(error)).toBe(true);
  });

  it('should return true for "prompt is too long" in direct message', () => {
    const error = {
      message: "Error: prompt is too long",
    };

    expect(isContextLengthError(error)).toBe(true);
  });

  it("should be case-insensitive for prompt too long check", () => {
    const error1 = {
      message: "PROMPT IS TOO LONG",
    };

    const error2 = {
      message: "Prompt Is Too Long",
    };

    expect(isContextLengthError(error1)).toBe(true);
    expect(isContextLengthError(error2)).toBe(true);
  });

  it("should return false for non-context-length errors", () => {
    const error = {
      status: 500,
      message: "Internal server error",
    };

    expect(isContextLengthError(error)).toBe(false);
  });

  it("should return false for 401 status", () => {
    const error = {
      status: 401,
      message: "Unauthorized",
    };

    expect(isContextLengthError(error)).toBe(false);
  });

  it("should return false for null", () => {
    expect(isContextLengthError(null)).toBe(false);
  });

  it("should return false for undefined", () => {
    expect(isContextLengthError(undefined)).toBe(false);
  });

  it("should return false for error without status or message", () => {
    const error = {
      code: "SOME_CODE",
    };

    expect(isContextLengthError(error)).toBe(false);
  });
});
