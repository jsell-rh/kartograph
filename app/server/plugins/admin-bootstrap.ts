/**
 * Admin Bootstrap Plugin
 *
 * Promotes users to admin role based on ADMIN_EMAILS environment variable.
 * Runs on server startup to ensure configured admin emails are promoted.
 *
 * Environment variable format: ADMIN_EMAILS=email1@domain.com,email2@domain.com
 */

import { eq } from "drizzle-orm";
import { db } from "../db/client";
import { users } from "../db/schema";
import { createLogger } from "../lib/logger";

export default defineNitroPlugin(async () => {
  const log = createLogger("admin-bootstrap");

  // Check for admin emails in environment
  const adminEmailsEnv =
    process.env.ADMIN_EMAILS || process.env.NUXT_ADMIN_EMAILS;

  if (!adminEmailsEnv) {
    log.info("No ADMIN_EMAILS configured - skipping admin bootstrap");
    return;
  }

  // Parse email list
  const adminEmails = adminEmailsEnv
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter((e) => e.length > 0);

  if (adminEmails.length === 0) {
    log.info("ADMIN_EMAILS empty - skipping admin bootstrap");
    return;
  }

  log.info({ count: adminEmails.length }, "Bootstrapping admin users");

  // Process each admin email
  for (const email of adminEmails) {
    try {
      const user = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (user && user.role !== "admin") {
        await db
          .update(users)
          .set({ role: "admin", updatedAt: new Date() })
          .where(eq(users.id, user.id));

        log.info({ email, userId: user.id }, "Promoted user to admin");
      } else if (user) {
        log.debug({ email }, "User already admin");
      } else {
        log.warn({ email }, "Admin email not found - user must sign up first");
      }
    } catch (error) {
      log.error({ email, error }, "Failed to process admin email");
    }
  }

  log.info("Admin bootstrap complete");
});
