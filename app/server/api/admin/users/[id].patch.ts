/**
 * PATCH /api/admin/users/[id]
 *
 * Updates user account (enable/disable, change role).
 * Requires admin access.
 */

import { eq } from "drizzle-orm";
import { users, sessions } from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  const admin = await requireAdmin(event);
  const userId = getRouterParam(event, "id");
  const body = await readBody(event);

  if (!userId) {
    throw createError({ statusCode: 400, message: "User ID required" });
  }

  // Get target user
  const targetUser = await db.query.users.findFirst({
    where: eq(users.id, userId),
  });

  if (!targetUser) {
    throw createError({ statusCode: 404, message: "User not found" });
  }

  // Prevent self-disable
  if (body.isActive === false && admin.id === userId) {
    throw createError({
      statusCode: 400,
      message: "Cannot disable your own account",
    });
  }

  // Prepare update
  const updates: any = {
    updatedAt: new Date(),
  };

  let action = "";
  const metadata: any = {
    before: {},
    after: {},
  };

  // Handle isActive change
  if (body.isActive !== undefined && body.isActive !== targetUser.isActive) {
    updates.isActive = body.isActive;

    if (body.isActive === false) {
      updates.disabledAt = new Date();
      updates.disabledBy = admin.id;
      action = "user_disabled";
    } else {
      updates.disabledAt = null;
      updates.disabledBy = null;
      action = "user_enabled";
    }

    metadata.before.isActive = targetUser.isActive;
    metadata.after.isActive = body.isActive;
  }

  // Handle role change
  if (body.role !== undefined && body.role !== targetUser.role) {
    // Prevent self-demotion
    if (body.role === "user" && admin.id === userId) {
      throw createError({
        statusCode: 400,
        message: "Cannot demote your own account",
      });
    }

    updates.role = body.role;
    action = action || "role_changed";
    metadata.before.role = targetUser.role;
    metadata.after.role = body.role;
  }

  if (Object.keys(updates).length === 1) {
    // Only updatedAt changed, no actual updates
    return { success: true, user: targetUser };
  }

  // Update user
  await db.update(users).set(updates).where(eq(users.id, userId));

  // Log admin action
  await logAdminAction(admin.id, action, userId, metadata, event);

  // If user was disabled, terminate all their sessions
  if (updates.isActive === false) {
    await db.delete(sessions).where(eq(sessions.userId, userId));
  }

  // Fetch updated user
  const updatedUser = await db.query.users.findFirst({
    where: eq(users.id, userId),
  });

  return {
    success: true,
    user: updatedUser,
  };
});
