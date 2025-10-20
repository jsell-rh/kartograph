/**
 * PATCH /api/admin/changelog/[id]
 *
 * Updates an existing changelog entry.
 * Requires admin access.
 */

import { eq } from "drizzle-orm";
import { changelogEntries } from "~/server/db/schema";
import type { ChangelogEntryMetadata } from "~/server/db/schema";
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

  // Parse and validate request body
  const body = await readBody(event);

  const updateData: any = {
    updatedAt: new Date(),
  };

  // Update only provided fields
  if (body.title !== undefined) {
    if (!body.title || body.title.length > 255) {
      throw createError({
        statusCode: 400,
        message: "Title must be between 1 and 255 characters",
      });
    }
    updateData.title = body.title;
  }

  if (body.description !== undefined) {
    updateData.description = body.description || null;
  }

  if (body.type !== undefined) {
    if (!["code", "data", "maintenance", "config", "system"].includes(body.type)) {
      throw createError({
        statusCode: 400,
        message:
          "Type must be one of: code, data, maintenance, config, system",
      });
    }
    updateData.type = body.type;
  }

  if (body.metadata !== undefined) {
    updateData.metadata = (body.metadata as ChangelogEntryMetadata) || null;
  }

  if (body.pinned !== undefined) {
    updateData.pinned = Boolean(body.pinned);
  }

  if (body.visibility !== undefined) {
    if (!["public", "admin"].includes(body.visibility)) {
      throw createError({
        statusCode: 400,
        message: "Visibility must be either 'public' or 'admin'",
      });
    }
    updateData.visibility = body.visibility;
  }

  if (body.timestamp !== undefined) {
    updateData.timestamp = new Date(body.timestamp);
  }

  // Update entry
  const [updatedEntry] = await db
    .update(changelogEntries)
    .set(updateData)
    .where(eq(changelogEntries.id, id))
    .returning();

  return updatedEntry;
});
