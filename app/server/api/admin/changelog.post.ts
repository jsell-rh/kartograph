/**
 * POST /api/admin/changelog
 *
 * Creates a new operational changelog entry.
 * Requires admin access.
 */

import { changelogEntries } from "~/server/db/schema";
import type { ChangelogEntryMetadata } from "~/server/db/schema";
import { db } from "~/server/db/client";
import { requireAdmin } from "~/server/utils/admin";

export default defineEventHandler(async (event) => {
  // Require admin access (returns the user object)
  const user = await requireAdmin(event);

  // Parse and validate request body
  const body = await readBody(event);

  const {
    type,
    title,
    description,
    metadata,
    pinned = false,
    visibility = "public",
    timestamp,
  } = body;

  // Validation
  if (!title || typeof title !== "string" || title.length > 255) {
    throw createError({
      statusCode: 400,
      message: "Title is required and must be less than 255 characters",
    });
  }

  if (
    !type ||
    !["code", "data", "maintenance", "config", "system"].includes(type)
  ) {
    throw createError({
      statusCode: 400,
      message:
        "Type is required and must be one of: code, data, maintenance, config, system",
    });
  }

  if (visibility && !["public", "admin"].includes(visibility)) {
    throw createError({
      statusCode: 400,
      message: "Visibility must be either 'public' or 'admin'",
    });
  }

  // Create entry
  const [entry] = await db
    .insert(changelogEntries)
    .values({
      id: crypto.randomUUID(),
      type,
      title,
      description: description || null,
      timestamp: timestamp ? new Date(timestamp) : new Date(),
      authorId: user?.id || null,
      authorName: user?.name || "System",
      metadata: (metadata as ChangelogEntryMetadata) || null,
      pinned: Boolean(pinned),
      visibility,
      createdAt: new Date(),
      updatedAt: new Date(),
    })
    .returning();

  return entry;
});
