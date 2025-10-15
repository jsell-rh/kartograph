/**
 * Rate Limiter
 *
 * Implements sliding window rate limiting per API token.
 * Tracks query timestamps in memory to enforce request limits.
 */

import { createLogger } from "./logger";

const log = createLogger("rate-limiter");

/**
 * In-memory sliding window tracker
 * Maps tokenId → array of query timestamps (ms since epoch)
 */
const queryWindows = new Map<string, number[]>();

/**
 * Check if a token has exceeded its rate limit
 *
 * @param tokenId - The API token ID
 * @param limitPerHour - Maximum queries allowed per hour
 * @returns Object indicating if request is allowed and retry time if not
 */
export function checkRateLimit(
  tokenId: string,
  limitPerHour: number,
): {
  allowed: boolean;
  retryAfter?: number;
  currentCount?: number;
} {
  const now = Date.now();
  const oneHourAgo = now - 60 * 60 * 1000;

  // Get or create window for this token
  let window = queryWindows.get(tokenId) || [];

  // Remove timestamps older than 1 hour (sliding window)
  window = window.filter((timestamp) => timestamp > oneHourAgo);

  // Check if under limit
  if (window.length >= limitPerHour) {
    // Calculate when the oldest query will expire
    const oldestTimestamp = window[0]!; // Safe: array has at least limitPerHour items
    const retryAfter = Math.ceil(
      (oldestTimestamp + 60 * 60 * 1000 - now) / 1000,
    );

    log.warn(
      {
        tokenId,
        currentCount: window.length,
        limit: limitPerHour,
        retryAfter,
      },
      "Rate limit exceeded",
    );

    return {
      allowed: false,
      retryAfter,
      currentCount: window.length,
    };
  }

  // Add current timestamp to window
  window.push(now);
  queryWindows.set(tokenId, window);

  log.debug(
    {
      tokenId,
      currentCount: window.length,
      limit: limitPerHour,
    },
    "Rate limit check passed",
  );

  return {
    allowed: true,
    currentCount: window.length,
  };
}

/**
 * Clean up old entries from rate limiter
 * Should be called periodically to prevent memory leaks
 *
 * @param maxAge - Maximum age of entries to keep (default: 2 hours)
 */
export function cleanupRateLimiter(maxAge: number = 2 * 60 * 60 * 1000) {
  const now = Date.now();
  const cutoff = now - maxAge;

  let removedCount = 0;

  for (const [tokenId, window] of queryWindows.entries()) {
    // Remove old timestamps
    const filtered = window.filter((timestamp) => timestamp > cutoff);

    if (filtered.length === 0) {
      // No recent activity, remove entire token entry
      queryWindows.delete(tokenId);
      removedCount++;
    } else if (filtered.length < window.length) {
      // Update with filtered timestamps
      queryWindows.set(tokenId, filtered);
    }
  }

  if (removedCount > 0) {
    log.info(
      {
        removedTokens: removedCount,
        remainingTokens: queryWindows.size,
      },
      "Rate limiter cleanup completed",
    );
  }

  return removedCount;
}

/**
 * Get current rate limit stats for a token
 *
 * @param tokenId - The API token ID
 * @returns Current query count and when window resets
 */
export function getRateLimitStats(tokenId: string): {
  currentCount: number;
  oldestQueryAt?: Date;
  windowResetsIn?: number;
} {
  const window = queryWindows.get(tokenId) || [];
  const now = Date.now();

  if (window.length === 0) {
    return { currentCount: 0 };
  }

  const oneHourAgo = now - 60 * 60 * 1000;
  const recentQueries = window.filter((timestamp) => timestamp > oneHourAgo);
  const oldestTimestamp = recentQueries[0];

  return {
    currentCount: recentQueries.length,
    oldestQueryAt: oldestTimestamp ? new Date(oldestTimestamp) : undefined,
    windowResetsIn: oldestTimestamp
      ? Math.ceil((oldestTimestamp + 60 * 60 * 1000 - now) / 1000)
      : undefined,
  };
}

// Schedule periodic cleanup (every hour)
if (typeof setInterval !== "undefined") {
  setInterval(
    () => {
      cleanupRateLimiter();
    },
    60 * 60 * 1000,
  );

  log.info("Rate limiter cleanup scheduled (every 60 minutes)");
}
