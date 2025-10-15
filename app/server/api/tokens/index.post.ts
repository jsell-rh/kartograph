/**
 * POST /api/tokens
 *
 * Create a new API token for MCP server access
 */

import { getSession } from "../../utils/auth";
import { db } from "../../db";
import { apiTokens } from "../../db/schema";
import { generateToken } from "../../utils/tokens";
import { createLogger } from "../../lib/logger";

const log = createLogger("create-token-api");

interface CreateTokenRequest {
  name: string;
  expiryDays?: number;
}

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

    // Parse request body
    const body = await readBody<CreateTokenRequest>(event);

    if (
      !body.name ||
      typeof body.name !== "string" ||
      body.name.trim().length === 0
    ) {
      throw createError({
        statusCode: 400,
        message: "Token name is required",
      });
    }

    // Get configuration
    const config = useRuntimeConfig(event);
    const maxExpiryDays = Number(config.apiTokenMaxExpiryDays) || 365;
    const defaultExpiryDays = Number(config.apiTokenDefaultExpiryDays) || 90;

    // Validate expiry days
    const expiryDays = body.expiryDays || defaultExpiryDays;
    if (expiryDays < 1 || expiryDays > maxExpiryDays) {
      throw createError({
        statusCode: 400,
        message: `Token expiry must be between 1 and ${maxExpiryDays} days`,
      });
    }

    // Generate token and hash
    const { token, hash } = generateToken();

    // Calculate expiry date
    const now = new Date();
    const expiresAt = new Date(
      now.getTime() + expiryDays * 24 * 60 * 60 * 1000,
    );

    // Save to database
    const tokenId = crypto.randomUUID();
    await db.insert(apiTokens).values({
      id: tokenId,
      userId,
      name: body.name.trim(),
      tokenHash: hash,
      totalQueries: 0,
      lastUsedAt: null,
      expiresAt,
      createdAt: now,
      revokedAt: null,
    });

    log.info(
      {
        userId,
        tokenId,
        name: body.name,
        expiryDays,
      },
      "API token created",
    );

    // Return token (ONLY TIME user will see it)
    return {
      success: true,
      token,
      id: tokenId,
      name: body.name.trim(),
      expiresAt: expiresAt.toISOString(),
      warning: "Save this token now - you won't be able to see it again",
    };
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to create API token",
    );

    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }

    throw createError({
      statusCode: 500,
      message: "Failed to create API token",
    });
  }
});
