/**
 * API Token Authentication Middleware
 *
 * Validates Bearer tokens for MCP server endpoints.
 * Checks token validity, expiry, and revocation status.
 *
 * Usage:
 *   Authorization: Bearer cart_example123456789012345678901
 */

import { db } from "../db";
import { apiTokens } from "../db/schema";
import { eq } from "drizzle-orm";
import { hashToken, isValidTokenFormat } from "../utils/tokens";
import { createLogger } from "../lib/logger";

const log = createLogger("token-auth-middleware");

interface TokenAuthContext {
  tokenId: string;
  userId: string;
  tokenName: string;
}

/**
 * Extract and validate API token from request
 *
 * Sets event.context.tokenAuth if valid
 * Throws 401 error if invalid
 */
export async function validateApiToken(event: any): Promise<TokenAuthContext> {
  // Extract Authorization header
  const authHeader = getHeader(event, "Authorization");

  if (!authHeader) {
    throw createError({
      statusCode: 401,
      message: "Missing Authorization header",
    });
  }

  // Parse Bearer token
  const parts = authHeader.split(" ");
  if (parts.length !== 2 || parts[0] !== "Bearer" || !parts[1]) {
    throw createError({
      statusCode: 401,
      message: "Invalid Authorization header format. Expected: Bearer <token>",
    });
  }

  const token = parts[1]; // Guaranteed to be defined by check above

  // Validate token format
  if (!isValidTokenFormat(token)) {
    log.warn(
      {
        tokenPreview: token.substring(0, 10),
        tokenLength: token.length,
        expectedLength: 37,
      },
      "Invalid token format",
    );
    throw createError({
      statusCode: 401,
      message: "Invalid token format",
    });
  }

  // Hash token for lookup
  const tokenHash = hashToken(token);

  // Find token in database
  const result = await db
    .select({
      id: apiTokens.id,
      userId: apiTokens.userId,
      name: apiTokens.name,
      expiresAt: apiTokens.expiresAt,
      revokedAt: apiTokens.revokedAt,
    })
    .from(apiTokens)
    .where(eq(apiTokens.tokenHash, tokenHash))
    .limit(1);

  if (!result || result.length === 0) {
    log.warn({ tokenHash: tokenHash.substring(0, 16) }, "Token not found");
    throw createError({
      statusCode: 401,
      message: "Invalid token",
    });
  }

  const tokenRecord = result[0];

  if (!tokenRecord) {
    log.warn(
      { tokenHash: tokenHash.substring(0, 16) },
      "Token not found (no record)",
    );
    throw createError({
      statusCode: 401,
      message: "Invalid token",
    });
  }

  // Check if revoked
  if (tokenRecord.revokedAt) {
    log.warn(
      {
        tokenId: tokenRecord.id,
        revokedAt: tokenRecord.revokedAt,
      },
      "Attempted use of revoked token",
    );
    throw createError({
      statusCode: 401,
      message: "Token has been revoked",
    });
  }

  // Check if expired
  const now = new Date();
  if (tokenRecord.expiresAt && tokenRecord.expiresAt < now) {
    log.warn(
      {
        tokenId: tokenRecord.id,
        expiresAt: tokenRecord.expiresAt,
      },
      "Attempted use of expired token",
    );
    throw createError({
      statusCode: 401,
      message: "Token has expired",
    });
  }

  // Ensure required fields exist
  if (!tokenRecord.id || !tokenRecord.userId || !tokenRecord.name) {
    log.error({ tokenRecord }, "Token record missing required fields");
    throw createError({
      statusCode: 500,
      message: "Invalid token data",
    });
  }

  // Token is valid!
  log.debug(
    {
      tokenId: tokenRecord.id,
      userId: tokenRecord.userId,
      tokenName: tokenRecord.name,
    },
    "Token authenticated successfully",
  );

  return {
    tokenId: tokenRecord.id,
    userId: tokenRecord.userId,
    tokenName: tokenRecord.name,
  };
}

/**
 * Nitro middleware to protect MCP endpoints
 *
 * Only applies to /api/mcp routes
 */
export default defineEventHandler(async (event) => {
  // Only apply to MCP endpoints
  const path = event.path;
  if (!path.startsWith("/api/mcp")) {
    return;
  }

  // Debug: Log auth check (without sensitive data)
  log.debug(
    {
      path,
      hasAuthHeader: !!getHeader(event, "Authorization"),
    },
    "MCP auth check",
  );

  try {
    // Validate token and set context
    const authContext = await validateApiToken(event);
    event.context.tokenAuth = authContext;
  } catch (error) {
    // Let the error propagate (Nitro will handle 401 responses)
    throw error;
  }
});
