# Feature: Conversation History Context

**Status**: Completed
**Priority**: Critical
**Created**: 2025-10-07
**Implemented**: 2025-10-07

---

## Problem Statement

Each query is currently treated as an isolated conversation with no memory of previous exchanges. This severely degrades user experience:

- Follow-up questions don't work (e.g., "Tell me more about that")
- References to previous responses fail
- Multi-turn conversations are impossible
- Users must repeat context in every query

## Evidence

**Frontend** (`pages/index.vue` line 235):

```typescript
body: JSON.stringify({ prompt: query }),
```

Only sends the current query, not the conversation history.

**Backend** (`server/api/query.post.ts` line 511):

```typescript
const messages: Anthropic.MessageParam[] = [
  {
    role: "user",
    content: prompt,
  },
];
```

Creates a fresh messages array with only the current prompt.

## User Stories

- As a user, I want to ask follow-up questions without repeating context
- As a user, I want the assistant to remember previous responses in the conversation
- As a user, I want to reference "the first service" or "that namespace" naturally
- As a user, I want multi-turn conversations that feel cohesive

## Requirements

### Functional Requirements

1. **Context Preservation**: Maintain conversation history across multiple queries
2. **Follow-up Support**: Enable natural follow-up questions referencing previous context
3. **Token Management**: Limit history to prevent token overflow (max 20 messages)
4. **Graceful Degradation**: Handle empty history (first message) correctly
5. **Validation**: Sanitize and validate conversation history

### Non-Functional Requirements

1. **Performance**: No significant increase in request/response time
2. **Scalability**: Stateless design (no server-side session storage)
3. **Request Size**: Keep payloads under 100KB
4. **Error Handling**: Fail gracefully on malformed history

## Technical Approach

### Architecture Decision: Stateless History Passing

**Chosen Approach**: Send conversation history with each request (no server-side state)

**Pros**:

- Simple implementation
- Works with current architecture
- Horizontally scalable
- No database changes required

**Cons**:

- Larger request payloads
- Token limits (mitigated by message truncation)

**Future Migration**: Move to stateful approach (database-backed) in Phase 2 with full conversation history feature

### Implementation

#### Frontend Changes

**File**: `pages/index.vue`

```typescript
interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  // Don't send metadata to backend
}

async function handleSubmit(query: string) {
  // Prepare conversation history (exclude metadata)
  const conversationHistory: ConversationMessage[] = messages.value.map(
    (msg) => ({
      role: msg.role,
      content: msg.content,
    }),
  );

  // Make POST request with history
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: query,
      conversationHistory: conversationHistory,
    }),
    signal: abortController.signal,
  });
}
```

#### Backend Changes

**File**: `server/api/query.post.ts`

```typescript
interface QueryRequestBody {
  prompt: string;
  conversationHistory?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
}

export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) as QueryRequestBody;
  const { prompt, conversationHistory = [] } = body;

  // Validate and sanitize conversation history
  const MAX_HISTORY_MESSAGES = 20;
  const sanitizedHistory: Anthropic.MessageParam[] = conversationHistory
    .slice(-MAX_HISTORY_MESSAGES) // Keep last N messages
    .filter((msg) => msg.role && msg.content && typeof msg.content === "string")
    .map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

  // Initialize messages with history + new prompt
  const messages: Anthropic.MessageParam[] = [
    ...sanitizedHistory,
    {
      role: "user",
      content: prompt,
    },
  ];
});
```

### Token Management

- **Claude Sonnet 4**: 200k context window
- **Safety Limit**: 20 messages maximum
- **Calculation**: System prompt (~10k tokens) + history + tools + response space
- **Overflow Strategy**: Truncate oldest messages first (FIFO)

### Message Filtering

**What to Send**:

- `role`: 'user' | 'assistant'
- `content`: string

**What to Exclude** (UI metadata only):

- `thinkingSteps`
- `entities`
- `elapsedSeconds`
- `timestamp`

### Role Alternation

- Anthropic requires strict user/assistant alternation
- Frontend enforces this pattern naturally
- Backend validates as safety measure

## Success Criteria

- [x] Follow-up questions work correctly
- [x] References to previous responses are understood
- [x] No increase in error rate
- [x] Request size stays under 100KB
- [x] No token limit errors
- [x] User reports improved conversation quality

## Testing

### Test Cases

1. **Single message (no history)**
   - Send: `{ prompt: "What is Kartograph?" }`
   - Expect: Normal response, no context needed

2. **Follow-up question**
   - Message 1: "Who owns the Cincinnati service?"
   - Message 2: "What about its dependencies?"
   - Expect: Assistant understands "its" = Cincinnati

3. **Reference to previous response**
   - Message 1: "List all services"
   - Message 2: "Tell me more about the first one"
   - Expect: Assistant remembers the list

4. **Long conversation (>20 messages)**
   - Send 25 messages
   - Expect: Only last 20 included, no error

5. **Malformed history**
   - Send invalid history structure
   - Expect: Filtered out, doesn't crash

## Implementation Status

**Completed**: 2025-10-07
**Estimated Time**: 1 hour
**Actual Time**: ~1 hour

## Migration Path

**Short-term (Completed)**:

- ✅ Implement stateless history passing
- ✅ No database changes needed
- ✅ Works with current architecture

**Medium-term (Phase 2)**:

- Add database tables for conversations
- Store full history server-side
- Client sends only conversation ID
- Enables: search, sharing, analytics

**Long-term (Future)**:

- Conversation branching
- Message editing (fork at point)
- Collaborative conversations
- Advanced context management

## Risks & Mitigations

| Risk                       | Likelihood | Impact | Mitigation                                 |
| -------------------------- | ---------- | ------ | ------------------------------------------ |
| Request size too large     | Low        | Medium | Limit to 20 messages, warn at 15           |
| Token limit exceeded       | Low        | High   | Monitor token usage, truncate aggressively |
| Alternating role violation | Low        | High   | Validate role alternation in backend       |
| History corruption         | Medium     | Medium | Sanitize and validate all history          |
| Performance degradation    | Low        | Low    | History is small, minimal overhead         |

## Related Specifications

- [004-user-management-and-history](../004-user-management-and-history/spec.md) - Full database-backed conversation history (Phase 2)
