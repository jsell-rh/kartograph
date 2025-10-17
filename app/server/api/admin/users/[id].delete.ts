/**
 * DELETE /api/admin/users/[id]
 *
 * Hard deletes a user account (permanent).
 * Requires admin access and explicit confirmation.
 */

import { eq } from "drizzle-orm";
import { users } from "~/server/db/schema";
import { db } from "~/server/db/client";

export default defineEventHandler(async (event) => {
  const admin = await requireAdmin(event);
  const userId = getRouterParam(event, "id");
  const query = getQuery(event);

  if (!userId) {
    throw createError({ statusCode: 400, message: "User ID required" });
  }

  // Require confirmation
  if (query.confirm !== "true") {
    throw createError({
      statusCode: 400,
      message: "Deletion must be confirmed with ?confirm=true",
    });
  }

  // Prevent self-deletion
  if (admin.id === userId) {
    throw createError({
      statusCode: 400,
      message: "Cannot delete your own account",
    });
  }

  // Get user for audit log
  const targetUser = await db.query.users.findFirst({
    where: eq(users.id, userId),
  });

  if (!targetUser) {
    throw createError({ statusCode: 404, message: "User not found" });
  }

  // Log before deletion (user will be cascade deleted, so targetUserId will be null after)
  await logAdminAction(
    admin.id,
    "user_deleted",
    userId,
    {
      email: targetUser.email,
      name: targetUser.name,
      role: targetUser.role,
    },
    event,
  );

  // Delete user (cascade will handle related records)
  await db.delete(users).where(eq(users.id, userId));

  return {
    success: true,
    deletedUserId: userId,
  };
});
