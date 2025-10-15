/**
 * DELETE /api/tokens/:id
 *
 * Revoke an API token (soft delete)
 */

import { getSession } from "../../utils/auth";
import { db } from "../../db";
import { apiTokens } from "../../db/schema";
import { eq, and } from "drizzle-orm";
import { createLogger } from "../../lib/logger";

const log = createLogger("revoke-token-api");

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

    // Get token ID from route params
    const tokenId = getRouterParam(event, "id");

    if (!tokenId) {
      throw createError({
        statusCode: 400,
        message: "Missing token ID",
      });
    }

    // Verify token exists and belongs to user
    const existing = await db
      .select()
      .from(apiTokens)
      .where(and(eq(apiTokens.id, tokenId), eq(apiTokens.userId, userId)))
      .limit(1);

    if (!existing || existing.length === 0 || !existing[0]) {
      throw createError({
        statusCode: 404,
        message: "Token not found",
      });
    }

    // Soft delete by setting revokedAt
    const now = new Date();
    await db
      .update(apiTokens)
      .set({ revokedAt: now })
      .where(eq(apiTokens.id, tokenId));

    log.info(
      {
        userId,
        tokenId,
        tokenName: existing[0].name,
      },
      "API token revoked",
    );

    return {
      success: true,
      message: "Token revoked successfully",
    };
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to revoke API token",
    );

    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }

    throw createError({
      statusCode: 500,
      message: "Failed to revoke API token",
    });
  }
});
