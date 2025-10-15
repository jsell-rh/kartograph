/**
 * Retry utilities with exponential backoff for API rate limiting
 *
 * Features:
 * - Exponential backoff with jitter
 * - Configurable max retries
 * - Rate limit detection (429 errors)
 * - Progress callbacks for UI updates
 * - Comprehensive logging
 */

import type { Logger } from "pino";

export interface RetryOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  onRetry?: (
    attempt: number,
    delayMs: number,
    error: any,
  ) => void | Promise<void>;
}

export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: any;
  attempts: number;
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff with jitter
 * Formula: min(maxDelay, baseDelay * 2^attempt) + random(0, 1000)
 */
function calculateBackoff(
  attempt: number,
  baseDelayMs: number,
  maxDelayMs: number,
): number {
  const exponentialDelay = baseDelayMs * Math.pow(2, attempt);
  const capped = Math.min(exponentialDelay, maxDelayMs);
  const jitter = Math.random() * 1000; // Add 0-1000ms jitter to prevent thundering herd
  return Math.floor(capped + jitter);
}

/**
 * Check if error is a rate limit error (429)
 */
function isRateLimitError(error: any): boolean {
  // Check for Anthropic SDK rate limit errors
  if (error?.status === 429) return true;
  if (error?.error?.type === "rate_limit_error") return true;
  if (error?.message?.includes("rate limit")) return true;
  if (error?.message?.includes("429")) return true;
  return false;
}

/**
 * Retry a function with exponential backoff
 *
 * @param fn - Async function to retry
 * @param options - Retry configuration
 * @param logger - Pino logger for structured logging
 * @returns Result with success status, data, and metadata
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
  logger?: Logger,
): Promise<RetryResult<T>> {
  const {
    maxRetries = 5,
    baseDelayMs = 1000,
    maxDelayMs = 30000,
    onRetry,
  } = options;

  let lastError: any;
  let attempt = 0;

  while (attempt <= maxRetries) {
    try {
      logger?.debug({ attempt, maxRetries }, "Attempting operation");
      const result = await fn();

      if (attempt > 0) {
        logger?.info(
          { attempt, succeeded: true },
          "Operation succeeded after retry",
        );
      }

      return {
        success: true,
        data: result,
        attempts: attempt + 1,
      };
    } catch (error) {
      lastError = error;

      // Check if this is a retryable error
      const isRetryable = isRateLimitError(error);

      if (!isRetryable) {
        logger?.warn(
          {
            attempt,
            error: error instanceof Error ? error.message : String(error),
            retryable: false,
          },
          "Non-retryable error encountered",
        );
        return {
          success: false,
          error,
          attempts: attempt + 1,
        };
      }

      // If we've exhausted retries, fail
      if (attempt >= maxRetries) {
        logger?.error(
          {
            attempt,
            maxRetries,
            error: error instanceof Error ? error.message : String(error),
          },
          "Max retries exceeded",
        );
        return {
          success: false,
          error,
          attempts: attempt + 1,
        };
      }

      // Calculate backoff delay
      const delayMs = calculateBackoff(attempt, baseDelayMs, maxDelayMs);

      logger?.warn(
        {
          attempt: attempt + 1,
          maxRetries,
          delayMs,
          delaySeconds: Math.round(delayMs / 1000),
          error: error instanceof Error ? error.message : String(error),
          isRateLimit: isRateLimitError(error),
        },
        "Rate limit hit, retrying with backoff",
      );

      // Call retry callback (for UI updates)
      if (onRetry) {
        try {
          await onRetry(attempt + 1, delayMs, error);
        } catch (callbackError) {
          logger?.warn({ callbackError }, "Retry callback failed");
        }
      }

      // Wait before retrying
      await sleep(delayMs);
      attempt++;
    }
  }

  // Should never reach here, but for type safety
  return {
    success: false,
    error: lastError,
    attempts: attempt,
  };
}

/**
 * Wrap Anthropic API calls with automatic retry
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  context: string,
  logger?: Logger,
  onRetry?: (attempt: number, delayMs: number) => void | Promise<void>,
): Promise<T> {
  const result = await retryWithBackoff(
    fn,
    {
      maxRetries: 5,
      baseDelayMs: 2000,
      maxDelayMs: 60000,
      onRetry: async (attempt, delayMs, error) => {
        logger?.warn(
          {
            context,
            attempt,
            delayMs,
            delaySeconds: Math.round(delayMs / 1000),
            error: error instanceof Error ? error.message : String(error),
          },
          "Retrying after rate limit",
        );

        if (onRetry) {
          await onRetry(attempt, delayMs);
        }
      },
    },
    logger,
  );

  if (!result.success) {
    throw result.error;
  }

  return result.data as T;
}
