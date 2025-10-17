/**
 * Admin Authorization Utilities
 *
 * Provides functions for:
 * - Checking admin role
 * - Checking user active status
 * - Logging admin actions to audit log
 */

import { type H3Event } from "h3";
import { eq } from "drizzle-orm";
import { db } from "../db/client";
import { users, sessions, adminAuditLog } from "../db/schema";
import { auth } from "../lib/auth";
import { createLogger } from "../lib/logger";

const log = createLogger("admin-auth");

/**
 * Check if current user is an admin
 * @throws 401 if not authenticated
 * @throws 403 if not admin
 */
export async function requireAdmin(event: H3Event) {
  const session = await auth.api.getSession({ headers: event.headers });

  if (!session?.user) {
    log.warn({ path: event.path }, "Unauthenticated admin access attempt");
    throw createError({
      statusCode: 401,
      message: "Authentication required",
    });
  }

  const user = await db.query.users.findFirst({
    where: eq(users.id, session.user.id),
  });

  if (!user) {
    log.error(
      { userId: session.user.id },
      "Session user not found in database",
    );
    throw createError({
      statusCode: 401,
      message: "Invalid session",
    });
  }

  if (user.role !== "admin") {
    log.warn(
      { userId: user.id, email: user.email, path: event.path },
      "Non-admin user attempted admin access",
    );
    throw createError({
      statusCode: 403,
      message: "Admin access required",
    });
  }

  return user;
}

/**
 * Check if current user is active (not disabled)
 * @throws 403 if user is disabled
 */
export async function requireActiveUser(event: H3Event) {
  const session = await auth.api.getSession({ headers: event.headers });

  if (!session?.user) {
    return; // Not authenticated, let other middleware handle
  }

  const user = await db.query.users.findFirst({
    where: eq(users.id, session.user.id),
    columns: {
      id: true,
      email: true,
      isActive: true,
      disabledAt: true,
    },
  });

  if (!user) {
    return; // Session invalid, let other middleware handle
  }

  if (!user.isActive) {
    log.warn(
      { userId: user.id, email: user.email, disabledAt: user.disabledAt },
      "Disabled user attempted access",
    );

    // Clear all sessions for this user
    await db.delete(sessions).where(eq(sessions.userId, user.id));

    throw createError({
      statusCode: 403,
      message:
        "Your account has been disabled. Please contact an administrator.",
    });
  }
}

/**
 * Log admin action to audit log
 */
export async function logAdminAction(
  adminUserId: string,
  action: string,
  targetUserId?: string,
  metadata?: any,
  event?: H3Event,
) {
  const auditLog = createLogger("admin-audit");

  const ipAddress = event ? getRequestIP(event) : null;
  const userAgent = event ? getHeader(event, "user-agent") : null;

  await db.insert(adminAuditLog).values({
    id: crypto.randomUUID(),
    adminUserId,
    targetUserId: targetUserId || null,
    action,
    metadata: metadata ? JSON.stringify(metadata) : null,
    ipAddress,
    userAgent,
    timestamp: new Date(),
  });

  auditLog.info(
    {
      adminUserId,
      targetUserId,
      action,
      metadata,
    },
    "Admin action logged",
  );
}
