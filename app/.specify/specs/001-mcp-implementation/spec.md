# MCP Server Implementation Plan

## Overview

Expose the `query_dgraph` tool as a hosted MCP (Model Context Protocol) endpoint to enable local Claude Desktop clients and standalone agents to query the remote Dgraph instance.

## Architecture Decision

**Approach**: Integrated Nitro MCP endpoints within the existing Nuxt application

**Rationale**:

- Reuses existing Dgraph connection and query tools
- Shares Better Auth authentication infrastructure
- Leverages existing database for token storage
- Simpler deployment (single service)
- Shared monitoring and logging

## Security Model

### API Token Authentication

**Token Format**: `cart_<base64url(24 random bytes)>`

- Example: `cart_example123456789012345678901`
- Prefix for easy identification
- 24 random bytes = 192 bits of entropy
- Base64url encoding (URL-safe, no padding)

**Storage**: SHA-256 hash only

- Never store plaintext tokens
- User sees token ONCE on creation
- Tokens are irrecoverable if lost

**Token Metadata**:

- Name/description (user-defined)
- Created by (userId)
- Total queries executed
- Last used timestamp
- Expires at (max 1 year, default 90 days)
- Revoked at (soft delete)

### Read-Only Enforcement

**Query Validation** (multiple layers):

1. **Mutation Detection Regex**:

   ```typescript
   const MUTATION_PATTERN = /\b(set\s*\{|delete\s*\{|upsert\s*\{|mutation)/i;
   ```

2. **Query Timeout**: 30 seconds max
3. **Content-Type Check**: Must be `application/dql`
4. **Method Check**: Only DQL queries, no `/mutate` endpoint access

### Rate Limiting

**Algorithm**: Sliding window (per token)

- 100 queries per hour (configurable via `API_TOKEN_RATE_LIMIT`)
- Window slides with each query
- Tracked in-memory with periodic database sync
- Returns `429 Too Many Requests` when exceeded
- Includes `Retry-After` header

### Audit Logging

**Logged on Every Query**:

- Token ID and User ID
- Query text (full DQL)
- Execution time (ms)
- Success/failure status
- Error message (if failed)
- Timestamp

**Retention**: Configurable via `AUDIT_LOG_RETENTION_DAYS` (default: 90 days)

## Database Schema

### `api_tokens` Table

```typescript
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
  createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
  revokedAt: integer("revoked_at", { mode: "timestamp" }),
});
```

### `query_audit_log` Table

```typescript
export const queryAuditLog = sqliteTable("query_audit_log", {
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
  timestamp: integer("timestamp", { mode: "timestamp" }).notNull(),
});

// Indexes for performance
export const queryAuditLogTokenIdIndex = index(
  "query_audit_log_token_id_idx",
).on(queryAuditLog.tokenId);
export const queryAuditLogTimestampIndex = index(
  "query_audit_log_timestamp_idx",
).on(queryAuditLog.timestamp);
```

## Environment Variables

```bash
# MCP Server Configuration
AUDIT_LOG_RETENTION_DAYS=90                # Default: 90 days
API_TOKEN_RATE_LIMIT=100                   # Queries per hour, default: 100
API_TOKEN_MAX_EXPIRY_DAYS=365              # Max token lifetime, default: 365 (1 year)
API_TOKEN_DEFAULT_EXPIRY_DAYS=90           # Default token lifetime, default: 90 days
```

## API Endpoints

### Token Management

#### `POST /api/tokens`

Create new API token

**Request**:

```json
{
  "name": "My Local Agent",
  "expiryDays": 90 // Optional, defaults to API_TOKEN_DEFAULT_EXPIRY_DAYS
}
```

**Response**:

```json
{
  "success": true,
  "token": "cart_example123456789012345678901",
  "id": "uuid",
  "name": "My Local Agent",
  "expiresAt": "2025-07-08T00:00:00Z",
  "warning": "Save this token now - you won't be able to see it again"
}
```

#### `GET /api/tokens`

List user's API tokens

**Response**:

```json
{
  "tokens": [
    {
      "id": "uuid",
      "name": "My Local Agent",
      "totalQueries": 1234,
      "lastUsedAt": "2025-04-08T12:34:56Z",
      "expiresAt": "2025-07-08T00:00:00Z",
      "createdAt": "2025-04-08T00:00:00Z",
      "revokedAt": null
    }
  ]
}
```

#### `DELETE /api/tokens/:id`

Revoke API token (soft delete)

**Response**:

```json
{
  "success": true,
  "message": "Token revoked"
}
```

### MCP Protocol Endpoints

#### `GET /api/mcp/sse`

SSE transport for MCP protocol

**Authentication**: Bearer token in `Authorization` header

```
Authorization: Bearer cart_example123456789012345678901
```

**Response**: Server-Sent Events stream

```
event: endpoint
data: {"endpoint":"sse"}

event: message
data: {"jsonrpc":"2.0","id":"1","result":{"...":"..."}}
```

#### `POST /api/mcp/message`

JSON-RPC message handler for MCP

**Authentication**: Bearer token in `Authorization` header

**Request**:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "query_dgraph",
    "arguments": {
      "dql": "{ query(func: has(<urn:predicate:type>)) { uid <urn:predicate:type> } }",
      "description": "List all entity types"
    }
  }
}
```

**Response**:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"data\": {\n    \"query\": [...]\n  }\n}"
      }
    ],
    "isError": false
  }
}
```

## Implementation Phases

### Phase 1: Database Schema & Token API (Current)

**Files to Create/Modify**:

- `server/db/schema.ts` - Add `apiTokens` and `queryAuditLog` tables
- `server/db/migrations/000X_api_tokens.sql` - Migration script
- `server/utils/tokens.ts` - Token generation and validation utilities
- `server/api/tokens/index.get.ts` - List tokens
- `server/api/tokens/index.post.ts` - Create token
- `server/api/tokens/[id].delete.ts` - Revoke token
- `server/middleware/tokenAuth.ts` - Token authentication middleware

**Token Generation Utility**:

```typescript
import crypto from "crypto";

export function generateToken(): { token: string; hash: string } {
  const randomBytes = crypto.randomBytes(24);
  const token = `cart_${randomBytes.toString("base64url")}`;
  const hash = crypto.createHash("sha256").update(token).digest("hex");
  return { token, hash };
}

export function hashToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}
```

### Phase 2: MCP Server Integration

**Dependencies**:

```bash
npm install @modelcontextprotocol/sdk
```

**Files to Create**:

- `server/api/mcp/sse.get.ts` - SSE transport endpoint
- `server/api/mcp/message.post.ts` - JSON-RPC handler
- `server/lib/mcp-server.ts` - MCP server instance
- `server/lib/mcp-tools.ts` - Tool adapter (wraps `query_dgraph`)

**MCP Server Setup**:

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { executeTool } from "../lib/dgraph-tools";

export function createMCPServer() {
  const server = new Server(
    {
      name: "kartograph-dgraph",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  // Register query_dgraph tool
  server.setRequestHandler("tools/list", async () => ({
    tools: [
      {
        name: "query_dgraph",
        description: "Execute a DQL query against the Dgraph knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            dql: {
              type: "string",
              description: "The DQL (Dgraph Query Language) query to execute",
            },
            description: {
              type: "string",
              description: "A brief description of what this query does",
            },
          },
          required: ["dql", "description"],
        },
      },
    ],
  }));

  server.setRequestHandler("tools/call", async (request) => {
    if (request.params.name !== "query_dgraph") {
      throw new Error(`Unknown tool: ${request.params.name}`);
    }

    const result = await executeTool("query_dgraph", request.params.arguments);

    return {
      content: [
        {
          type: "text",
          text: result,
        },
      ],
      isError: false,
    };
  });

  return server;
}
```

### Phase 3: Security & Validation

**Files to Create**:

- `server/lib/query-validator.ts` - Read-only query validation
- `server/lib/rate-limiter.ts` - Sliding window rate limiter
- `server/lib/audit-logger.ts` - Query audit logging

**Query Validator**:

```typescript
const MUTATION_PATTERN = /\b(set\s*\{|delete\s*\{|upsert\s*\{|mutation)/i;

export function validateReadOnlyQuery(dql: string): {
  valid: boolean;
  error?: string;
} {
  // Check for mutation keywords
  if (MUTATION_PATTERN.test(dql)) {
    return {
      valid: false,
      error:
        "Mutation operations are not allowed. Only read-only queries permitted.",
    };
  }

  // Additional checks could be added here
  // - Max query length
  // - Banned predicates
  // - etc.

  return { valid: true };
}
```

**Rate Limiter**:

```typescript
// In-memory sliding window tracker
const queryWindows = new Map<string, number[]>();

export function checkRateLimit(
  tokenId: string,
  limitPerHour: number,
): {
  allowed: boolean;
  retryAfter?: number;
} {
  const now = Date.now();
  const oneHourAgo = now - 60 * 60 * 1000;

  // Get or create window for this token
  let window = queryWindows.get(tokenId) || [];

  // Remove timestamps older than 1 hour
  window = window.filter((timestamp) => timestamp > oneHourAgo);

  // Check if under limit
  if (window.length >= limitPerHour) {
    const oldestTimestamp = window[0];
    const retryAfter = Math.ceil(
      (oldestTimestamp + 60 * 60 * 1000 - now) / 1000,
    );
    return { allowed: false, retryAfter };
  }

  // Add current timestamp
  window.push(now);
  queryWindows.set(tokenId, window);

  return { allowed: true };
}
```

**Audit Logger**:

```typescript
export async function logQuery(
  tokenId: string,
  userId: string,
  query: string,
  executionTimeMs: number,
  success: boolean,
  errorMessage?: string,
) {
  await db.insert(queryAuditLog).values({
    id: crypto.randomUUID(),
    tokenId,
    userId,
    query,
    executionTimeMs,
    success,
    errorMessage,
    timestamp: new Date(),
  });

  // Update token metrics
  await db
    .update(apiTokens)
    .set({
      totalQueries: sql`${apiTokens.totalQueries} + 1`,
      lastUsedAt: new Date(),
    })
    .where(eq(apiTokens.id, tokenId));
}
```

### Phase 4: UI & Monitoring

**Files to Create**:

- `pages/settings/api-tokens.vue` - Token management page
- `components/TokenCreationDialog.vue` - Token creation wizard
- `components/TokenList.vue` - Token list with metrics

**Features**:

- Create new tokens with custom name and expiry
- Display token ONCE on creation (modal with copy button)
- List all tokens with usage metrics (total queries, last used)
- Revoke tokens
- Visual indicators for expired/revoked tokens
- Usage dashboard (queries per day chart)

### Phase 5: Cleanup & Maintenance

**Files to Create**:

- `server/api/admin/cleanup-tokens.post.ts` - Delete expired/revoked tokens
- `server/api/admin/cleanup-audit-logs.post.ts` - Delete old audit logs
- `server/tasks/cleanup.ts` - Scheduled cleanup jobs (if using Nuxt tasks)

**Cleanup Jobs**:

1. **Expired Tokens**: Delete tokens where `expiresAt < now` AND `revokedAt IS NOT NULL`
2. **Old Audit Logs**: Delete logs where `timestamp < (now - AUDIT_LOG_RETENTION_DAYS)`

**Cron Schedule** (optional):

- Run daily at 2 AM UTC
- Or trigger via admin API endpoint

## Testing Strategy

### Unit Tests

- Token generation and hashing
- Query validation (mutation detection)
- Rate limiting logic

### Integration Tests

- Token CRUD operations
- MCP protocol flow (SSE handshake, JSON-RPC messages)
- Query execution with audit logging
- Rate limit enforcement
- Token expiry/revocation

### Security Tests

- Attempt mutation with read-only token
- Rate limit bypass attempts
- Expired token usage
- Revoked token usage
- Token enumeration protection

## Monitoring & Observability

### Metrics to Track

- Tokens created/revoked per day
- Queries executed per token
- Query execution time (p50, p95, p99)
- Rate limit hits per token
- Failed queries (errors)
- Audit log size growth

### Alerts

- High error rate (> 10% failures)
- Excessive rate limit hits (possible abuse)
- Unusual query patterns (potential security issue)

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Initial admin token created (for testing)
- [ ] Rate limits tested
- [ ] Audit log retention working
- [ ] SSE transport tested with Claude Desktop
- [ ] Documentation updated (how to create/use tokens)
- [ ] Security review completed

## Usage Example (Claude Desktop)

**MCP Server Configuration** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kartograph": {
      "url": "https://kartograph.example.com/api/mcp/sse",
      "headers": {
        "Authorization": "Bearer cart_example123456789012345678901"
      }
    }
  }
}
```

**Claude Desktop Usage**:

```
User: Use the query_dgraph tool to find all applications owned by team-api

Claude: I'll query the Dgraph knowledge graph for applications owned by team-api.

[Executes query_dgraph tool via MCP]

Found 5 applications owned by team-api:
- app-interface
- qontract-reconcile
- qontract-server
- ...
```

## Future Enhancements

1. **Query Templates**: Pre-defined safe queries users can execute
2. **Result Caching**: Cache common queries to reduce load
3. **Query Analytics**: Track popular queries, slow queries
4. **Token Scopes**: Fine-grained permissions (read-only vs full access)
5. **OAuth Integration**: Use Better Auth OAuth tokens instead of API tokens
6. **WebSocket Transport**: In addition to SSE
7. **Query Cost Estimation**: Prevent expensive queries
8. **Multi-tenancy**: Team-based token management
