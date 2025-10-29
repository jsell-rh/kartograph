/**
 * Error utility functions for handling Anthropic API errors and context length errors.
 */

/**
 * Extract a user-friendly error message from Anthropic API errors.
 * Handles nested error structures like: { error: { error: { message: "..." } } }
 *
 * @param error - The error object from Anthropic API
 * @returns User-friendly error message
 */
export function extractErrorMessage(error: any): string {
  // Check for nested Anthropic error structure
  if (error?.error?.error?.message) {
    return error.error.error.message;
  }

  // Check for single-level nested error
  if (error?.error?.message) {
    return error.error.message;
  }

  // Check for direct message
  if (error?.message) {
    return error.message;
  }

  // Fallback
  return "An error occurred while processing your request";
}

/**
 * Check if an error is a context length error (413 or "prompt is too long").
 *
 * @param error - The error object to check
 * @returns True if the error is a context length error
 */
export function isContextLengthError(error: any): boolean {
  return (
    error?.status === 413 ||
    error?.error?.message?.toLowerCase().includes("prompt is too long") ||
    error?.message?.toLowerCase().includes("prompt is too long")
  );
}
