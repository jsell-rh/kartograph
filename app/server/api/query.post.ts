/**
 * POST /api/query
 *
 * Natural language query endpoint using Anthropic Messages API
 * to translate questions into Dgraph queries via custom tools.
 *
 * Streams responses via Server-Sent Events (SSE).
 */

import Anthropic from "@anthropic-ai/sdk";
import AnthropicVertex from "@anthropic-ai/vertex-sdk";
import { dgraphTools, executeTool } from "../lib/dgraph-tools";
import { setResponseStatus, setHeader, sendStream } from "h3";
import { createRequestLogger, truncateForLog } from "../lib/logger";
import { withRetry } from "../lib/retry";
import { getSession } from "../utils/auth";
import { db } from "../db";
import {
  conversations,
  messages as messagesTable,
  type ThinkingStep,
} from "../db/schema";
import { eq, and } from "drizzle-orm";

// Entity extraction regex
const URN_PATTERN = /<urn:([^:]+):([^>]+)>/g;

interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

/**
 * Extract entities from assistant message text
 */
function extractEntities(text: string): Entity[] {
  const entities: Entity[] = [];
  const matches = text.matchAll(URN_PATTERN);

  for (const match of matches) {
    const [fullUrn, type, id] = match;
    if (!fullUrn || !type || !id) continue;
    entities.push({
      urn: fullUrn,
      type,
      id,
      displayName: id.replace(/-/g, " ").replace(/_/g, " "),
    });
  }

  // Deduplicate by URN
  const uniqueEntities = entities.filter(
    (entity, index, self) =>
      index === self.findIndex((e) => e.urn === entity.urn),
  );

  return uniqueEntities;
}

/**
 * Check if a message contains tool_result blocks
 */
function hasToolResults(message: Anthropic.MessageParam): boolean {
  if (message.role !== "user") return false;

  const content = message.content;
  if (typeof content === "string") return false;

  return (
    Array.isArray(content) &&
    content.some((block: any) => block.type === "tool_result")
  );
}

/**
 * Progressive context truncation for handling prompt length errors
 * Returns trimmed message history in decreasing sizes: full → half → quarter → recent 5 → recent 2 → empty
 *
 * IMPORTANT: Ensures tool_use/tool_result pairing is preserved by removing orphaned tool_result messages
 * that would reference tool_use blocks that were truncated.
 */
function getProgressivelyTrimmedHistory(
  originalHistory: Anthropic.MessageParam[],
  attempt: number,
): Anthropic.MessageParam[] {
  const historyLength = originalHistory.length;

  let trimmed: Anthropic.MessageParam[];

  switch (attempt) {
    case 0:
      // First attempt: use full history
      trimmed = originalHistory;
      break;
    case 1:
      // Second attempt: keep last half
      trimmed = originalHistory.slice(-Math.ceil(historyLength / 2));
      break;
    case 2:
      // Third attempt: keep last quarter
      trimmed = originalHistory.slice(-Math.ceil(historyLength / 4));
      break;
    case 3:
      // Fourth attempt: keep last 5 messages
      trimmed = originalHistory.slice(-5);
      break;
    case 4:
      // Fifth attempt: keep last 2 messages
      trimmed = originalHistory.slice(-2);
      break;
    default:
      // Final attempt: no history, just current prompt
      return [];
  }

  // Remove orphaned tool_result messages at the start
  // If first message is a user message with tool_results, it references tool_use blocks
  // that were truncated, so we must remove it to avoid API errors
  while (trimmed.length > 0 && trimmed[0] && hasToolResults(trimmed[0])) {
    trimmed = trimmed.slice(1);
  }

  return trimmed;
}

/**
 * Build system prompt with current graph statistics
 */
async function buildSystemPrompt(config: any, logger: any): Promise<string> {
  try {
    // Fetch current graph statistics directly from Dgraph
    const dgraphUrl = config.dgraphUrl;

    // Query to get entity counts by type
    const statsQuery = `
      {
        byType(func: has(type)) {
          type
          count(uid)
        }
      }
    `;

    const statsResponse = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: statsQuery,
    });

    if (!statsResponse.ok) {
      throw new Error(`Dgraph stats query failed: ${statsResponse.status}`);
    }

    const statsData = await statsResponse.json();

    // Extract counts by type
    const typeCounts: Record<string, number> = {};
    let totalEntities = 0;

    if (statsData.data?.byType) {
      for (const item of statsData.data.byType) {
        const type = item.type;
        if (type) {
          typeCounts[type] = (typeCounts[type] || 0) + 1;
          totalEntities++;
        }
      }
    }

    // Get schema (all predicates)
    const schemaQuery = `schema {}`;
    const schemaResponse = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: schemaQuery,
    });

    if (!schemaResponse.ok) {
      throw new Error(`Dgraph schema query failed: ${schemaResponse.status}`);
    }

    const schemaData = await schemaResponse.json();

    // Extract predicates from schema
    const predicates: string[] = [];
    if (schemaData.data?.schema) {
      for (const predicate of schemaData.data.schema) {
        if (predicate.predicate && !predicate.predicate.startsWith("dgraph.")) {
          predicates.push(predicate.predicate);
        }
      }
    }

    // Format entity types with counts
    const entityTypesFormatted = Object.entries(typeCounts)
      .sort(([, a], [, b]) => b - a)
      .map(([type, count]) => `- ${type} (${count})`)
      .join("\n");

    // Format predicates in a compact way
    const predicatesFormatted = predicates.sort().join(", ");

    logger.debug(
      {
        totalEntities,
        typeCount: Object.keys(typeCounts).length,
        predicateCount: predicates.length,
      },
      "Built system prompt with graph stats",
    );

    return `You are an expert graph database analyst and natural language query specialist with deep expertise in Dgraph, DQL (Dgraph Query Language),
and translating complex business questions into precise database queries. Your role is to serve as an intelligent interface between users and
a Dgraph database, making graph data accessible through natural conversation.

## Your Database Environment

You work with a Dgraph knowledge graph containing:
- **${totalEntities} total entities** across **${Object.keys(typeCounts).length} entity types**
- Service topology, dependencies, ownership, and infrastructure metadata
- Proxy endpoints and their routing to services
- **${predicates.length} relationship and property types (predicates)**

You access this data through the **query_dgraph tool** which executes DQL queries and returns results.

### Entity Types in This Graph

${entityTypesFormatted}

### Available Predicates (Properties and Relationships)

The following ${predicates.length} predicates are available in the graph:

${predicatesFormatted}`;
  } catch (error) {
    logger.warn(
      { error: error instanceof Error ? error.message : String(error) },
      "Failed to fetch stats for prompt, using static fallback",
    );

    // Fallback to static prompt if stats fetch fails
    return `You are an expert graph database analyst and natural language query specialist with deep expertise in Dgraph, DQL (Dgraph Query Language),
and translating complex business questions into precise database queries. Your role is to serve as an intelligent interface between users and
a Dgraph database, making graph data accessible through natural conversation.

## Your Database Environment

You work with a Dgraph knowledge graph containing approximately:
- 6,441 entities across 34 types (Services, Namespaces, Routes, Users, Roles, AWS Accounts, etc.)
- Service topology, dependencies, ownership, and infrastructure metadata
- Proxy endpoints and their routing to services

You access this data through the **query_dgraph tool** which executes DQL queries and returns results.`;
  }
}

/**
 * System prompt continuation (common to all prompts)
 */
const SYSTEM_PROMPT_CONTINUATION = `

## Your Core Workflow

### Step 1: Question Decomposition
When a user asks a question, systematically identify:
- **Primary entities**: What are they asking about? (services, applications, endpoints, teams)
- **Desired information**: What specific data do they need? (ownership, URLs, dependencies, contacts)
- **Relationships**: What connections need to be traversed? (depends on, has endpoint, owned by)
- **Filters**: Are there constraints? (name patterns, types, statuses)
- **Context**: What's the underlying need? (troubleshooting, contact info, impact analysis)

### Step 2: Query Construction
Build DQL queries using the query_dgraph tool. **Key principles:**

#### ALWAYS Use Case-Insensitive Partial Matching
- **PRIMARY STRATEGY**: Use \`regexp()\` with \`/i\` flag for all name searches
- **AVOID** exact \`eq()\` matching on names - it's case-sensitive and brittle
- Names vary in casing: "Cincinnati" vs "cincinnati", "TelemeterServer" vs "telemeter-server"

\`\`\`dql
# ✅ GOOD - case-insensitive partial match
{
  services(func: eq(type, "Application"))
    @filter(regexp(name, /cincinnati/i)) {
    name
    ownedBy
  }
}
\`\`\`

#### Search Patterns (Ranked by Usefulness)

1. **Partial/fuzzy matching (USE FIRST):**
   - \`@filter(regexp(name, /pattern/i))\` - Case-insensitive text patterns
   - \`func: anyoftext(name, "search words")\` - Word-based search
   - Always include \`/i\` flag for case insensitivity

2. **Type-based filtering:**
   - Start broad: \`func: eq(type, "Application")\`
   - Then narrow with regexp filters

3. **Relationship traversal:**
   - Follow edges: \`hasEndpoint { ... }\`
   - Reverse lookup: \`~ownedBy { ... }\`

4. **Path/URL matching:**
   - For endpoints, use regexp for partial paths: \`/api/upgrades_info\` matches \`/api/upgrades_info/graph-data\`
   - Pattern: \`func: eq(type, "Endpoint") @filter(regexp(path, /upgrades_info/i))\`

### Step 3: Query Execution
Use the query_dgraph tool with:
- \`dql\`: Your complete DQL query as a string
- \`description\`: Brief explanation of what you're searching for

### Step 4: Handle Empty Results Intelligently
**CRITICAL**: Empty results ≠ connectivity issues!

When you get no results:
- The query executed successfully - the data just doesn't exist
- **DO NOT** say "connectivity issues" or "database problems"
- **DO** try alternative searches:
  - Broader regexp patterns
  - Related entity types (search routes/endpoints if service not found)
  - Name variations (abbreviations, with/without prefixes)
  - Check for typos or alternative spellings

### Step 5: Make Results Explorable with Interactive URNs

**CRITICAL FOR FRONTEND INTERACTIVITY**: Always format entity mentions as clickable URNs using this exact syntax:
\`\`\`
<urn:EntityType:entity-name>
\`\`\`

This enables users to click entities in your response and visually explore the knowledge graph.

#### How to Transform Dgraph Results into URNs

When query_dgraph returns results, follow this transformation process:

**1. Identify the entity's name field:**
   - Could be \`name\`, \`service_name\`, \`route_name\`, \`namespace_name\`, etc.
   - Use whatever name field exists in the result

**2. Identify the entity's type:**
   - Look for \`type\` field in the result
   - Or infer from query context (querying Applications → type is "Application")

**3. Format as URN:**
   - Pattern: \`<urn:Type:exact-name-from-result>\`
   - Use the EXACT name value from the result
   - Use the proper capitalized type (Application, Route, Namespace, etc.)

#### URN Best Practices

✅ **DO:**
- Use entity names from results, not hex UIDs
- Include URNs for ALL entities mentioned in your response
- Use proper entity type capitalization (Application, not application)
- Include URNs in tables, lists, and prose

❌ **DON'T:**
- Don't use hex UIDs: \`<0x123abc>\` ❌
- Don't invent entity names not in the result
- Don't skip URN formatting for "minor" entities
- Don't use lowercase types: \`<urn:application:foo>\` ❌

#### Why This Matters

Every URN you format becomes an interactive node in the frontend:
- Users can click to view the entity in the graph explorer
- Reveals relationships and properties visually
- Enables navigation through the knowledge graph
- Transforms static text into an explorable data experience

**Make every response explorable by liberally using URN formatting!**

### Step 6: Intelligent Response Generation
Present findings in a clear, actionable format:

- **Use tables** for structured data (services, endpoints, owners)
- **Highlight key information**: owners, contact details, critical paths
- **Provide context**: explain what the data means for the user's situation
- **Include actionable next steps**: who to contact, what to check
- **Be honest about gaps**: if data is missing, explain what's not available

## Key Predicates You'll Use Frequently

- **Identity**: \`name\`, \`type\`
- **Ownership**: \`ownedBy\`, \`ownerName\`
- **URLs**: \`fullUrl\`, \`serverUrl\`, \`consoleUrl\`
- **Paths**: \`path\`, \`host\`
- **JIRA**: \`hasJiraProject\`, \`hasJiraComponent\`
- **Relationships**: \`dependsOn\`, \`hasEndpoint\`, \`servedBy\`, \`routedBy\`
- **Communication**: \`slackChannel\`
- **Namespaces**: \`hasNamespace\`, \`cluster\`

## Creative Exploration Strategy

General Form to Minimize Queries

  1. Start Broad, Then Drill Down

  Bad:  Query for service name → Query for owner → Query for dependencies → Query for namespaces
  Good: Single query getting service with ALL predicates (name, owner, dependencies, namespaces)

  2. Use Recursive/Traversal Queries Upfront

  Bad:  Get entity → Get its dependencies → For each dependency, get details
  Good: Single query with nested blocks traversing relationships and fetching details

  3. Request Multiple Entity Types in Parallel

  Bad:  Query for ROSA services → Query for ROSA namespaces → Query for ROSA accounts
  Good: Single query with multiple root blocks for each entity type pattern

  4. Get Counts Before Fetching Details

  Good: Count entities by type first → Decide which types to explore → Fetch details

  5. Follow Relationships Bidirectionally in One Query

  Good: Query both "X depends on Y" AND "what depends on X" in same query

  Optimal Query Structure Pattern

  {
    # Part 1: Get target entities with ALL predicates
    entities(func: ...) {
      uid
      expand(_all_) {  # Get everything at once
        uid
        expand(_all_)  # Follow relationships 1-2 levels deep
      }
    }

    # Part 2: Get related entities by pattern in parallel
    related_type1(func: ...) { ... }
    related_type2(func: ...) { ... }

    # Part 3: Reverse lookups
    what_depends_on_this(func: ...) @filter(...) { ... }

    # Part 4: Counts for context
    counts(func: has(dgraph.type)) {
      count(uid)
    }
  }

  What I Learned From My Queries

  ❌ Inefficient Approach (What I Did Initially)

  1. Query for backplane entities
  2. Query for ROSA entities
  3. Query for dependencies of ROSA
  4. Query specific UIDs one by one
  5. Try to find paths between them
  6. Query in reverse direction
  7. Expand to related patterns

  Result: 7+ separate agent invocations

  ✅ Efficient Approach (What I Should Have Done)

  Single comprehensive query:
  - Get all ROSA entities with full details + dependencies expanded
  - Get all backplane entities with full details + reverse dependencies
  - Get entity type counts
  - Find shortest paths between them
  - Get shared infrastructure (AWS accounts, clusters, namespaces)

  Result: 1-2 agent invocations maximum

**Remember**: The goal is to answer the user's question, not to find exact entity matches. Be creative and persistent!

## Response Format

Use professional, concise prose. No emojis or sycophancy. Be direct and use active voice.

You are proactive, precise, and focused on delivering actionable answers. You understand that behind every question is a person trying to solve a problem—your job is to give them exactly what they need to move forward.
`;

export default defineEventHandler(async (event) => {
  const startTime = Date.now();

  // Create request-scoped logger with correlation ID
  const { logger: log, correlationId } = createRequestLogger("query-api");

  try {
    // Get authenticated user
    const session = await getSession(event);
    if (!session?.user?.id) {
      throw createError({
        statusCode: 401,
        message: "Unauthorized",
      });
    }

    const userId = session.user.id;

    // Parse request body
    const body = await readBody(event);
    const { prompt, conversationHistory = [], conversationId } = body;

    log.info(
      {
        promptLength: prompt?.length || 0,
        promptPreview: truncateForLog(prompt, 100),
        historyLength: conversationHistory?.length || 0,
        conversationId: conversationId || "new",
        userId,
        correlationId,
      },
      "Received query request",
    );

    if (!prompt || typeof prompt !== "string") {
      throw createError({
        statusCode: 400,
        message: "Missing or invalid prompt",
      });
    }

    // Handle conversation persistence
    let activeConversationId = conversationId;

    if (conversationId) {
      // Verify user owns the conversation
      const existing = await db
        .select()
        .from(conversations)
        .where(
          and(
            eq(conversations.id, conversationId),
            eq(conversations.userId, userId),
          ),
        )
        .limit(1);

      if (!existing || existing.length === 0) {
        throw createError({
          statusCode: 404,
          message: "Conversation not found",
        });
      }

      log.debug({ conversationId }, "Using existing conversation");
    } else {
      // Create new conversation
      activeConversationId = crypto.randomUUID();
      const now = new Date();

      await db.insert(conversations).values({
        id: activeConversationId,
        userId,
        title: "New Conversation", // Will be updated with auto-naming later
        messageCount: 0,
        isArchived: false,
        createdAt: now,
        updatedAt: now,
      });

      log.info(
        { conversationId: activeConversationId },
        "Created new conversation",
      );
    }

    // Validate and sanitize conversation history
    const MAX_HISTORY_MESSAGES = 20; // Limit to prevent token overflow
    const sanitizedHistory: Anthropic.MessageParam[] = (
      conversationHistory || []
    )
      .slice(-MAX_HISTORY_MESSAGES) // Keep last N messages
      .filter(
        (msg: any) =>
          msg.role && msg.content && typeof msg.content === "string",
      )
      .map((msg: any) => ({
        role: msg.role,
        content: msg.content,
      }));

    // Log full user message
    log.debug(
      {
        userMessage: prompt,
        messageLength: prompt.length,
        historyMessages: sanitizedHistory.length,
      },
      "User message content",
    );

    // Get runtime config
    const config = useRuntimeConfig(event);

    // Check for either VertexAI or Anthropic configuration
    const hasVertexAI = config.vertexProjectId && config.vertexRegion;
    const hasAnthropic = config.anthropicApiKey;

    if (!hasVertexAI && !hasAnthropic) {
      throw createError({
        statusCode: 500,
        message:
          "Neither VertexAI (VERTEX_PROJECT_ID, VERTEX_REGION) nor ANTHROPIC_API_KEY configured",
      });
    }

    log.info(
      {
        hasVertexAI,
        hasAnthropic,
        vertexProjectId: hasVertexAI ? config.vertexProjectId : "not set",
        vertexRegion: hasVertexAI ? config.vertexRegion : "not set",
      },
      "AI provider configuration",
    );

    // Initialize Anthropic client with VertexAI or direct API
    const anthropic: Anthropic | AnthropicVertex = hasVertexAI
      ? new AnthropicVertex({
          projectId: config.vertexProjectId,
          region: config.vertexRegion,
        })
      : new Anthropic({
          apiKey: config.anthropicApiKey,
        });

    // Set up SSE headers
    log.debug("Setting up SSE headers");
    setResponseStatus(event, 200);
    setHeader(event, "Content-Type", "text/event-stream");
    setHeader(event, "Cache-Control", "no-cache");
    setHeader(event, "Connection", "keep-alive");

    log.debug("Creating response stream");

    // Create a manual event stream
    let streamClosed = false;
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        // Helper to push SSE formatted data
        const pushEvent = (eventType: string, data: any) => {
          if (streamClosed) return;
          const message = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
          controller.enqueue(encoder.encode(message));
        };

        try {
          // Send keepalive
          controller.enqueue(encoder.encode(":\n\n"));
          log.info("SSE connection established");

          // Build system prompt with current graph stats
          const systemPromptHeader = await buildSystemPrompt(config, log);
          const fullSystemPrompt =
            systemPromptHeader + SYSTEM_PROMPT_CONTINUATION;

          log.debug(
            {
              systemPromptLength: fullSystemPrompt.length,
              systemPromptPreview: fullSystemPrompt.substring(0, 200),
            },
            "System prompt built",
          );

          // Track all extracted entities
          const allEntities: Entity[] = [];

          // Track assistant's response text for database persistence
          let assistantResponseText = "";
          let assistantThinkingSteps: ThinkingStep[] = [];
          let currentToolCallStep: ThinkingStep | null = null;

          // Conversation history (messages back and forth with Claude)
          // Include previous conversation context + new prompt
          // Keep track of initial history length for context truncation on 413 errors
          let currentHistoryTrimLevel = 0; // 0 = full history, increases on 413 errors
          const initialHistoryLength = sanitizedHistory.length;

          const messages: Anthropic.MessageParam[] = [
            ...sanitizedHistory,
            {
              role: "user",
              content: prompt,
            },
          ];

          log.debug(
            {
              initialMessageCount: messages.length,
              historyCount: sanitizedHistory.length,
              conversationStart: sanitizedHistory.length === 0,
            },
            "Starting conversation with history",
          );

          // Agentic loop - keep calling Claude until it stops requesting tools
          let turnCount = 0;
          const maxTurns = 50;

          while (turnCount < maxTurns) {
            turnCount++;
            log.info(
              {
                turn: turnCount,
                maxTurns,
                messageCount: messages.length,
              },
              "Starting turn",
            );

            // Determine model identifier
            const model = hasVertexAI
              ? "claude-sonnet-4-5@20250929"
              : "claude-sonnet-4-20250514";

            // Wrap API call with context length error handling
            let stream: any;
            let contextTruncationAttempt = 0;
            const maxContextTruncationAttempts = 6;

            while (contextTruncationAttempt < maxContextTruncationAttempts) {
              try {
                // Call Claude with streaming (with retry on 429)
                stream = await withRetry(
                  () =>
                    (anthropic as any).messages.create({
                      model,
                      max_tokens: 8000,
                      system: fullSystemPrompt,
                      messages,
                      tools: dgraphTools,
                      stream: true,
                    }),
                  `anthropic-stream-turn-${turnCount}`,
                  log,
                  async (attempt, delayMs) => {
                    // Send retry event to frontend
                    const delaySeconds = Math.ceil(delayMs / 1000);
                    pushEvent("retry", {
                      attempt,
                      delayMs,
                      delaySeconds,
                      message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
                    });
                  },
                );
                break; // Success, exit retry loop
              } catch (error: any) {
                // Check if this is a context length error (413 or "prompt is too long")
                const isContextError =
                  error?.status === 413 ||
                  error?.error?.message
                    ?.toLowerCase()
                    .includes("prompt is too long") ||
                  error?.message?.toLowerCase().includes("prompt is too long");

                if (
                  isContextError &&
                  contextTruncationAttempt < maxContextTruncationAttempts - 1
                ) {
                  contextTruncationAttempt++;
                  currentHistoryTrimLevel = contextTruncationAttempt;

                  // Get trimmed history
                  const trimmedHistory = getProgressivelyTrimmedHistory(
                    sanitizedHistory,
                    contextTruncationAttempt,
                  );

                  log.warn(
                    {
                      turn: turnCount,
                      attempt: contextTruncationAttempt,
                      originalHistoryLength: initialHistoryLength,
                      trimmedHistoryLength: trimmedHistory.length,
                      droppedMessages:
                        initialHistoryLength - trimmedHistory.length,
                    },
                    "Context length exceeded, trimming history",
                  );

                  // Notify frontend of context truncation
                  pushEvent("context_truncated", {
                    attempt: contextTruncationAttempt,
                    originalCount: initialHistoryLength,
                    newCount: trimmedHistory.length,
                    droppedCount: initialHistoryLength - trimmedHistory.length,
                    message:
                      trimmedHistory.length === 0
                        ? "Conversation too long. Using only current message (history cleared)."
                        : `Conversation too long. Dropped ${initialHistoryLength - trimmedHistory.length} older messages to fit context.`,
                  });

                  // Rebuild messages array with trimmed history
                  // Keep: trimmed history + current prompt + accumulated session messages
                  const sessionMessagesStart = initialHistoryLength + 1; // After original history + prompt
                  const sessionMessages = messages.slice(sessionMessagesStart);

                  // Rebuild messages array
                  messages.length = 0; // Clear array
                  messages.push(...trimmedHistory);
                  messages.push({ role: "user", content: prompt });
                  messages.push(...sessionMessages);

                  log.info(
                    {
                      rebuiltMessageCount: messages.length,
                      historyCount: trimmedHistory.length,
                      sessionMessageCount: sessionMessages.length,
                    },
                    "Rebuilt messages with trimmed history",
                  );

                  // Continue to next retry attempt
                  continue;
                } else {
                  // Not a context error or exhausted retries, rethrow
                  throw error;
                }
              }
            }

            if (!stream) {
              throw new Error(
                "Failed to create stream after context truncation retries",
              );
            }

            let currentText = "";
            let currentToolCalls: Anthropic.Messages.ToolUseBlock[] = [];

            // Process stream
            for await (const chunk of stream) {
              if (chunk.type === "content_block_start") {
                if (chunk.content_block.type === "text") {
                  // Text block starting
                  log.debug("Text block started");
                } else if (chunk.content_block.type === "tool_use") {
                  // Tool use block starting
                  log.debug(
                    {
                      toolId: chunk.content_block.id,
                      toolName: chunk.content_block.name,
                    },
                    "Tool use block started",
                  );
                }
              } else if (chunk.type === "content_block_delta") {
                if (chunk.delta.type === "text_delta") {
                  // Stream text to client
                  const delta = chunk.delta.text;
                  currentText += delta;
                  pushEvent("text", { delta });
                } else if (chunk.delta.type === "input_json_delta") {
                  // Tool input is being streamed (we'll handle complete tool call later)
                  log.debug(
                    { partial: chunk.delta.partial_json },
                    "Tool input delta",
                  );
                }
              } else if (chunk.type === "content_block_stop") {
                log.debug({ index: chunk.index }, "Content block stopped");
              } else if (chunk.type === "message_delta") {
                log.debug(
                  { stopReason: chunk.delta.stop_reason },
                  "Message delta",
                );
              } else if (chunk.type === "message_stop") {
                log.debug("Message stopped");
              }
            }

            // After stream completes, get the complete message
            // We need to reconstruct it from what we know
            // OR we can make a non-streaming call to get the complete message
            // For now, let's use non-streaming to get tool calls

            // Make non-streaming call to get complete message with tool calls (with retry on 429)
            // Note: Context truncation already handled in streaming call above,
            // so this call should succeed with the same trimmed messages array
            const response = await withRetry<Anthropic.Message>(
              () =>
                (anthropic as any).messages.create({
                  model,
                  max_tokens: 8000,
                  system: fullSystemPrompt,
                  messages,
                  tools: dgraphTools,
                  stream: false,
                }),
              `anthropic-complete-turn-${turnCount}`,
              log,
              async (attempt, delayMs) => {
                // Send retry event to frontend
                const delaySeconds = Math.ceil(delayMs / 1000);
                pushEvent("retry", {
                  attempt,
                  delayMs,
                  delaySeconds,
                  message: `Rate limit hit. Retrying in ${delaySeconds}s... (attempt ${attempt})`,
                });
              },
            );

            // Extract tool calls
            currentToolCalls = response.content.filter(
              (
                block: Anthropic.Messages.ContentBlock,
              ): block is Anthropic.Messages.ToolUseBlock =>
                block.type === "tool_use",
            );

            // Extract text content
            const textBlocks = response.content.filter(
              (
                block: Anthropic.Messages.ContentBlock,
              ): block is Anthropic.Messages.TextBlock => block.type === "text",
            );
            const fullText = textBlocks
              .map((b: Anthropic.Messages.TextBlock) => b.text)
              .join("");

            // Log assistant response
            if (fullText) {
              log.debug(
                {
                  turn: turnCount,
                  responseLength: fullText.length,
                  responsePreview: truncateForLog(fullText, 200),
                  hasToolCalls: currentToolCalls.length > 0,
                },
                "Assistant response received",
              );

              // Track thinking steps and final response
              if (currentToolCalls.length > 0) {
                // This is a thinking step (has tool calls)
                assistantThinkingSteps.push({
                  type: "thinking",
                  content: fullText,
                });
              } else {
                // This is the final response (no tool calls)
                assistantResponseText = fullText;
              }

              pushEvent("thinking", { text: fullText });
              const entities = extractEntities(fullText);
              allEntities.push(...entities);

              if (entities.length > 0) {
                log.info(
                  {
                    turn: turnCount,
                    entitiesExtracted: entities.length,
                    entityTypes: [...new Set(entities.map((e) => e.type))],
                  },
                  "Entities extracted from response",
                );
                pushEvent("entities", { entities });
              }
            }

            // Add assistant message to history
            messages.push({
              role: "assistant",
              content: response.content,
            });

            // If no tool calls, we're done
            if (currentToolCalls.length === 0) {
              const elapsedSeconds = Math.floor(
                (Date.now() - startTime) / 1000,
              );

              log.info(
                {
                  turns: turnCount,
                  totalEntities: allEntities.length,
                  inputTokens: response.usage.input_tokens,
                  outputTokens: response.usage.output_tokens,
                  totalTokens:
                    response.usage.input_tokens + response.usage.output_tokens,
                  elapsedSeconds,
                },
                "Conversation complete",
              );

              // Save messages to database
              let savedUserMessageId: string | undefined;
              let savedAssistantMessageId: string | undefined;

              try {
                const messageTimestamp = new Date();

                // Save user message
                const userMessageId = crypto.randomUUID();
                savedUserMessageId = userMessageId;
                await db.insert(messagesTable).values({
                  id: userMessageId,
                  conversationId: activeConversationId,
                  role: "user",
                  content: prompt,
                  createdAt: messageTimestamp,
                });

                // Save assistant message
                const assistantMessageId = crypto.randomUUID();
                savedAssistantMessageId = assistantMessageId;
                await db.insert(messagesTable).values({
                  id: assistantMessageId,
                  conversationId: activeConversationId,
                  role: "assistant",
                  content: assistantResponseText,
                  thinkingSteps:
                    assistantThinkingSteps.length > 0
                      ? assistantThinkingSteps
                      : undefined,
                  entities: allEntities.length > 0 ? allEntities : undefined,
                  elapsedSeconds,
                  createdAt: messageTimestamp,
                });

                // Update conversation metadata
                // Count messages in this conversation (should be 2 after we just added user + assistant)
                const messageCountResult = await db
                  .select()
                  .from(messagesTable)
                  .where(
                    eq(messagesTable.conversationId, activeConversationId),
                  );

                await db
                  .update(conversations)
                  .set({
                    lastMessageAt: messageTimestamp,
                    messageCount: messageCountResult.length,
                    updatedAt: messageTimestamp,
                  })
                  .where(eq(conversations.id, activeConversationId));

                log.info(
                  {
                    conversationId: activeConversationId,
                    messageCount: messageCountResult.length,
                  },
                  "Messages saved to database",
                );

                // Auto-generate conversation title after first exchange
                if (messageCountResult.length === 2) {
                  try {
                    log.debug(
                      {
                        conversationId: activeConversationId,
                        userPrompt: prompt,
                      },
                      "Generating conversation title",
                    );

                    const titleResponse: Anthropic.Message = await (
                      anthropic as any
                    ).messages.create({
                      model: hasVertexAI
                        ? "claude-3-5-haiku@20241022"
                        : "claude-3-5-haiku-20241022",
                      max_tokens: 50,
                      messages: [
                        {
                          role: "user",
                          content: `Generate a concise, descriptive 3-5 word title for a conversation that starts with this question: "${prompt}"\n\nRespond with ONLY the title, no quotes or punctuation.`,
                        },
                      ],
                    });

                    const titleBlock = titleResponse.content.find(
                      (
                        block: Anthropic.Messages.ContentBlock,
                      ): block is Anthropic.Messages.TextBlock =>
                        block.type === "text",
                    );

                    if (titleBlock && titleBlock.text) {
                      const generatedTitle = titleBlock.text
                        .trim()
                        .replace(/^["']|["']$/g, "");

                      await db
                        .update(conversations)
                        .set({ title: generatedTitle })
                        .where(eq(conversations.id, activeConversationId));

                      log.info(
                        {
                          conversationId: activeConversationId,
                          generatedTitle,
                        },
                        "Auto-generated conversation title",
                      );
                    }
                  } catch (titleError) {
                    // Gracefully fail - keep "New Conversation" title
                    log.warn(
                      {
                        conversationId: activeConversationId,
                        error:
                          titleError instanceof Error
                            ? titleError.message
                            : String(titleError),
                      },
                      "Failed to auto-generate conversation title",
                    );
                  }
                }
              } catch (dbError) {
                log.error(
                  {
                    error:
                      dbError instanceof Error
                        ? dbError.message
                        : String(dbError),
                    conversationId: activeConversationId,
                  },
                  "Failed to save messages to database",
                );
              }

              pushEvent("done", {
                success: true,
                turns: turnCount,
                entities: allEntities,
                usage: response.usage,
                conversationId: activeConversationId,
                userMessageId: savedUserMessageId,
                assistantMessageId: savedAssistantMessageId,
              });
              break;
            }

            // Execute tool calls
            log.info(
              {
                toolCount: currentToolCalls.length,
                tools: currentToolCalls.map((t) => t.name),
              },
              "Executing tools",
            );
            const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

            for (const toolCall of currentToolCalls) {
              const toolStartTime = Date.now();
              const description =
                (toolCall.input as any).description || "Executing query...";

              // Log tool call details
              log.debug(
                {
                  toolId: toolCall.id,
                  toolName: toolCall.name,
                  toolInput: toolCall.input,
                  turn: turnCount,
                },
                "Tool call started",
              );

              // Create thinking step for this tool call
              const toolStep: ThinkingStep = {
                type: "tool_call",
                content: description,
                metadata: {
                  toolName: toolCall.name,
                  description,
                },
              };
              assistantThinkingSteps.push(toolStep);

              pushEvent("tool_call", {
                id: toolCall.id,
                name: toolCall.name,
                description,
              });

              try {
                const result = await executeTool(toolCall.name, toolCall.input);
                const toolElapsedMs = Date.now() - toolStartTime;

                // Log successful tool result
                log.info(
                  {
                    toolId: toolCall.id,
                    toolName: toolCall.name,
                    toolElapsedMs,
                    resultLength:
                      typeof result === "string"
                        ? result.length
                        : JSON.stringify(result).length,
                    resultPreview: truncateForLog(result, 200),
                  },
                  "Tool execution succeeded",
                );

                // Update tool step with timing
                toolStep.metadata!.timing = toolElapsedMs;

                // Send completion event with timing
                pushEvent("tool_complete", {
                  toolId: toolCall.id,
                  elapsedMs: toolElapsedMs,
                });

                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolCall.id,
                  content: result,
                });
              } catch (error) {
                const toolElapsedMs = Date.now() - toolStartTime;
                const errorMessage =
                  error instanceof Error ? error.message : "Unknown error";

                log.error(
                  {
                    toolId: toolCall.id,
                    toolName: toolCall.name,
                    toolElapsedMs,
                    error: errorMessage,
                    errorStack:
                      error instanceof Error ? error.stack : undefined,
                  },
                  "Tool execution failed",
                );

                // Update tool step with error
                toolStep.metadata!.timing = toolElapsedMs;
                toolStep.metadata!.error = errorMessage;

                // Send completion event with timing even on error
                pushEvent("tool_complete", {
                  toolId: toolCall.id,
                  elapsedMs: toolElapsedMs,
                  error: true,
                });

                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolCall.id,
                  content: `Error: ${errorMessage}`,
                  is_error: true,
                });
                pushEvent("tool_error", {
                  toolId: toolCall.id,
                  error: errorMessage,
                });
              }
            }

            // Add tool results to conversation
            messages.push({
              role: "user",
              content: toolResults,
            });
          }

          if (turnCount >= maxTurns) {
            log.warn("Hit max turns limit");
            pushEvent("done", {
              success: false,
              error: "Max turns reached",
              turns: turnCount,
              entities: allEntities,
            });
          }

          log.info(
            { turns: turnCount, elapsed: `${Date.now() - startTime}ms` },
            "Stream complete",
          );
          controller.close();
        } catch (error) {
          log.error(
            {
              error: error instanceof Error ? error.message : String(error),
              stack: error instanceof Error ? error.stack : undefined,
              elapsed: `${Date.now() - startTime}ms`,
            },
            "Fatal error",
          );

          if (!streamClosed) {
            pushEvent("done", {
              success: false,
              error:
                error instanceof Error
                  ? error.message
                  : "Internal server error",
              entities: [],
            });
          }

          controller.close();
        } finally {
          streamClosed = true;
        }
      },
    });

    log.debug("Returning stream to client");
    return sendStream(event, stream);
  } catch (setupError) {
    log.error(
      {
        error:
          setupError instanceof Error ? setupError.message : String(setupError),
        stack: setupError instanceof Error ? setupError.stack : undefined,
      },
      "Setup error",
    );
    throw createError({
      statusCode: 500,
      message:
        setupError instanceof Error
          ? setupError.message
          : "Failed to initialize query",
    });
  }
});
