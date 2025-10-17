# Admin User Management - Implementation Plan

**Date**: 2025-10-17
**Version**: 1.0
**Status**: Planning

---

## Executive Summary

This document outlines the architecture and implementation plan for adding admin-level user management to Kartograph. The feature enables designated administrators to view user accounts, monitor activity, disable/enable accounts, and manage the user base. Admin access is bootstrapped via environment variables and enforced through role-based authorization checks on every API request.

**Key Requirements:**

- Admin role assignment via environment variable (`ADMIN_EMAILS`)
- User listing with activity statistics (conversations, messages, API tokens)
- Account status management (soft disable and hard delete)
- Immediate session invalidation for disabled users (checked on each request)
- Message feedback system (thumbs up/down with optional text feedback)
- Privacy-preserving access: admins see conversation content ONLY when users submit feedback
- Feedback stats integration (helpful vs unhelpful percentages)
- API token usage tracking per user

---

## Phase 1: Database Schema Extensions

### 1.1 Users Table Modifications

**New Fields:**

```typescript
// server/db/schema.ts

export const users = sqliteTable("users", {
  // ... existing fields ...
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  name: text("name").notNull(),
  emailVerified: integer("email_verified", { mode: "boolean" })
    .notNull()
    .default(false),
  image: text("image"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),

  // NEW FIELDS
  role: text("role", { enum: ["user", "admin"] })
    .notNull()
    .default("user"),
  isActive: integer("is_active", { mode: "boolean" })
    .notNull()
    .default(true),
  lastLoginAt: integer("last_login_at", { mode: "timestamp" }),
  disabledAt: integer("disabled_at", { mode: "timestamp" }),
  disabledBy: text("disabled_by"), // Admin user ID who disabled this account
});
```

**Migration Strategy:**

- Create migration file: `0005_add_admin_features.sql`
- Add new columns with defaults (all existing users become "user" role, active)
- Backfill `lastLoginAt` from sessions table if possible
- Run migration on startup via Drizzle

### 1.2 Admin Audit Log Table

**Purpose:** Track all admin actions for security and compliance

```typescript
export const adminAuditLog = sqliteTable(
  "admin_audit_log",
  {
    id: text("id")
      .primaryKey()
      .$defaultFn(() => crypto.randomUUID()),
    adminUserId: text("admin_user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    targetUserId: text("target_user_id")
      .references(() => users.id, { onDelete: "set null" }),
    action: text("action").notNull(), // 'user_disabled', 'user_enabled', 'user_deleted', 'role_changed'
    metadata: text("metadata", { mode: "json" }), // Additional context
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    timestamp: integer("timestamp", { mode: "timestamp" })
      .notNull()
      .default(sql`(unixepoch())`),
  },
  (table) => ({
    adminUserIdx: index("admin_audit_log_admin_user_idx").on(table.adminUserId),
    targetUserIdx: index("admin_audit_log_target_user_idx").on(table.targetUserId),
    timestampIdx: index("admin_audit_log_timestamp_idx").on(table.timestamp),
  })
);
```

---

## Phase 2: Authorization System

### 2.1 Admin Bootstrap

**Environment Variable:**

```bash
# .env
ADMIN_EMAILS=jsell@redhat.com,admin2@redhat.com
```

**Server Plugin:** `server/plugins/admin-bootstrap.ts`

```typescript
export default defineNitroPlugin(async () => {
  const log = createLogger("admin-bootstrap");

  const adminEmailsEnv = process.env.ADMIN_EMAILS || process.env.NUXT_ADMIN_EMAILS;
  if (!adminEmailsEnv) {
    log.info("No ADMIN_EMAILS configured - skipping admin bootstrap");
    return;
  }

  const adminEmails = adminEmailsEnv.split(",").map(e => e.trim().toLowerCase());

  if (adminEmails.length === 0) {
    return;
  }

  log.info({ count: adminEmails.length }, "Bootstrapping admin users");

  for (const email of adminEmails) {
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
  }
});
```

### 2.2 Authorization Utilities

**File:** `server/utils/admin.ts`

```typescript
import { H3Event } from "h3";
import { db } from "../db/client";
import { users } from "../db/schema";
import { eq } from "drizzle-orm";
import { getSession } from "./auth";
import { createLogger } from "../lib/logger";

const log = createLogger("admin-auth");

/**
 * Check if current user is an admin
 * @throws 401 if not authenticated
 * @throws 403 if not admin
 */
export async function requireAdmin(event: H3Event) {
  const session = await getSession(event);

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
    log.error({ userId: session.user.id }, "Session user not found in database");
    throw createError({
      statusCode: 401,
      message: "Invalid session",
    });
  }

  if (user.role !== "admin") {
    log.warn({ userId: user.id, email: user.email, path: event.path }, "Non-admin user attempted admin access");
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
  const session = await getSession(event);

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
    log.warn({ userId: user.id, email: user.email, disabledAt: user.disabledAt }, "Disabled user attempted access");

    // Clear session
    await clearSession(event);

    throw createError({
      statusCode: 403,
      message: "Account has been disabled. Please contact an administrator.",
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
  event?: H3Event
) {
  const log = createLogger("admin-audit");

  const ipAddress = event ? getRequestIP(event) : null;
  const userAgent = event ? getHeader(event, "user-agent") : null;

  await db.insert(adminAuditLog).values({
    id: crypto.randomUUID(),
    adminUserId,
    targetUserId,
    action,
    metadata: metadata ? JSON.stringify(metadata) : null,
    ipAddress,
    userAgent,
    timestamp: new Date(),
  });

  log.info({
    adminUserId,
    targetUserId,
    action,
    metadata,
  }, "Admin action logged");
}
```

### 2.3 Global Middleware for User Status Check

**File:** `server/middleware/check-user-status.ts`

```typescript
export default defineEventHandler(async (event) => {
  // Skip auth routes and public endpoints
  const path = event.path;
  if (
    path.startsWith("/api/auth") ||
    path.startsWith("/api/health") ||
    path.startsWith("/_nuxt") ||
    path === "/favicon.ico"
  ) {
    return;
  }

  // Check if user is active (will throw 403 if disabled)
  await requireActiveUser(event);
});
```

### 2.4 Session Update for Last Login

**Modify:** `server/utils/auth.ts`

Add hook to update `lastLoginAt` on session creation:

```typescript
// In Better Auth configuration
{
  hooks: {
    after: createAuthMiddleware(async (ctx) => {
      // ... existing hooks ...

      // Update lastLoginAt on successful login
      if (ctx.path === "/sign-in/email" || ctx.path.startsWith("/callback/")) {
        const session = (ctx.context as any)?.newSession || (ctx.context as any)?.session;

        if (session?.user?.id) {
          await db
            .update(users)
            .set({ lastLoginAt: new Date() })
            .where(eq(users.id, session.user.id));
        }
      }
    }),
  },
}
```

---

## Phase 3: Admin API Endpoints

### 3.1 User Management APIs

#### GET /api/admin/users

**Purpose:** List all users with activity statistics

**Query Parameters:**

- `?limit=50` - Pagination limit (default: 50, max: 200)
- `?offset=0` - Pagination offset
- `?status=all` - Filter: 'all', 'active', 'disabled'
- `?role=all` - Filter: 'all', 'user', 'admin'
- `?search=` - Search by name or email
- `?sortBy=createdAt` - Sort field: 'createdAt', 'lastLoginAt', 'email', 'conversations'
- `?sortOrder=desc` - Sort order: 'asc', 'desc'

**Response:**

```typescript
{
  users: [
    {
      id: string
      email: string
      name: string
      role: "user" | "admin"
      isActive: boolean
      emailVerified: boolean
      image: string | null
      createdAt: Date
      updatedAt: Date
      lastLoginAt: Date | null
      disabledAt: Date | null
      disabledBy: string | null

      // Activity stats
      stats: {
        conversationCount: number
        messageCount: number
        apiTokenCount: number
        activeApiTokenCount: number
        totalApiCalls: number
        lastQueryAt: Date | null

        // Feedback stats
        feedbackCount: number
        helpfulCount: number
        unhelpfulCount: number
        helpfulPercentage: number
      }
    }
  ],
  total: number
  hasMore: boolean
}
```

**Implementation:** `server/api/admin/users.get.ts`

```typescript
export default defineEventHandler(async (event) => {
  // Require admin access
  await requireAdmin(event);

  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const status = (query.status as string) || "all";
  const role = (query.role as string) || "all";
  const search = (query.search as string) || "";
  const sortBy = (query.sortBy as string) || "createdAt";
  const sortOrder = (query.sortOrder as string) || "desc";

  // Build where conditions
  const conditions = [];

  if (status === "active") {
    conditions.push(eq(users.isActive, true));
  } else if (status === "disabled") {
    conditions.push(eq(users.isActive, false));
  }

  if (role !== "all") {
    conditions.push(eq(users.role, role));
  }

  if (search) {
    conditions.push(
      or(
        like(users.email, `%${search}%`),
        like(users.name, `%${search}%`)
      )
    );
  }

  // Fetch users with stats
  const allUsers = await db
    .select({
      user: users,
      conversationCount: count(conversations.id),
      messageCount: count(messages.id),
      apiTokenCount: count(apiTokens.id),
      activeApiTokenCount: count(
        sql`CASE WHEN ${apiTokens.revokedAt} IS NULL THEN 1 END`
      ),
    })
    .from(users)
    .leftJoin(conversations, eq(conversations.userId, users.id))
    .leftJoin(messages, eq(messages.conversationId, conversations.id))
    .leftJoin(apiTokens, eq(apiTokens.userId, users.id))
    .where(and(...conditions))
    .groupBy(users.id)
    .orderBy(
      sortOrder === "desc"
        ? desc(users[sortBy])
        : asc(users[sortBy])
    );

  // Paginate
  const paginatedUsers = allUsers.slice(offset, offset + limit);

  // Get API usage stats for these users
  const userIds = paginatedUsers.map(u => u.user.id);
  const apiUsageStats = await db
    .select({
      userId: queryAuditLog.userId,
      totalApiCalls: count(queryAuditLog.id),
      lastQueryAt: max(queryAuditLog.timestamp),
    })
    .from(queryAuditLog)
    .where(inArray(queryAuditLog.userId, userIds))
    .groupBy(queryAuditLog.userId);

  const apiUsageMap = new Map(
    apiUsageStats.map(stat => [stat.userId, stat])
  );

  // Combine data
  const result = paginatedUsers.map(row => ({
    ...row.user,
    stats: {
      conversationCount: row.conversationCount,
      messageCount: row.messageCount,
      apiTokenCount: row.apiTokenCount,
      activeApiTokenCount: row.activeApiTokenCount,
      totalApiCalls: apiUsageMap.get(row.user.id)?.totalApiCalls || 0,
      lastQueryAt: apiUsageMap.get(row.user.id)?.lastQueryAt || null,
    },
  }));

  return {
    users: result,
    total: allUsers.length,
    hasMore: offset + limit < allUsers.length,
  };
});
```

#### PATCH /api/admin/users/[id]

**Purpose:** Update user account (enable/disable, change role)

**Body:**

```typescript
{
  isActive?: boolean
  role?: "user" | "admin"
}
```

**Response:**

```typescript
{
  success: boolean
  user: User
}
```

**Implementation:** `server/api/admin/users/[id].patch.ts`

```typescript
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
  await db
    .update(users)
    .set(updates)
    .where(eq(users.id, userId));

  // Log admin action
  await logAdminAction(admin.id, action, userId, metadata, event);

  // If user was disabled, terminate all their sessions
  if (updates.isActive === false) {
    await db
      .delete(sessions)
      .where(eq(sessions.userId, userId));
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
```

#### DELETE /api/admin/users/[id]

**Purpose:** Hard delete user account (permanent)

**Query Parameters:**

- `?confirm=true` - Required confirmation

**Response:**

```typescript
{
  success: boolean
  deletedUserId: string
}
```

**Implementation:** `server/api/admin/users/[id].delete.ts`

```typescript
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

  // Log before deletion
  await logAdminAction(
    admin.id,
    "user_deleted",
    userId,
    {
      email: targetUser.email,
      name: targetUser.name,
      role: targetUser.role,
    },
    event
  );

  // Delete user (cascade will handle related records)
  await db.delete(users).where(eq(users.id, userId));

  return {
    success: true,
    deletedUserId: userId,
  };
});
```

#### GET /api/admin/stats

**Purpose:** Dashboard statistics for admin overview

**Response:**

```typescript
{
  totalUsers: number
  activeUsers: number
  disabledUsers: number
  adminUsers: number
  totalConversations: number
  totalMessages: number
  totalApiTokens: number
  activeApiTokens: number
  totalApiCalls: number
  stats: {
    usersCreatedLast30Days: number
    conversationsLast30Days: number
    messagesLast30Days: number
    apiCallsLast30Days: number
  }
}
```

**Implementation:** `server/api/admin/stats.get.ts`

---

## Phase 4: Admin UI

### 4.1 Admin Route Protection

**Middleware:** `middleware/admin.ts`

```typescript
export default defineNuxtRouteMiddleware(async (to, from) => {
  // Only protect /admin routes
  if (!to.path.startsWith('/admin')) {
    return;
  }

  const authStore = useAuthStore();

  // Ensure user is loaded
  if (!authStore.user) {
    await authStore.fetchUser();
  }

  // Check if user is admin
  if (!authStore.user || authStore.user.role !== 'admin') {
    return navigateTo('/');
  }
});
```

### 4.2 Admin Page Structure

**Route:** `/admin`

```
pages/
└── admin/
    └── index.vue (Main admin dashboard)
```

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  Kartograph Admin                                       │
│  ┌─────────────────┬─────────────────┬───────────────┐ │
│  │  Total Users    │  Active Users   │  Conversations│ │
│  │      125        │       118       │     1,457     │ │
│  └─────────────────┴─────────────────┴───────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  User Management                                   │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │ 🔍 Search users...        [Filter ▼] [Sort] │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │                                                    │ │
│  │  Name         Email           Role  Status  Last  │ │
│  │  ────────────────────────────────────────────────│ │
│  │  John Doe     john@...      User   Active  2h    │ │
│  │  Jane Smith   jane@...      Admin  Active  1d    │ │
│  │  Bob Wilson   bob@...       User   Disabled 5d   │ │
│  │  ...                                              │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Components

**File:** `pages/admin/index.vue`

```vue
<template>
  <div class="h-full bg-background flex flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b border-border bg-card px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-foreground">Admin Dashboard</h1>
          <p class="text-sm text-muted-foreground">
            User management and system overview
          </p>
        </div>
        <NuxtLink
          to="/"
          class="px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
        >
          Back to App
        </NuxtLink>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="px-6 py-6 border-b border-border bg-muted/30">
      <AdminStatsCards :stats="dashboardStats" :loading="statsLoading" />
    </div>

    <!-- User Management Table -->
    <div class="flex-1 overflow-auto px-6 py-6">
      <AdminUserTable
        :users="users"
        :loading="usersLoading"
        :total="totalUsers"
        @update-user="handleUpdateUser"
        @delete-user="handleDeleteUser"
        @refresh="fetchUsers"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'admin',
});

// Component implementation...
</script>
```

**Component:** `components/admin/StatsCards.vue`

**Component:** `components/admin/UserTable.vue`

Features:

- Sortable columns
- Filterable (active/disabled, role)
- Search by email/name
- Expandable rows for detailed stats
- Action menu per user (Enable/Disable, Delete)
- Pagination

**Component:** `components/admin/UserActionMenu.vue`

Actions:

- Enable/Disable Account
- Change Role (User ↔ Admin)
- Hard Delete (with confirmation dialog)
- View Audit Log (future)

### 4.4 Admin Menu Item

**Modify:** `pages/index.vue` user menu

Add admin menu item (visible only to admins):

```vue
<NuxtLink
  v-if="authStore.user?.role === 'admin'"
  to="/admin"
  class="w-full px-4 py-2 text-left text-sm hover:bg-muted transition-colors flex items-center gap-2"
  @click="showUserMenu = false"
>
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
  Admin Dashboard
</NuxtLink>
```

---

## Phase 5: Message Feedback System

### 5.1 Overview

**Purpose:** Allow users to provide feedback on assistant responses to improve quality

**Privacy Model:**

- No feedback submitted = Admins see ONLY metadata (message count, conversation count, etc.)
- Feedback submitted = Admins can view the specific user query + assistant response + user feedback
- Users control visibility by choosing whether to submit feedback

**User Experience Goals:**

- Seamless, non-intrusive feedback mechanism
- Minimal friction (single click for thumbs up/down)
- Optional detailed feedback for unhelpful responses
- Clear visual confirmation after submission
- Elegant, polished UI that feels natural

### 5.2 Database Schema

See **Phase 1.3** for the `messageFeedback` table schema.

### 5.3 Feedback API Endpoints

#### POST /api/feedback

**Purpose:** Submit user feedback for an assistant message

**Request Body:**

```typescript
{
  messageId: string
  rating: "helpful" | "unhelpful"
  feedbackText?: string  // Optional, typically provided with "unhelpful"
}
```

**Response:**

```typescript
{
  success: boolean
  feedbackId: string
}
```

**Implementation:** `server/api/feedback.post.ts`

```typescript
export default defineEventHandler(async (event) => {
  const session = await getSession(event);

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      message: "Authentication required",
    });
  }

  const body = await readBody(event);
  const { messageId, rating, feedbackText } = body;

  // Validate input
  if (!messageId || !rating) {
    throw createError({
      statusCode: 400,
      message: "messageId and rating are required",
    });
  }

  if (!["helpful", "unhelpful"].includes(rating)) {
    throw createError({
      statusCode: 400,
      message: "rating must be 'helpful' or 'unhelpful'",
    });
  }

  // Get the message and verify ownership
  const message = await db.query.messages.findFirst({
    where: eq(messages.id, messageId),
    with: {
      conversation: true,
    },
  });

  if (!message) {
    throw createError({
      statusCode: 404,
      message: "Message not found",
    });
  }

  if (message.conversation.userId !== session.user.id) {
    throw createError({
      statusCode: 403,
      message: "You can only provide feedback on your own messages",
    });
  }

  // Only allow feedback on assistant messages
  if (message.role !== "assistant") {
    throw createError({
      statusCode: 400,
      message: "Feedback can only be submitted for assistant responses",
    });
  }

  // Get the user's query (previous message in conversation)
  const userMessage = await db.query.messages.findFirst({
    where: and(
      eq(messages.conversationId, message.conversationId),
      eq(messages.role, "user"),
      lt(messages.createdAt, message.createdAt)
    ),
    orderBy: desc(messages.createdAt),
  });

  const userQuery = userMessage?.content || "[No user query found]";

  // Check if feedback already exists for this message
  const existingFeedback = await db.query.messageFeedback.findFirst({
    where: and(
      eq(messageFeedback.messageId, messageId),
      eq(messageFeedback.userId, session.user.id)
    ),
  });

  let feedbackId: string;

  if (existingFeedback) {
    // Update existing feedback
    await db
      .update(messageFeedback)
      .set({
        rating,
        feedbackText: feedbackText || null,
        createdAt: new Date(), // Update timestamp
      })
      .where(eq(messageFeedback.id, existingFeedback.id));

    feedbackId = existingFeedback.id;
  } else {
    // Create new feedback
    feedbackId = crypto.randomUUID();

    await db.insert(messageFeedback).values({
      id: feedbackId,
      messageId,
      conversationId: message.conversationId,
      userId: session.user.id,
      rating,
      feedbackText: feedbackText || null,
      userQuery,
      assistantResponse: message.content,
      createdAt: new Date(),
    });
  }

  return {
    success: true,
    feedbackId,
  };
});
```

#### GET /api/admin/feedback

**Purpose:** View all user feedback (admin only)

**Query Parameters:**

- `?limit=50` - Pagination limit (default: 50, max: 200)
- `?offset=0` - Pagination offset
- `?rating=all` - Filter: 'all', 'helpful', 'unhelpful'
- `?userId=` - Filter by specific user
- `?hasText=false` - Filter: only feedback with written text
- `?sortBy=createdAt` - Sort field: 'createdAt'
- `?sortOrder=desc` - Sort order: 'asc', 'desc'

**Response:**

```typescript
{
  feedback: [
    {
      id: string
      messageId: string
      conversationId: string
      userId: string
      userName: string
      userEmail: string
      rating: "helpful" | "unhelpful"
      feedbackText: string | null
      userQuery: string
      assistantResponse: string
      createdAt: Date
    }
  ],
  total: number
  hasMore: boolean
  stats: {
    totalFeedback: number
    helpfulCount: number
    unhelpfulCount: number
    helpfulPercentage: number
    feedbackWithTextCount: number
  }
}
```

**Implementation:** `server/api/admin/feedback.get.ts`

```typescript
export default defineEventHandler(async (event) => {
  await requireAdmin(event);

  const query = getQuery(event);
  const limit = Math.min(Number(query.limit) || 50, 200);
  const offset = Number(query.offset) || 0;
  const rating = (query.rating as string) || "all";
  const userId = (query.userId as string) || "";
  const hasText = query.hasText === "true";
  const sortOrder = (query.sortOrder as string) || "desc";

  // Build where conditions
  const conditions = [];

  if (rating !== "all") {
    conditions.push(eq(messageFeedback.rating, rating));
  }

  if (userId) {
    conditions.push(eq(messageFeedback.userId, userId));
  }

  if (hasText) {
    conditions.push(isNotNull(messageFeedback.feedbackText));
  }

  // Fetch feedback with user info
  const allFeedback = await db
    .select({
      feedback: messageFeedback,
      user: {
        id: users.id,
        name: users.name,
        email: users.email,
      },
    })
    .from(messageFeedback)
    .leftJoin(users, eq(users.id, messageFeedback.userId))
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .orderBy(
      sortOrder === "desc"
        ? desc(messageFeedback.createdAt)
        : asc(messageFeedback.createdAt)
    );

  // Paginate
  const paginatedFeedback = allFeedback.slice(offset, offset + limit);

  // Calculate stats
  const stats = await db
    .select({
      totalFeedback: count(messageFeedback.id),
      helpfulCount: count(
        sql`CASE WHEN ${messageFeedback.rating} = 'helpful' THEN 1 END`
      ),
      unhelpfulCount: count(
        sql`CASE WHEN ${messageFeedback.rating} = 'unhelpful' THEN 1 END`
      ),
      feedbackWithTextCount: count(
        sql`CASE WHEN ${messageFeedback.feedbackText} IS NOT NULL THEN 1 END`
      ),
    })
    .from(messageFeedback);

  const totalFeedback = stats[0].totalFeedback;
  const helpfulCount = stats[0].helpfulCount;
  const unhelpfulCount = stats[0].unhelpfulCount;
  const helpfulPercentage = totalFeedback > 0
    ? Math.round((helpfulCount / totalFeedback) * 100)
    : 0;

  return {
    feedback: paginatedFeedback.map(row => ({
      ...row.feedback,
      userName: row.user.name,
      userEmail: row.user.email,
    })),
    total: allFeedback.length,
    hasMore: offset + limit < allFeedback.length,
    stats: {
      totalFeedback,
      helpfulCount,
      unhelpfulCount,
      helpfulPercentage,
      feedbackWithTextCount: stats[0].feedbackWithTextCount,
    },
  };
});
```

### 5.4 User-Facing Feedback UI

**Critical UX Requirements:**

- ✨ **Delightful interaction** - smooth animations, satisfying feedback
- 🎯 **Non-intrusive** - doesn't disrupt conversation flow
- ⚡ **Fast** - single click for thumbs up/down, no page reload
- 💬 **Progressive disclosure** - text feedback only appears if needed
- ✅ **Clear confirmation** - visual feedback that submission succeeded

**Component:** `components/MessageFeedback.vue`

**Visual Design:**

```
Initial State (subtle, below message):
┌───────────────────────────────────────┐
│ Assistant Response                    │
│ Here's the information you requested: │
│ ...                                    │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ Was this helpful?              │   │ ← Subtle gray text
│ │   👍 Yes    👎 No              │   │ ← Buttons with hover state
│ └────────────────────────────────┘   │
└───────────────────────────────────────┘

After Thumbs Up (confirmation):
┌───────────────────────────────────────┐
│ ✓ Thanks for your feedback!           │ ← Green checkmark, fades after 2s
│   👍 Yes    👎 No                     │ ← Thumbs up highlighted
└───────────────────────────────────────┘

After Thumbs Down (expanded):
┌───────────────────────────────────────┐
│ 👎 Sorry this wasn't helpful          │ ← Orange/yellow tone
│                                        │
│ Help us improve (optional):           │
│ ┌─────────────────────────────────┐  │
│ │ What went wrong?                │  │ ← Auto-focus textarea
│ │                                  │  │
│ │                                  │  │
│ └─────────────────────────────────┘  │
│                                        │
│ ℹ️ Your message and the assistant's  │ ← Privacy notice (subtle)
│   response will be shared with our    │
│   team to improve the service.        │
│                                        │
│ [Skip] [Submit Feedback]              │ ← Clear actions
└───────────────────────────────────────┘

After Submit (confirmation):
┌───────────────────────────────────────┐
│ ✓ Thank you! We'll use your feedback │ ← Green confirmation
│   to improve our responses.           │
│                                        │
│   👍 Yes    👎 No                     │ ← Thumbs down highlighted
└───────────────────────────────────────┘
```

**Implementation:**

```vue
<template>
  <div class="message-feedback">
    <!-- Feedback confirmation (shown after submission) -->
    <Transition name="fade">
      <div
        v-if="showConfirmation"
        class="feedback-confirmation"
        :class="confirmationClass"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span>{{ confirmationMessage }}</span>
      </div>
    </Transition>

    <!-- Feedback prompt (always visible) -->
    <div class="feedback-prompt">
      <span class="feedback-label">Was this helpful?</span>
      <div class="feedback-buttons">
        <button
          @click="handleFeedback('helpful')"
          class="feedback-button"
          :class="{ active: currentRating === 'helpful', disabled: isSubmitting }"
          :disabled="isSubmitting"
        >
          <span class="feedback-icon">👍</span>
          <span class="feedback-text">Yes</span>
        </button>
        <button
          @click="handleFeedback('unhelpful')"
          class="feedback-button"
          :class="{ active: currentRating === 'unhelpful', disabled: isSubmitting }"
          :disabled="isSubmitting"
        >
          <span class="feedback-icon">👎</span>
          <span class="feedback-text">No</span>
        </button>
      </div>
    </div>

    <!-- Expanded feedback form (shown after thumbs down) -->
    <Transition name="expand">
      <div v-if="showFeedbackForm" class="feedback-form">
        <div class="feedback-form-header">
          <span class="feedback-icon">👎</span>
          <span class="feedback-form-title">Sorry this wasn't helpful</span>
        </div>

        <label class="feedback-form-label">
          Help us improve (optional):
        </label>

        <textarea
          ref="feedbackTextarea"
          v-model="feedbackText"
          class="feedback-textarea"
          placeholder="What went wrong? What would have been more helpful?"
          rows="3"
          maxlength="1000"
          :disabled="isSubmitting"
        />

        <!-- Privacy notice -->
        <div class="feedback-privacy-notice">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs text-muted-foreground">
            Your message and the assistant's response will be shared with our team to improve the service.
          </span>
        </div>

        <div class="feedback-form-actions">
          <button
            @click="skipFeedback"
            class="feedback-action-button secondary"
            :disabled="isSubmitting"
          >
            Skip
          </button>
          <button
            @click="submitFeedback"
            class="feedback-action-button primary"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting" class="spinner"></span>
            <span v-else>Submit Feedback</span>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
interface Props {
  messageId: string
}

const props = defineProps<Props>();

const currentRating = ref<'helpful' | 'unhelpful' | null>(null);
const showFeedbackForm = ref(false);
const feedbackText = ref('');
const isSubmitting = ref(false);
const showConfirmation = ref(false);
const confirmationMessage = ref('');
const confirmationClass = ref('');
const feedbackTextarea = ref<HTMLTextAreaElement | null>(null);

async function handleFeedback(rating: 'helpful' | 'unhelpful') {
  currentRating.value = rating;

  if (rating === 'helpful') {
    // Submit immediately for thumbs up
    await submitFeedbackToServer(rating);
  } else {
    // Show feedback form for thumbs down
    showFeedbackForm.value = true;

    // Auto-focus textarea
    await nextTick();
    feedbackTextarea.value?.focus();
  }
}

function skipFeedback() {
  // Submit thumbs down without text
  submitFeedbackToServer('unhelpful');
}

async function submitFeedback() {
  await submitFeedbackToServer('unhelpful', feedbackText.value);
}

async function submitFeedbackToServer(rating: 'helpful' | 'unhelpful', text?: string) {
  isSubmitting.value = true;

  try {
    await $fetch('/api/feedback', {
      method: 'POST',
      body: {
        messageId: props.messageId,
        rating,
        feedbackText: text || null,
      },
    });

    // Show confirmation
    confirmationMessage.value = rating === 'helpful'
      ? 'Thanks for your feedback!'
      : "Thank you! We'll use your feedback to improve our responses.";
    confirmationClass.value = 'success';
    showConfirmation.value = true;

    // Hide feedback form
    showFeedbackForm.value = false;

    // Hide confirmation after 3 seconds
    setTimeout(() => {
      showConfirmation.value = false;
    }, 3000);

  } catch (error) {
    console.error('Failed to submit feedback:', error);

    confirmationMessage.value = 'Failed to submit feedback. Please try again.';
    confirmationClass.value = 'error';
    showConfirmation.value = true;

    setTimeout(() => {
      showConfirmation.value = false;
    }, 3000);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.message-feedback {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.feedback-confirmation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.feedback-confirmation.success {
  background-color: rgb(220 252 231 / 0.5);
  color: rgb(22 163 74);
  border: 1px solid rgb(134 239 172 / 0.5);
}

.feedback-confirmation.error {
  background-color: rgb(254 226 226 / 0.5);
  color: rgb(220 38 38);
  border: 1px solid rgb(252 165 165 / 0.5);
}

.feedback-prompt {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.feedback-label {
  font-size: 0.875rem;
  color: var(--muted-foreground);
  font-weight: 500;
}

.feedback-buttons {
  display: flex;
  gap: 0.5rem;
}

.feedback-button {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  background-color: var(--background);
  color: var(--muted-foreground);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.feedback-button:hover:not(.disabled) {
  background-color: var(--muted);
  border-color: var(--primary);
  color: var(--foreground);
}

.feedback-button.active {
  background-color: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.feedback-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-icon {
  font-size: 1rem;
  line-height: 1;
}

.feedback-text {
  font-weight: 500;
}

.feedback-form {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: var(--muted);
  border: 1px solid var(--border);
}

.feedback-form-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.feedback-form-title {
  font-weight: 500;
  color: var(--foreground);
}

.feedback-form-label {
  display: block;
  font-size: 0.875rem;
  color: var(--muted-foreground);
  margin-bottom: 0.5rem;
}

.feedback-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  background-color: var(--background);
  color: var(--foreground);
  font-size: 0.875rem;
  resize: vertical;
  min-height: 4rem;
  font-family: inherit;
}

.feedback-textarea:focus {
  outline: none;
  border-color: var(--primary);
  ring: 2px;
  ring-color: var(--primary);
}

.feedback-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-privacy-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 0.75rem;
  background-color: var(--muted);
  border-radius: 0.375rem;
  border: 1px solid var(--border);
}

.feedback-privacy-notice svg {
  flex-shrink: 0;
  color: var(--muted-foreground);
  opacity: 0.7;
}

.feedback-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.feedback-action-button {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.feedback-action-button.secondary {
  background-color: transparent;
  border: 1px solid var(--border);
  color: var(--muted-foreground);
}

.feedback-action-button.secondary:hover:not(:disabled) {
  background-color: var(--muted);
  color: var(--foreground);
}

.feedback-action-button.primary {
  background-color: var(--primary);
  border: 1px solid var(--primary);
  color: var(--primary-foreground);
}

.feedback-action-button.primary:hover:not(:disabled) {
  opacity: 0.9;
}

.feedback-action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid currentColor;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
```

**Integration:** Add to `ResponseDisplay.vue`

```vue
<!-- In assistant message block, after content -->
<div class="prose prose-sm max-w-none">
  <div v-html="renderMessage(message.content)" />
</div>

<!-- Add feedback component -->
<MessageFeedback :message-id="message.id" />
```

### 5.5 Admin Feedback View

**Component:** `components/admin/FeedbackPanel.vue`

**Layout:**

```
┌──────────────────────────────────────────────────────┐
│ Feedback Overview                    [Refresh]       │
├──────────────────────────────────────────────────────┤
│ ┌──────────┬───────────┬──────────┬───────────────┐ │
│ │ 👍 85%   │ 👎 15%    │ Total    │ With Comments │ │
│ │ 340 👍   │ 60 👎     │ 400      │ 45            │ │
│ └──────────┴───────────┴──────────┴───────────────┘ │
├──────────────────────────────────────────────────────┤
│ Filters: [All Feedback ▼] [Show Comments Only]      │
├──────────────────────────────────────────────────────┤
│                                                       │
│ ┌────────────────────────────────────────────────┐  │
│ │ 👎 Unhelpful • john@redhat.com • 2h ago        │  │
│ │                                                 │  │
│ │ User Query:                                     │  │
│ │ "Show me all services owned by Team X"         │  │
│ │                                                 │  │
│ │ Assistant Response:                             │  │
│ │ "I found 500 services across the system..."    │  │
│ │                                                 │  │
│ │ User Feedback:                                  │  │
│ │ "Too many results - I only wanted services     │  │
│ │  owned by Team X, not all services"            │  │
│ │                                                 │  │
│ │ [View Full Conversation]                        │  │
│ └────────────────────────────────────────────────┘  │
│                                                       │
│ ┌────────────────────────────────────────────────┐  │
│ │ 👍 Helpful • jane@redhat.com • 5h ago          │  │
│ │                                                 │  │
│ │ User Query:                                     │  │
│ │ "What's the SLO for service-auth?"             │  │
│ │                                                 │  │
│ │ Assistant Response:                             │  │
│ │ "The SLO for <urn:service:service-auth> is..." │  │
│ └────────────────────────────────────────────────┘  │
│                                                       │
│ [Load More]                                           │
└──────────────────────────────────────────────────────┘
```

**Features:**

- Real-time stats (helpful %, total feedback, etc.)
- Filter by rating (all/helpful/unhelpful)
- Filter by has comments
- Search by user
- Expandable feedback cards
- Link to full conversation (if needed for context)
- Pagination for large volumes

### 5.6 Integration with Admin Dashboard

**Update:** `server/api/admin/stats.get.ts`

Add feedback stats to dashboard overview:

```typescript
{
  // ... existing stats ...

  feedback: {
    totalFeedback: number
    helpfulCount: number
    unhelpfulCount: number
    helpfulPercentage: number
    recentUnhelpfulCount: number  // Last 7 days
    feedbackWithTextCount: number
  }
}
```

**Update:** `server/api/admin/users.get.ts`

Add feedback stats to per-user stats (already done in earlier edit):

```typescript
stats: {
  // ... existing stats ...
  feedbackCount: number
  helpfulCount: number
  unhelpfulCount: number
  helpfulPercentage: number
}
```

### 5.7 Privacy & Security

**User Control:**

- Users explicitly choose to submit feedback
- Feedback submission is opt-in (no tracking without action)
- Clear messaging that feedback helps improve the service

**Admin Access:**

- Admins can ONLY see conversations where feedback was provided
- No backdoor access to all conversation content
- Audit log tracks admin views of feedback (future enhancement)

**Data Retention:**

- Feedback retained indefinitely for quality improvement
- Can be deleted with user account (cascade delete)
- Users can request feedback deletion (GDPR compliance)

---

## Phase 6: Security & Testing

### 5.1 Security Checklist

- [ ] Admin emails validated at bootstrap
- [ ] All admin endpoints require `requireAdmin()` check
- [ ] User status checked on every authenticated request
- [ ] Disabled users immediately logged out (sessions cleared)
- [ ] Admin cannot disable/delete their own account
- [ ] All admin actions logged to audit trail
- [ ] Soft delete preserves data for audit
- [ ] Hard delete requires explicit confirmation
- [ ] No access to user conversation content (only metadata)

### 5.2 Authorization Tests

**Test:** Admin access control

```typescript
describe('Admin Authorization', () => {
  it('should allow admin to access admin endpoints', async () => {
    // Test admin can call /api/admin/users
  });

  it('should deny non-admin users admin endpoints', async () => {
    // Test regular user gets 403
  });

  it('should deny unauthenticated users admin endpoints', async () => {
    // Test gets 401
  });

  it('should prevent admin from disabling themselves', async () => {
    // Test self-disable returns 400
  });

  it('should prevent admin from deleting themselves', async () => {
    // Test self-delete returns 400
  });
});
```

**Test:** User status enforcement

```typescript
describe('User Status Enforcement', () => {
  it('should block disabled user from making requests', async () => {
    // Disable user, attempt API call, expect 403
  });

  it('should clear sessions when user is disabled', async () => {
    // Disable user, verify sessions deleted
  });

  it('should allow re-enabled user to log in', async () => {
    // Disable then enable user, verify can login
  });
});
```

### 5.3 Audit Log Tests

```typescript
describe('Admin Audit Log', () => {
  it('should log user disable action', async () => {
    // Disable user, verify audit log entry
  });

  it('should log user enable action', async () => {
    // Enable user, verify audit log entry
  });

  it('should log user deletion', async () => {
    // Delete user, verify audit log entry before deletion
  });

  it('should log role changes', async () => {
    // Change role, verify audit log entry
  });
});
```

---

## Implementation Timeline

### Week 1: Backend Foundation (Phase 1-2)

**Day 1-2: Database Schema**

- [ ] Create migration for new user fields
- [ ] Create admin audit log table
- [ ] Test migration locally
- [ ] Document schema changes

**Day 3-4: Authorization System**

- [ ] Implement admin bootstrap plugin
- [ ] Create admin utilities (`requireAdmin`, `logAdminAction`)
- [ ] Add user status middleware
- [ ] Update session handling for `lastLoginAt`

**Day 5: Testing**

- [ ] Unit tests for authorization
- [ ] Integration tests for user status checks
- [ ] Test admin bootstrap with multiple emails

### Week 2: Admin API (Phase 3)

**Day 1-2: User Management Endpoints**

- [ ] Implement GET /api/admin/users (with stats)
- [ ] Implement PATCH /api/admin/users/[id]
- [ ] Implement DELETE /api/admin/users/[id]

**Day 3: Dashboard Stats**

- [ ] Implement GET /api/admin/stats
- [ ] Optimize queries for performance
- [ ] Add caching if needed

**Day 4-5: Testing & Documentation**

- [ ] API endpoint tests
- [ ] Performance testing with large user base
- [ ] API documentation

### Week 3: Admin UI (Phase 4)

**Day 1-2: Components**

- [ ] Create admin route middleware
- [ ] Build AdminStatsCards component
- [ ] Build AdminUserTable component
- [ ] Build AdminUserActionMenu component

**Day 3-4: Integration**

- [ ] Create admin page
- [ ] Connect to admin API endpoints
- [ ] Add real-time updates (polling or websocket)
- [ ] Error handling and loading states

**Day 5: Polish**

- [ ] Styling and responsive design
- [ ] Add admin menu item to main app
- [ ] User testing
- [ ] UI feedback improvements

### Week 4: Feedback System (Phase 5)

**Day 1-2: Backend**

- [ ] Add message feedback table migration
- [ ] Implement POST /api/feedback endpoint
- [ ] Implement GET /api/admin/feedback endpoint
- [ ] Add feedback stats to admin endpoints

**Day 2-3: User-Facing UI**

- [ ] Create MessageFeedback component
- [ ] Design delightful UX interactions
- [ ] Add animations and transitions
- [ ] Integrate with ResponseDisplay component
- [ ] Test feedback submission flow

**Day 4-5: Admin Feedback View**

- [ ] Build AdminFeedbackPanel component
- [ ] Add feedback tab to admin dashboard
- [ ] Display feedback stats
- [ ] Test feedback filtering and search
- [ ] Polish UI/UX

### Week 5: Testing & Deployment (Phase 6)

**Day 1-2: End-to-End Testing**

- [ ] E2E tests for admin workflows
- [ ] Test across different user roles
- [ ] Test edge cases (self-disable, etc.)

**Day 3-4: Security Review**

- [ ] Code review for security issues
- [ ] Penetration testing
- [ ] Audit log verification
- [ ] Documentation review

**Day 5: Deployment**

- [ ] Deploy to staging environment
- [ ] Run migration on staging database
- [ ] Set ADMIN_EMAILS for production
- [ ] Deploy to production
- [ ] Monitor for issues

---

## Success Metrics

**Security:**

- Zero unauthorized admin access attempts succeed
- 100% of admin actions logged
- Disabled user sessions cleared within 1 request
- Admin access to conversations limited to feedback-provided content only

**Performance:**

- Admin user list loads in < 500ms (100 users)
- User enable/disable completes in < 200ms
- Dashboard stats load in < 300ms
- Feedback submission completes in < 200ms
- Feedback list loads in < 400ms (100 feedback items)

**Usability:**

- Admins can disable user in < 3 clicks
- Search/filter responds in < 100ms
- Clear visual feedback for all actions

**User Feedback:**

- Feedback submission rate > 10% of conversations
- Thumbs up/down interaction feels natural and delightful
- Text feedback provided in > 30% of negative ratings
- Feedback UI doesn't disrupt conversation flow

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Admin accidentally disables themselves | Medium | Prevent self-disable in API, show warning in UI |
| Mass user deletion by mistake | High | Require explicit confirmation, audit logging |
| Performance issues with large user lists | Medium | Pagination, indexing, caching |
| Admin privilege escalation | High | Comprehensive authorization tests, code review |
| Disabled user circumvents check | High | Middleware on every request, session clearing |

---

## Future Enhancements (Post-MVP)

1. **Advanced Audit Logging**
   - View audit log in UI
   - Filter by admin, action, date range
   - Export audit logs

2. **Bulk Operations**
   - Bulk disable users
   - Bulk role changes
   - CSV import/export

3. **User Impersonation**
   - Admin can impersonate user (for support)
   - Audit trail for impersonation sessions
   - Clear visual indicator when impersonating

4. **Advanced Analytics**
   - User activity graphs
   - API usage trends
   - Geographic distribution

5. **Role Granularity**
   - Multiple admin levels (super-admin, moderator, support)
   - Permission-based access control
   - Custom role definitions

6. **Automated Actions**
   - Auto-disable inactive users after N days
   - Auto-archive old accounts
   - Alert on suspicious activity

---

## References

- [Better Auth Documentation](https://www.better-auth.com/)
- [Drizzle ORM - Migrations](https://orm.drizzle.team/docs/migrations)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

---

**Last Updated:** 2025-10-17
**Next Review:** After Phase 1 completion
