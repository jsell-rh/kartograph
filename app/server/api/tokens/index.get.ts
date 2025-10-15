/**
 * GET /api/tokens
 *
 * List all API tokens for the authenticated user
 */

import { getSession } from "../../utils/auth";
import { db } from "../../db";
import { apiTokens } from "../../db/schema";
import { eq } from "drizzle-orm";
import { createLogger } from "../../lib/logger";

const log = createLogger("list-tokens-api");

export default defineEventHandler(async (event) => {
  try {
    // Get authenticated user
    const session = await getSession(event);
    if (!session?.user?.id) {
      throw createError({
        statusCode: 401,
        message: "Unauthorized",
      });
    }

    const userId = session.user.id;

    // Fetch user's tokens
    const tokens = await db
      .select({
        id: apiTokens.id,
        name: apiTokens.name,
        totalQueries: apiTokens.totalQueries,
        lastUsedAt: apiTokens.lastUsedAt,
        expiresAt: apiTokens.expiresAt,
        createdAt: apiTokens.createdAt,
        revokedAt: apiTokens.revokedAt,
      })
      .from(apiTokens)
      .where(eq(apiTokens.userId, userId))
      .orderBy(apiTokens.createdAt);

    log.info(
      {
        userId,
        tokenCount: tokens.length,
      },
      "Listed API tokens",
    );

    return {
      tokens: tokens.map((token) => ({
        id: token.id,
        name: token.name,
        totalQueries: token.totalQueries,
        lastUsedAt: token.lastUsedAt ? token.lastUsedAt.toISOString() : null,
        expiresAt: token.expiresAt.toISOString(),
        createdAt: token.createdAt.toISOString(),
        revokedAt: token.revokedAt ? token.revokedAt.toISOString() : null,
        isActive: !token.revokedAt && token.expiresAt > new Date(),
      })),
    };
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to list API tokens",
    );

    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }

    throw createError({
      statusCode: 500,
      message: "Failed to list API tokens",
    });
  }
});
