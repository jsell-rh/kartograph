# User Management & Conversation History - Implementation Plan

**Date**: 2025-10-07
**Version**: 1.0
**Status**: Planning

---

## Executive Summary

This document outlines the architecture and implementation plan for adding comprehensive user management and conversation history tracking to the Kartograph knowledge graph visualizer. The expansion enables multi-user conversation persistence, API key management for MCP integration, and a seamless conversation browsing experience.

---

## Phase 1: User Management

### 1.1 Database Schema Extensions

**New Tables:**

```typescript
// visualizer/server/db/schema.ts

export const apiKeys = sqliteTable("api_keys", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(), // User-friendly name: "MCP Server", "CI Pipeline", etc.
  keyHash: text("key_hash").notNull(), // SHA-256 hash of the actual key
  keyPrefix: text("key_prefix").notNull(), // First 8 chars for display: "cg_abc12..."
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  lastUsedAt: integer("last_used_at", { mode: "timestamp" }),
  expiresAt: integer("expires_at", { mode: "timestamp" }), // Optional expiration
  isActive: integer("is_active", { mode: "boolean" }).notNull().default(true),
});

export const userPreferences = sqliteTable("user_preferences", {
  userId: text("user_id")
    .primaryKey()
    .references(() => users.id, { onDelete: "cascade" }),
  theme: text("theme").default("system"), // 'light', 'dark', 'system'
  defaultModel: text("default_model").default("claude-sonnet-4-20250514"),
  apiKeyName: text("api_key_name"), // Preferred API key display name
  notificationsEnabled: integer("notifications_enabled", {
    mode: "boolean",
  }).default(true),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});
```

**Migration Strategy:**

- Create migration file: `0002_add_user_management.sql`
- Run migration on app startup via Drizzle
- Handle existing users gracefully (create default preferences)

### 1.2 API Key Generation System

**Key Format:**

```
cg_dev_1a2b3c4d5e6f7g8h9i0j...  (total 48 chars)
├─┬─ ──┬── ──────────┬─────────
│ │    │            │
│ │    │            └─ Random secure token (32 chars)
│ │    └────────────── Environment hint (dev/prod/test)
│ └─────────────────── Product prefix
└───────────────────── "kartograph" abbreviated
```

**Security Model:**

- Generate 256-bit cryptographically secure random keys
- Store only SHA-256 hash in database
- Return plaintext key only once at creation time
- Prefix allows quick identification without exposing full key
- Support key rotation (create new, deprecate old)

**Implementation Files:**

- `server/utils/api-keys.ts` - Key generation, hashing, validation
- `server/api/user/api-keys.get.ts` - List user's keys
- `server/api/user/api-keys.post.ts` - Create new key
- `server/api/user/api-keys/[id].delete.ts` - Revoke key
- `server/middleware/api-auth.ts` - Validate API key on requests

### 1.3 User Preferences

**Preferences Page:**

- Route: `/settings` or `/preferences`
- Sections:
  - Profile (name, email - read-only from auth)
  - Appearance (theme selection)
  - API Keys (management interface)
  - Advanced (default model, etc.)

**Implementation Files:**

- `pages/settings.vue` - Main preferences page
- `components/settings/ProfileSection.vue`
- `components/settings/ApiKeySection.vue`
- `components/settings/AppearanceSection.vue`
- `server/api/user/preferences.get.ts`
- `server/api/user/preferences.put.ts`

### 1.4 Enhanced User Menu

**Current State:** Basic dropdown with logout only

**Enhanced State:**

- User info display (name, email, avatar initials)
- Settings/Preferences link
- API Keys (count badge)
- Logout

**Implementation:**

- Update `pages/index.vue` user menu dropdown
- Add navigation to settings page
- Add API key count indicator

---

## Phase 2: Conversation History

### 2.1 Database Schema

```typescript
// visualizer/server/db/schema.ts

export const conversations = sqliteTable("conversations", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(), // LLM-generated or user-edited
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  lastMessageAt: integer("last_message_at", { mode: "timestamp" }),
  messageCount: integer("message_count").notNull().default(0),
  isArchived: integer("is_archived", { mode: "boolean" }).default(false),
});

export const messages = sqliteTable("messages", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),
  conversationId: text("conversation_id")
    .notNull()
    .references(() => conversations.id, { onDelete: "cascade" }),
  role: text("role").notNull(), // 'user' | 'assistant'
  content: text("content").notNull(),
  timestamp: integer("timestamp", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),

  // Metadata (stored as JSON)
  thinkingSteps: text("thinking_steps", { mode: "json" }), // Array of ThinkingStep objects
  entities: text("entities", { mode: "json" }), // Array of extracted entities
  elapsedSeconds: integer("elapsed_seconds"),

  // Tool usage tracking
  toolCalls: text("tool_calls", { mode: "json" }), // Array of tool call metadata
});

// Indexes for performance
export const conversationsByUser = index("conversations_by_user").on(
  conversations.userId,
  conversations.lastMessageAt,
);
export const messagesByConversation = index("messages_by_conversation").on(
  messages.conversationId,
  messages.timestamp,
);
```

### 2.2 Backend API Design

#### Conversation Management APIs

**GET /api/conversations**

- Query params: `?archived=false&limit=50&offset=0`
- Returns: Paginated list of user's conversations
- Sort: lastMessageAt DESC (most recent first)
- Response:

  ```typescript
  {
    conversations: [
      {
        id: string
        title: string
        createdAt: Date
        lastMessageAt: Date
        messageCount: number
        preview: string // First 100 chars of last message
      }
    ],
    total: number
    hasMore: boolean
  }
  ```

**POST /api/conversations**

- Body: `{ title?: string }`
- Creates new conversation
- If no title provided, uses "New Conversation" temporarily
- Returns: `{ id, title, createdAt }`

**GET /api/conversations/:id**

- Returns full conversation with all messages
- Security: Verify userId matches conversation owner
- Response:

  ```typescript
  {
    id: string
    title: string
    createdAt: Date
    messages: Message[]
  }
  ```

**PUT /api/conversations/:id**

- Body: `{ title: string }`
- Updates conversation title
- Returns: Updated conversation

**DELETE /api/conversations/:id**

- Soft delete (archives) or hard delete based on query param
- Security: Verify ownership
- Returns: `{ success: true }`

**GET /api/conversations/:id/messages**

- Paginated message retrieval
- Query params: `?limit=50&before=<messageId>`
- For infinite scroll in UI

#### Modified Query Endpoint

**POST /api/query**

- Enhanced body:

  ```typescript
  {
    prompt: string
    conversationId?: string // Optional: attach to existing conversation
    createConversation?: boolean // Auto-create if not in conversation
  }
  ```

- Behavior:
  1. If `conversationId` provided, append to that conversation
  2. If `createConversation: true`, create new conversation first
  3. Save both user message and assistant response to DB
  4. Update conversation's `lastMessageAt` and `messageCount`
  5. After first exchange, generate title via LLM

**Title Generation:**

- Triggered after first user message + assistant response
- Use Claude Haiku (fast, cheap) to generate concise title
- Prompt: "Summarize this conversation in 5-7 words: [first exchange]"
- Update conversation asynchronously (don't block response)

### 2.3 Frontend Architecture

#### Component Hierarchy

```
pages/
  index.vue (Main App)
    ├─ ConversationSidebar.vue (LEFT PANEL - 300px fixed width)
    │   ├─ ConversationList.vue
    │   │   ├─ ConversationItem.vue (repeatable)
    │   │   └─ NewConversationButton.vue
    │   └─ ConversationSearch.vue
    │
    ├─ ConversationView.vue (CENTER PANEL - flex-1)
    │   ├─ ResponseDisplay.vue (existing)
    │   └─ QueryInput.vue (existing)
    │
    └─ GraphExplorer.vue (RIGHT PANEL - existing)
```

#### State Management

**Store: `stores/conversation.ts`**

```typescript
export const useConversationStore = defineStore('conversation', {
  state: () => ({
    conversations: [] as Conversation[],
    activeConversationId: null as string | null,
    messages: [] as Message[],
    isLoadingConversations: false,
    isLoadingMessages: false,
    currentQuery: null as AbortController | null,
  }),

  actions: {
    async fetchConversations()
    async loadConversation(id: string)
    async createConversation(title?: string)
    async renameConversation(id: string, title: string)
    async deleteConversation(id: string)
    async sendMessage(prompt: string)
    stopCurrentQuery()
    switchConversation(id: string) // Aborts current, loads new
  },

  getters: {
    activeConversation()
    sortedConversations()
    hasActiveQuery()
  }
})
```

#### Conversation Switching Logic

**Challenge:** User switches conversation while query is in-progress

**Solution:**

1. Detect conversation switch in store action
2. Abort current SSE stream via AbortController
3. Clear current thinking steps/loading state
4. Save partial assistant response (if any) to old conversation
5. Load new conversation messages
6. Update UI to show new conversation
7. Reset query input

**Implementation:**

```typescript
async switchConversation(newId: string) {
  // Abort any in-flight query
  if (this.currentQuery) {
    this.currentQuery.abort()
    this.currentQuery = null
  }

  // Save current state if needed
  if (this.activeConversationId && this.messages.length > 0) {
    // Messages already saved via SSE stream
  }

  // Switch to new conversation
  this.activeConversationId = newId
  await this.loadConversation(newId)
}
```

### 2.4 UI/UX Design

#### Conversation Sidebar

**Layout:**

```
┌─────────────────────────────┐
│  ┌─────────────────────┐   │
│  │  + New Conversation  │   │
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │ 🔍 Search...         │   │
│  └─────────────────────┘   │
│                             │
│  Today                      │
│  ┌─────────────────────┐   │
│  │ ● Graph schema que...│ ← Active
│  │   Just now           │   │
│  └─────────────────────┘   │
│  ┌─────────────────────┐   │
│  │   User management... │   │
│  │   2 hours ago        │   │
│  └─────────────────────┘   │
│                             │
│  Yesterday                  │
│  ┌─────────────────────┐   │
│  │   Service dependen...│   │
│  │   Yesterday 3:42 PM  │   │
│  └─────────────────────┘   │
│                             │
│  Last 7 Days               │
│  ...                        │
└─────────────────────────────┘
```

**Features:**

- Group by time: Today, Yesterday, Last 7 Days, Last 30 Days
- Active conversation highlighted
- Hover actions: Rename (pencil), Delete (trash)
- Inline rename via double-click
- Smooth animations for conversation switching
- Optimistic UI updates

#### Conversation Item States

```typescript
interface ConversationItemState {
  isActive: boolean;
  isHovered: boolean;
  isRenaming: boolean;
  isLoading: boolean;
}

// Visual indicators:
// - Active: Blue left border, bold text
// - Hover: Background highlight, show action buttons
// - Renaming: Input field replaces title
// - Loading: Skeleton or spinner
```

### 2.5 Message Persistence Flow

**Query Lifecycle:**

1. **User submits query**
   - If no active conversation, create one
   - Save user message to DB immediately
   - Generate message ID, add to conversation
   - Start SSE stream to `/api/query`

2. **SSE events arrive**
   - `text`: Buffer assistant response (don't save yet)
   - `thinking`: Store in temporary state
   - `entities`: Extract and buffer
   - `tool_call`: Track for metadata
   - `done`: Save complete assistant message to DB

3. **Post-completion**
   - Update conversation `lastMessageAt`
   - Increment `messageCount`
   - If first exchange, trigger title generation
   - Update UI optimistically

4. **Title generation (background)**

   ```typescript
   // server/utils/conversation-title.ts
   async function generateConversationTitle(
     firstUserMessage: string,
     firstAssistantMessage: string
   ): Promise<string> {
     const response = await anthropic.messages.create({
       model: 'claude-haiku-3-5-20241022',
       max_tokens: 50,
       messages: [{
         role: 'user',
         content: `Summarize this conversation in 5-7 words:
   ```

User: ${firstUserMessage}
Assistant: ${firstAssistantMessage.substring(0, 500)}...`
}]
})

     return response.content[0].text.trim()

}

````

### 2.6 Migration Strategy

**Phase 2A: Database Setup**
1. Create migration `0003_add_conversations.sql`
2. Add tables: conversations, messages
3. Test migration on empty DB
4. Run migration on dev environment

**Phase 2B: Backend Implementation**
1. Implement conversation CRUD APIs
2. Modify `/api/query` to save messages
3. Add title generation utility
4. Add tests for conversation APIs

**Phase 2C: Frontend Implementation**
1. Create conversation store
2. Build ConversationSidebar component
3. Integrate with existing index.vue
4. Add conversation switching logic
5. Test seamless switching during queries

**Phase 2D: Polish & Testing**
1. Add loading states and skeletons
2. Error handling for failed saves
3. Offline support (queue messages)
4. Performance testing (large conversation lists)

---

## Security Considerations

### Authentication & Authorization

**API Key Validation:**
- Middleware checks `Authorization: Bearer cg_...` header
- Hash incoming key, compare with stored hashes
- Rate limit by key (100 req/min)
- Track `lastUsedAt` on each use
- Support key expiration

**Conversation Access Control:**
- Every conversation/message query MUST verify:
```sql
WHERE userId = :currentUserId
````

- Use Drizzle's `.where()` filters consistently
- Never expose conversation IDs in URLs without auth check

**Session Management:**

- Existing session-based auth for web UI
- API key auth for programmatic access (MCP)
- Separate auth middleware for each

### Data Privacy

**User Isolation:**

- Conversations are fully isolated per user
- No cross-user conversation access
- Soft delete maintains audit trail
- Hard delete option for GDPR compliance

**API Key Security:**

- Never log full API keys (only prefix)
- Store only SHA-256 hashes
- Revoked keys immediately inactive
- Auto-expire keys after 90 days (optional)

---

## Performance Considerations

### Database Indexing

```sql
-- Critical indexes for query performance
CREATE INDEX idx_conversations_user_time ON conversations(user_id, last_message_at DESC);
CREATE INDEX idx_messages_conversation_time ON messages(conversation_id, timestamp DESC);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

### Caching Strategy

**Conversation List:**

- Cache in memory for 30 seconds
- Invalidate on new message or title change
- Use Nuxt's built-in caching

**Active Conversation Messages:**

- Load all messages on conversation switch
- Cache in Pinia store
- Only refetch if stale (>5 min)

### Pagination

**Conversation List:**

- Load 50 conversations at a time
- Infinite scroll for older conversations
- Virtual scrolling for 1000+ conversations

**Message History:**

- Load last 50 messages initially
- "Load more" button for older messages
- Reverse chronological order

---

## Implementation Timeline

### Week 1: Database & Backend Foundation

- [ ] Design and create database migrations
- [ ] Implement conversation CRUD APIs
- [ ] Implement API key generation system
- [ ] Add auth middleware
- [ ] Unit tests for backend

### Week 2: Frontend State & Components

- [ ] Create conversation store (Pinia)
- [ ] Build ConversationSidebar component
- [ ] Build ConversationList & ConversationItem
- [ ] Implement conversation switching
- [ ] Integration with existing chat UI

### Week 3: User Management

- [ ] Create settings/preferences page
- [ ] Build API key management UI
- [ ] Implement user preferences backend
- [ ] Update user menu dropdown

### Week 4: Polish & Testing

- [ ] LLM-based conversation naming
- [ ] Error handling & edge cases
- [ ] Loading states & animations
- [ ] Performance optimization
- [ ] End-to-end testing
- [ ] Documentation

---

## Open Questions & Decisions Needed

1. **Conversation Limits:**
   - Max conversations per user? (1000?)
   - Max messages per conversation? (10,000?)
   - Archive old conversations automatically?

2. **API Key Pricing/Limits:**
   - How many keys per user? (5-10?)
   - Rate limits per key?
   - Different tiers (free vs paid)?

3. **Message Retention:**
   - Keep messages forever?
   - Auto-delete after N days?
   - Export functionality?

4. **Search:**
   - Full-text search across conversations?
   - SQLite FTS5 extension?
   - Separate search index?

5. **Sharing:**
   - Share conversations with other users?
   - Public conversation links?
   - Export to Markdown/JSON?

---

## Success Metrics

**User Engagement:**

- Average conversations per user
- Messages per conversation
- Conversation retention (users returning to old convos)

**Performance:**

- Conversation list load time < 200ms
- Message load time < 100ms
- Conversation switch time < 300ms

**API Usage:**

- API keys generated per user
- API request volume
- Error rates

---

## Risks & Mitigations

| Risk                          | Impact | Mitigation                                       |
| ----------------------------- | ------ | ------------------------------------------------ |
| Database migration fails      | High   | Test migrations thoroughly, backup before deploy |
| Conversation switching breaks | High   | Comprehensive tests, feature flag                |
| LLM title generation slow     | Medium | Async generation, fallback to "New Conversation" |
| API key leakage               | High   | Clear warnings in UI, revocation tools           |
| Poor conversation list UX     | Medium | User testing, iterate on design                  |

---

## Future Enhancements (Post-MVP)

1. **Conversation Templates**
   - Pre-built queries for common use cases
   - Share templates across team

2. **Conversation Branching**
   - Fork conversations at any point
   - Compare different query paths

3. **Collaborative Conversations**
   - Multi-user conversations
   - Real-time updates via WebSocket

4. **Advanced Search**
   - Full-text search with filters
   - Search within entities
   - Saved searches

5. **Analytics Dashboard**
   - Query patterns
   - Most used entity types
   - Response time trends

6. **MCP Server Integration**
   - Dedicated MCP server package
   - Auto-discovery of graph schema
   - Streaming responses via MCP transport

---

## References

- [Drizzle ORM Docs](https://orm.drizzle.team/)
- [Nuxt Auth Utils](https://github.com/atinux/nuxt-auth-utils)
- [Pinia Stores](https://pinia.vuejs.org/)
- [Claude API - Message Batches](https://docs.anthropic.com/claude/reference/messages-batches)

---

**Last Updated:** 2025-10-07
**Next Review:** After Phase 1 completion
