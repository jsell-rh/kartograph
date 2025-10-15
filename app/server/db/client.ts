/**
 * Database client using better-sqlite3 and Drizzle ORM
 */

import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";
import path from "path";

// Use /data volume in production (mounted PVC), or local path in dev
// Set DATABASE_URL to "/data/kartograph.db" in production
const DB_PATH =
  process.env.DATABASE_URL || path.join(process.cwd(), "server", "data.db");

const sqlite = new Database(DB_PATH);

// Enable foreign keys
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });
