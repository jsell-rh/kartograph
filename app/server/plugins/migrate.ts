/**
 * Auto-apply database migrations on server startup
 */

import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { db } from "../db/client";
import { createLogger } from "../lib/logger";
import path from "path";

const log = createLogger("db-migrate");

export default defineNitroPlugin(async () => {
  try {
    const dbPath = process.env.DATABASE_URL || "./server/data.db";
    log.info({ dbPath }, "Running database migrations...");

    // Run migrations from the migrations folder
    // In production (.output), migrations are at ./server/db/migrations
    // In development, they're at ./server/db/migrations
    const migrationsFolder = path.join(
      process.cwd(),
      "server",
      "db",
      "migrations",
    );

    migrate(db, { migrationsFolder });

    log.info("Database migrations completed successfully");
  } catch (error) {
    log.error(
      { error: error instanceof Error ? error.message : String(error) },
      "Failed to run database migrations",
    );

    // This is critical - if migrations fail, the app may not work correctly
    throw error;
  }
});
