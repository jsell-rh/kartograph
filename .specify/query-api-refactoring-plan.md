# Query API Refactoring Plan

**Issue:** #18
**Branch:** `refactor/query-api-services`
**Current File:** `app/server/api/query.post.ts` (1366 lines)
**Target:** ~150-200 lines in main handler

## Problem Statement

The `query.post.ts` file has grown to 1366 lines with 10+ distinct responsibilities crammed into a single handler. This violates Single Responsibility Principle and creates several issues:

- ❌ No dependency injection (everything inline)
- ❌ No separation of concerns
- ❌ Hard to test (can't mock DB, Anthropic, Dgraph)
- ❌ Callbacks/side-effects scattered throughout
- ❌ Can't reuse logic in other endpoints
- ❌ 850+ line ReadableStream block
- ❌ Difficult to debug and maintain

## Current Responsibilities (10+)

1. **Authentication & Session Management** (lines ~497-505)
   - Get session, validate user ID

2. **Request Parsing & Validation** (lines ~508-528)
   - Parse body, validate prompt

3. **Conversation CRUD Operations** (lines ~530-573)
   - Create/get conversations
   - Verify ownership

4. **System Prompt Building** (lines 131-260)
   - Fetch Dgraph stats
   - Build dynamic prompt with graph statistics
   - Fallback to static prompt on error

5. **SSE Stream Management** (lines ~636-654)
   - Setup headers
   - Event formatting
   - Keepalive

6. **Agentic Loop Orchestration** (lines ~709-1271)
   - Turn management
   - Tool execution
   - Response streaming

7. **Context Truncation Logic** (lines 77-126, 730-830)
   - Progressive history trimming on 413 errors
   - Orphaned tool_result removal

8. **Entity Extraction** (lines 25-60)
   - URN pattern matching
   - Entity deduplication

9. **Thinking Step Tracking** (lines 679, 947-954, 1176-1184)
   - Track thinking steps during execution

10. **Auto-naming Conversations** (lines 1060-1123)
    - Generate title after first exchange

11. **Usage/Metrics Tracking** (lines 989-996, 1029-1030)
    - Token usage, cost, duration

12. **Error Handling** (lines 81-99, 757-829, 1225-1262, 1288-1310)
    - Retry logic
    - Error message extraction
    - Graceful degradation

## Refactoring Strategy

### Phase 1: Extract Services (Dependency Injection)

Create testable, injectable service classes:

#### 1.1 ConversationService

**File:** `app/server/services/ConversationService.ts`

```typescript
export class ConversationService {
  constructor(
    private db: Database,
    private logger: Logger
  ) {}

  async create(userId: string): Promise<string>
  async get(conversationId: string, userId: string): Promise<Conversation | null>
  async saveMessages(
    conversationId: string,
    userMessage: string,
    assistantMessage: string,
    metadata: {
      thinkingSteps?: ThinkingStep[];
      entities?: Entity[];
      elapsedSeconds?: number;
    }
  ): Promise<{ userMessageId: string; assistantMessageId: string }>
  async generateTitle(
    prompt: string,
    anthropic: Anthropic | AnthropicVertex,
    model: string
  ): Promise<string>
  async updateMetadata(
    conversationId: string,
    updates: Partial<Conversation>
  ): Promise<void>
}
```

**Extracts:**

- Lines 530-573 (conversation creation/retrieval)
- Lines 999-1057 (message saving)
- Lines 1060-1123 (title generation)
- Lines 1035-1049 (metadata updates)

#### 1.2 SystemPromptBuilder

**File:** `app/server/services/SystemPromptBuilder.ts`

```typescript
export class SystemPromptBuilder {
  constructor(
    private dgraphUrl: string,
    private logger: Logger
  ) {}

  async build(): Promise<string>
  private async fetchGraphStats(): Promise<{
    totalEntities: number;
    typeCounts: Record<string, number>;
    predicates: string[];
  }>
  private buildDynamicPrompt(stats: GraphStats): string
  private buildFallbackPrompt(): string
}
```

**Extracts:**

- Lines 131-260 (buildSystemPrompt function)
- Graph stats fetching logic
- Prompt formatting

#### 1.3 EntityExtractor

**File:** `app/server/services/EntityExtractor.ts`

```typescript
export class EntityExtractor {
  private readonly URN_PATTERN = /<urn:([^:]+):([^>]+)>/g;

  extract(text: string): Entity[]
}
```

**Extracts:**

- Lines 25-60 (extractEntities function)
- Lines 26 (URN_PATTERN constant)

### Phase 2: Create Agent Orchestrator (Event-Driven)

#### 2.1 QueryAgent

**File:** `app/server/orchestrator/QueryAgent.ts`

```typescript
import { EventEmitter } from 'events';

export interface QueryAgentConfig {
  maxTurns: number;
  maxContextTruncationAttempts: number;
  model: string;
  maxTokens: number;
}

export class QueryAgent extends EventEmitter {
  constructor(
    private anthropic: Anthropic | AnthropicVertex,
    private tools: Tool[],
    private config: QueryAgentConfig,
    private logger: Logger,
    private contextTruncationStrategy: ContextTruncationStrategy
  ) {
    super();
  }

  async execute(
    systemPrompt: string,
    messages: Anthropic.MessageParam[]
  ): Promise<void>

  private async executeTurn(
    systemPrompt: string,
    messages: Anthropic.MessageParam[],
    turnCount: number
  ): Promise<{
    response: Anthropic.Message;
    toolCalls: Anthropic.Messages.ToolUseBlock[];
  }>

  private async executeToolCalls(
    toolCalls: Anthropic.Messages.ToolUseBlock[]
  ): Promise<Anthropic.Messages.ToolResultBlockParam[]>

  private async handleContextLengthError(
    error: Error,
    messages: Anthropic.MessageParam[],
    originalHistory: Anthropic.MessageParam[],
    currentPrompt: string,
    attempt: number
  ): Promise<{
    success: boolean;
    messages?: Anthropic.MessageParam[];
  }>
}
```

**Events Emitted:**

- `thinking`: `{ text: string }`
- `tool_call`: `{ id: string, name: string, description: string }`
- `tool_complete`: `{ toolId: string, elapsedMs: number, error?: boolean }`
- `tool_error`: `{ toolId: string, error: string }`
- `entities`: `{ entities: Entity[] }`
- `retry`: `{ attempt: number, delayMs: number, delaySeconds: number, message: string }`
- `context_truncated`: `{ attempt: number, originalCount: number, newCount: number, droppedCount: number, message: string }`
- `done`: `{ success: boolean, response?: string, usage?: Anthropic.Usage, turns?: number, error?: string }`

**Extracts:**

- Lines 709-1271 (agentic loop)
- Lines 842-880 (stream processing)
- Lines 887-912 (non-streaming call)
- Lines 915-927 (tool call extraction)
- Lines 1149-1264 (tool execution)
- Turn management
- Retry logic (via withRetry integration)

### Phase 3: Extract Strategies

#### 3.1 ContextTruncationStrategy

**File:** `app/server/strategies/ContextTruncationStrategy.ts`

```typescript
export interface ContextTruncationStrategy {
  truncate(
    originalHistory: Anthropic.MessageParam[],
    attempt: number
  ): Anthropic.MessageParam[];
}

export class ProgressiveTrimStrategy implements ContextTruncationStrategy {
  truncate(
    originalHistory: Anthropic.MessageParam[],
    attempt: number
  ): Anthropic.MessageParam[] {
    // Implements current getProgressivelyTrimmedHistory logic
  }

  private hasToolResults(message: Anthropic.MessageParam): boolean {
    // Moved from standalone function
  }
}
```

**Extracts:**

- Lines 77-126 (getProgressivelyTrimmedHistory)
- Lines 62-75 (hasToolResults)

### Phase 4: Extract SSE Manager

#### 4.1 SSEStreamManager

**File:** `app/server/stream/SSEStreamManager.ts`

```typescript
export class SSEStreamManager {
  private streamClosed = false;
  private encoder = new TextEncoder();

  constructor(
    private controller: ReadableStreamDefaultController
  ) {}

  pushEvent(eventType: string, data: any): void {
    if (this.streamClosed) return;
    const message = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
    this.controller.enqueue(this.encoder.encode(message));
  }

  keepalive(): void {
    if (this.streamClosed) return;
    this.controller.enqueue(this.encoder.encode(':\n\n'));
  }

  close(): void {
    if (!this.streamClosed) {
      this.streamClosed = true;
      this.controller.close();
    }
  }

  isClosed(): boolean {
    return this.streamClosed;
  }
}
```

**Extracts:**

- Lines 645-654 (pushEvent logic)
- Lines 658 (keepalive)
- Stream close logic

### Phase 5: Extract Utilities

#### 5.1 ErrorUtils

**File:** `app/server/utils/errorUtils.ts`

```typescript
export function extractErrorMessage(error: any): string {
  // Handles nested Anthropic error structures
}

export function isContextLengthError(error: any): boolean {
  return (
    error?.status === 413 ||
    error?.error?.message?.toLowerCase().includes("prompt is too long") ||
    error?.message?.toLowerCase().includes("prompt is too long")
  );
}
```

**Extracts:**

- Lines 77-99 (extractErrorMessage)
- Lines 759-764 (context length error detection)

### Phase 6: Thin Controller (Main Handler)

**File:** `app/server/api/query.post.ts` (refactored to ~150-200 lines)

**Structure:**

```typescript
export default defineEventHandler(async (event) => {
  // 1. Setup (logger, session) - ~15 lines

  // 2. Request validation - ~10 lines

  // 3. Initialize services (DI) - ~20 lines

  // 4. Conversation setup - ~15 lines

  // 5. Initialize AI client - ~10 lines

  // 6. Setup SSE - ~5 lines

  // 7. Create and return stream - ~80 lines
});

function createQueryStream(params: QueryStreamParams): ReadableStream {
  return new ReadableStream({
    async start(controller) {
      // Stream setup - ~10 lines
      // Service initialization - ~15 lines
      // Event listener setup - ~50 lines (declarative)
      // Execute agent - ~5 lines
    }
  });
}
```

**Event Listener Pattern (Declarative):**

```typescript
agent.on('thinking', ({ text }) => {
  sse.pushEvent('thinking', { text });
  thinkingSteps.push({ type: 'thinking', content: text });
  const entities = entityExtractor.extract(text);
  if (entities.length > 0) {
    allEntities.push(...entities);
    sse.pushEvent('entities', { entities });
  }
});

agent.on('done', async ({ success, response, usage, turns }) => {
  if (success && response) {
    // Save messages
    await conversationService.saveMessages(...);
    // Generate title if first exchange
    // Send done event
  }
  sse.close();
});
```

## File Structure After Refactoring

```
app/server/
├── api/
│   └── query.post.ts          (~150-200 lines) - Thin controller
├── services/
│   ├── ConversationService.ts (~150 lines)
│   ├── SystemPromptBuilder.ts (~130 lines)
│   └── EntityExtractor.ts     (~40 lines)
├── orchestrator/
│   └── QueryAgent.ts          (~300 lines)
├── strategies/
│   └── ContextTruncationStrategy.ts (~80 lines)
├── stream/
│   └── SSEStreamManager.ts    (~50 lines)
└── utils/
    └── errorUtils.ts          (~30 lines)
```

## Implementation Order

### Step 1: Extract Utilities (Lowest Risk)

- [x] Create `app/server/utils/errorUtils.ts`
- [x] Move `extractErrorMessage` and `isContextLengthError`
- [x] Update imports in query.post.ts

### Step 2: Extract Entity Extractor

- [x] Create `app/server/services/EntityExtractor.ts`
- [x] Move `extractEntities` and `URN_PATTERN`
- [x] Add unit tests
- [x] Update imports

### Step 3: Extract Context Truncation Strategy

- [x] Create `app/server/strategies/ContextTruncationStrategy.ts`
- [x] Move `getProgressivelyTrimmedHistory` and `hasToolResults`
- [x] Add unit tests
- [x] Update imports

### Step 4: Extract SSE Manager

- [x] Create `app/server/stream/SSEStreamManager.ts`
- [x] Extract SSE logic
- [x] Add unit tests
- [x] Integrate into query.post.ts

### Step 5: Extract System Prompt Builder

- [x] Create `app/server/services/SystemPromptBuilder.ts`
- [x] Move `buildSystemPrompt` logic
- [x] Add unit tests
- [x] Update imports

### Step 6: Extract Conversation Service

- [x] Create `app/server/services/ConversationService.ts`
- [x] Move conversation CRUD, message saving, title generation
- [x] Add unit tests
- [x] Update imports

### Step 7: Create Query Agent

- [x] Create `app/server/orchestrator/QueryAgent.ts`
- [x] Extract agentic loop with EventEmitter
- [x] Add unit tests
- [x] Integrate into query.post.ts

### Step 8: Refactor Main Handler

- [x] Reduce to thin controller pattern
- [x] Setup dependency injection
- [x] Setup event listeners
- [x] Verify all functionality preserved

### Step 9: Testing & Validation

- [x] Unit tests for all services
- [x] Integration tests for complete flow
- [x] Manual testing with UI
- [x] Performance testing
- [x] Error scenario testing

### Step 10: Documentation & Cleanup

- [x] Update API documentation
- [x] Add JSDoc comments
- [x] Remove dead code
- [x] Update README if needed

## Testing Strategy

### Unit Tests

Each service/class should have unit tests:

**ConversationService:**

- Creating conversations
- Getting conversations (ownership validation)
- Saving messages with metadata
- Generating titles
- Updating metadata

**SystemPromptBuilder:**

- Successful stats fetch
- Fallback on error
- Prompt formatting

**EntityExtractor:**

- Extract single entity
- Extract multiple entities
- Deduplicate entities
- Handle no entities

**ContextTruncationStrategy:**

- Progressive trimming levels
- Tool result orphan removal
- Edge cases (empty history, single message)

**SSEStreamManager:**

- Push event
- Keepalive
- Close stream
- Prevent events after close

**QueryAgent:**

- Turn execution
- Tool execution
- Event emission
- Context truncation handling
- Max turns handling

### Integration Tests

**Full Query Flow:**

- New conversation creation
- Conversation resumption
- Tool execution
- Entity extraction
- Title generation
- Error handling

## Benefits After Refactoring

✅ **Testability**

- Each service can be unit tested with mocks
- No need for complex test setup
- Isolated behavior testing

✅ **Reusability**

- Services can be used in other endpoints
- ConversationService for chat history API
- SystemPromptBuilder for other AI endpoints

✅ **Maintainability**

- Clear separation of concerns
- Easy to find and fix bugs
- Reduced cognitive load

✅ **Flexibility**

- Easy to swap implementations
- Different truncation strategies
- Different SSE managers

✅ **Debugging**

- Isolated components
- Clear event flow
- Better logging

✅ **Extensibility**

- Add new event listeners without core changes
- Add new services without touching existing code
- Plugin-style architecture

## Risks & Mitigations

### Risk 1: Breaking Existing Functionality

**Mitigation:**

- Incremental refactoring with tests
- Feature flags if needed
- Comprehensive integration tests
- Manual testing before merge

### Risk 2: Performance Regression

**Mitigation:**

- Benchmark before/after
- Profile event emission overhead
- Optimize if needed

### Risk 3: Increased Complexity (More Files)

**Mitigation:**

- Clear naming and structure
- Good documentation
- Logical file organization
- Benefits outweigh cost

### Risk 4: Breaking Type Safety

**Mitigation:**

- Strict TypeScript throughout
- Proper interfaces for all services
- No `any` types (except where unavoidable with Anthropic SDK)

## Success Criteria

- [ ] Main handler reduced to <200 lines
- [ ] All services extracted with unit tests
- [ ] QueryAgent with event emitter pattern
- [ ] 80%+ test coverage on new code
- [ ] All existing functionality preserved
- [ ] No breaking changes to API contract
- [ ] Integration tests passing
- [ ] Manual testing successful
- [ ] Performance within 5% of baseline
- [ ] Code review approved

## Timeline Estimate

- **Step 1-4:** 2-3 hours (utilities, simple services)
- **Step 5-6:** 3-4 hours (complex services with DB)
- **Step 7:** 4-5 hours (QueryAgent - most complex)
- **Step 8:** 2-3 hours (refactor main handler)
- **Step 9:** 3-4 hours (comprehensive testing)
- **Step 10:** 1-2 hours (documentation)

**Total:** ~15-21 hours of focused work

## Related Issues

- Issue #18: This refactoring
- PR will reference #18 when complete

## Notes

- Keep all changes backward compatible
- No changes to API contract (request/response format)
- No changes to SSE event format (frontend depends on it)
- Preserve all existing error handling behavior
- Maintain retry logic for 429 errors
- Keep context truncation behavior identical
