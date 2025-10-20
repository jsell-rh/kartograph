/**
 * DELETE /api/admin/changelog/[id]
 *
 * Deletes a changelog entry.
 * Requires admin access.
 */

import { eq } from "drizzle-orm";
import { changelogEntries } from "~/server/db/schema";
import { db } from "~/server/db/client";
import { requireAdmin } from "~/server/utils/admin";

export default defineEventHandler(async (event) => {
  // Require admin access
  await requireAdmin(event);

  const id = getRouterParam(event, "id");
  if (!id) {
    throw createError({
      statusCode: 400,
      message: "Entry ID is required",
    });
  }

  // Check if entry exists
  const existing = await db.query.changelogEntries.findFirst({
    where: eq(changelogEntries.id, id),
  });

  if (!existing) {
    throw createError({
      statusCode: 404,
      message: "Changelog entry not found",
    });
  }

  // Delete entry
  await db.delete(changelogEntries).where(eq(changelogEntries.id, id));

  return {
    success: true,
    message: "Changelog entry deleted",
  };
});
