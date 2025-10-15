/**
 * Database schema for Kartograph application
 *
 * Using Drizzle ORM with SQLite for local development
 * and easy deployment without external database dependencies.
 */

import { sqliteTable, text, integer, index } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

/**
 * Users table - managed by Better Auth
 */
export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  emailVerified: integer("email_verified", { mode: "boolean" })
    .notNull()
    .default(false),
  name: text("name").notNull(),
  image: text("image"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * Sessions table - managed by Better Auth
 */
export const sessions = sqliteTable("sessions", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  expiresAt: integer("expires_at", { mode: "timestamp" }).notNull(),
  token: text("token").notNull().unique(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * Accounts table - for OAuth providers (Better Auth managed)
 */
export const accounts = sqliteTable("accounts", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  accountId: text("account_id").notNull(),
  providerId: text("provider_id").notNull(),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  expiresAt: integer("expires_at", { mode: "timestamp" }),
  scope: text("scope"),
  password: text("password"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * Verifications table - for email verification tokens (Better Auth managed)
 */
export const verifications = sqliteTable("verifications", {
  id: text("id").primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: integer("expires_at", { mode: "timestamp" }).notNull(),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * Conversations table - chat sessions with the agent
 */
export const conversations = sqliteTable("conversations", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  lastMessageAt: integer("last_message_at", { mode: "timestamp" }),
  messageCount: integer("message_count").notNull().default(0),
  isArchived: integer("is_archived", { mode: "boolean" })
    .notNull()
    .default(false),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * ThinkingStep type for message metadata
 */
export interface ThinkingStep {
  type: "thinking" | "tool_call" | "retry";
  content: string;
  metadata?: {
    toolName?: string;
    description?: string;
    timing?: number;
    error?: string;
  };
}

/**
 * Messages table - individual messages within conversations
 */
export const messages = sqliteTable("messages", {
  id: text("id").primaryKey(),
  conversationId: text("conversation_id")
    .notNull()
    .references(() => conversations.id, { onDelete: "cascade" }),
  role: text("role", { enum: ["user", "assistant"] }).notNull(),
  content: text("content").notNull(),
  thinkingSteps: text("thinking_steps", { mode: "json" }).$type<
    ThinkingStep[]
  >(),
  entities: text("entities", { mode: "json" }).$type<
    {
      urn: string;
      type: string;
      id: string;
      displayName: string;
    }[]
  >(),
  elapsedSeconds: integer("elapsed_seconds"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

/**
 * API Tokens table - long-lived tokens for MCP server access
 *
 * Tokens are used to authenticate remote agents/clients accessing
 * the Dgraph query tool via MCP protocol.
 */
export const apiTokens = sqliteTable("api_tokens", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  tokenHash: text("token_hash").notNull().unique(),
  totalQueries: integer("total_queries").notNull().default(0),
  lastUsedAt: integer("last_used_at", { mode: "timestamp" }),
  expiresAt: integer("expires_at", { mode: "timestamp" }).notNull(),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  revokedAt: integer("revoked_at", { mode: "timestamp" }),
});

/**
 * Query Audit Log table - tracks all queries executed via API tokens
 *
 * Used for security monitoring, usage analytics, and debugging.
 * Retention is configurable via AUDIT_LOG_RETENTION_DAYS environment variable.
 */
export const queryAuditLog = sqliteTable(
  "query_audit_log",
  {
    id: text("id").primaryKey(),
    tokenId: text("token_id")
      .notNull()
      .references(() => apiTokens.id, { onDelete: "cascade" }),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    query: text("query").notNull(),
    executionTimeMs: integer("execution_time_ms").notNull(),
    success: integer("success", { mode: "boolean" }).notNull(),
    errorMessage: text("error_message"),
    timestamp: integer("timestamp", { mode: "timestamp" })
      .notNull()
      .default(sql`(unixepoch())`),
  },
  (table) => ({
    tokenIdIdx: index("query_audit_log_token_id_idx").on(table.tokenId),
    timestampIdx: index("query_audit_log_timestamp_idx").on(table.timestamp),
  }),
);
