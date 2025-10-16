<template>
  <div class="space-y-6">
    <!-- Loading state (when loading conversation history) -->
    <div v-if="loadingConversation" class="space-y-6">
      <!-- User message skeleton -->
      <div class="flex justify-end">
        <div
          class="max-w-[80%] bg-primary/20 backdrop-blur-md rounded-lg p-4 animate-pulse"
        >
          <div class="h-4 bg-primary/30 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-primary/30 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Assistant message skeleton -->
      <div class="flex justify-start">
        <div
          class="max-w-[90%] bg-card/40 backdrop-blur-md border border-border/40 rounded-lg p-5 animate-pulse"
        >
          <div class="h-4 bg-muted/50 rounded w-full mb-3"></div>
          <div class="h-4 bg-muted/50 rounded w-5/6 mb-3"></div>
          <div class="h-4 bg-muted/50 rounded w-4/5 mb-3"></div>
          <div class="h-3 bg-muted/40 rounded w-1/4 mt-4"></div>
        </div>
      </div>

      <!-- User message skeleton -->
      <div class="flex justify-end">
        <div
          class="max-w-[80%] bg-primary/20 backdrop-blur-md rounded-lg p-4 animate-pulse"
        >
          <div class="h-4 bg-primary/30 rounded w-2/3"></div>
        </div>
      </div>

      <!-- Assistant message skeleton -->
      <div class="flex justify-start">
        <div
          class="max-w-[90%] bg-card/40 backdrop-blur-md border border-border/40 rounded-lg p-5 animate-pulse"
        >
          <div class="h-4 bg-muted/50 rounded w-full mb-3"></div>
          <div class="h-4 bg-muted/50 rounded w-11/12 mb-3"></div>
          <div class="h-4 bg-muted/50 rounded w-3/4"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="messages.length === 0"
      class="text-center py-16 text-muted-foreground"
    >
      <div class="text-5xl mb-6">🗺️</div>
      <p class="text-xl font-medium text-foreground">
        Ask a question to explore the knowledge graph
      </p>
      <p v-if="graphStats" class="text-sm mt-3 text-muted-foreground/80">
        {{ graphStats.totalEntities.toLocaleString() }} entities •
        {{ graphStats.typeCount }} types • Real-time querying
      </p>
      <p v-else class="text-sm mt-3 text-muted-foreground/80">
        Loading graph statistics...
      </p>
    </div>

    <!-- Messages -->
    <div v-for="(message, index) in messages" :key="index" class="space-y-4">
      <!-- User message -->
      <div v-if="message.role === 'user'" class="flex justify-end">
        <div
          class="max-w-[80%] bg-primary/90 backdrop-blur-md text-primary-foreground rounded-lg p-4 shadow-lg shadow-primary/20 relative group border border-primary/20"
        >
          <!-- Copy button -->
          <button
            class="absolute top-2 right-2 p-1.5 rounded bg-primary-foreground/10 hover:bg-primary-foreground/20 transition-all"
            :class="
              isCopied(`user-${index}`)
                ? 'opacity-100'
                : 'opacity-0 group-hover:opacity-100'
            "
            @click="copyToClipboard(message.content, 'user', `user-${index}`)"
            :title="isCopied(`user-${index}`) ? 'Copied!' : 'Copy message'"
          >
            <!-- Checkmark icon when copied -->
            <svg
              v-if="isCopied(`user-${index}`)"
              class="w-4 h-4 text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <!-- Copy icon normally -->
            <svg
              v-else
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          </button>

          <div class="text-base prose prose-sm max-w-none prose-invert">
            <div v-html="renderUserMessage(message.content)" />
          </div>
          <div class="text-xs opacity-75 mt-2.5">
            {{ formatTime(message.timestamp) }}
          </div>
        </div>
      </div>

      <!-- Assistant message -->
      <div v-else class="flex justify-start">
        <div class="max-w-[90%]">
          <!-- Thinking process viewer (if there are thinking steps) -->
          <ThinkingViewer
            :thinking-steps="message.thinkingSteps"
            @entity-click="(entity) => emit('entityClick', entity)"
          />

          <!-- Final answer with glass-morphism -->
          <div
            class="bg-card/60 backdrop-blur-md border border-border/40 rounded-lg p-5 shadow-lg shadow-background/5 relative group"
          >
            <!-- Copy button -->
            <button
              class="absolute top-3 right-3 p-1.5 rounded bg-muted hover:bg-muted/80 transition-all"
              :class="
                isCopied(`assistant-${index}`)
                  ? 'opacity-100'
                  : 'opacity-0 group-hover:opacity-100'
              "
              @click="
                copyToClipboard(
                  message.content,
                  'assistant',
                  `assistant-${index}`,
                )
              "
              :title="
                isCopied(`assistant-${index}`) ? 'Copied!' : 'Copy response'
              "
            >
              <!-- Checkmark icon when copied -->
              <svg
                v-if="isCopied(`assistant-${index}`)"
                class="w-4 h-4 text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <!-- Copy icon normally -->
              <svg
                v-else
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </button>

            <div class="prose prose-sm max-w-none">
              <div v-html="renderMessage(message.content)" />
            </div>
            <div
              class="text-xs text-muted-foreground mt-3 flex items-center gap-2"
            >
              <span>{{ formatTime(message.timestamp) }}</span>
              <span
                v-if="message.elapsedSeconds"
                class="text-primary/70 font-medium"
              >
                • {{ formatElapsedTime(message.elapsedSeconds) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Live thinking viewer (appears while loading) -->
    <Transition name="fade">
      <div v-if="loading" class="mt-4">
        <ThinkingViewer
          :thinking-steps="currentThinkingSteps"
          :loading="true"
          :elapsed-time="elapsedTime"
          @entity-click="(entity) => emit('entityClick', entity)"
        />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { marked } from "marked";

interface ThinkingStep {
  type: "thinking" | "tool_call" | "retry";
  content: string;
  metadata?: {
    toolName?: string;
    description?: string;
    timing?: number;
    error?: string;
  };
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  thinkingSteps?: ThinkingStep[];
  elapsedSeconds?: number;
}

interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

interface Props {
  messages: Message[];
  entities?: Entity[];
  loading?: boolean;
  loadingConversation?: boolean;
  currentThinkingSteps?: ThinkingStep[];
}

const props = withDefaults(defineProps<Props>(), {
  entities: () => [],
  loading: false,
  loadingConversation: false,
  currentThinkingSteps: () => [],
});

const emit = defineEmits<{
  entityClick: [entity: Entity];
}>();

// Track copy state for each message (by index)
const copiedStates = ref<Map<string, boolean>>(new Map());

// Graph statistics
const graphStats = ref<{ totalEntities: number; typeCount: number } | null>(
  null,
);

// Configure marked for inline rendering with custom renderer
const renderer = new marked.Renderer();

// Override link renderer to add target="_blank" and rel attributes
renderer.link = ({ href, title, text }) => {
  const titleAttr = title ? ` title="${title}"` : '';
  return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`;
};

marked.setOptions({
  breaks: true,
  gfm: true,
  renderer,
});

/**
 * Elapsed time tracking for loading indicator
 */
const elapsedTime = ref(0);
let timerInterval: NodeJS.Timeout | null = null;

// Watch loading state to start/stop timer
watch(
  () => props.loading,
  (isLoading) => {
    if (isLoading) {
      // Reset and start timer
      elapsedTime.value = 0;
      if (timerInterval) clearInterval(timerInterval);

      timerInterval = setInterval(() => {
        elapsedTime.value++;
      }, 1000);
    } else {
      // Stop timer
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
    }
  },
);

// Cleanup on unmount
onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval);
});

/**
 * Format elapsed time (MM:SS)
//  */
// function formatElapsedTime(seconds: number): string {
//   const mins = Math.floor(seconds / 60)
//   const secs = seconds % 60
//   return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
// }

/**
 * Format timestamp
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format elapsed time (human readable)
 */
function formatElapsedTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(
  text: string,
  type: "user" | "assistant",
  messageId: string,
) {
  try {
    await navigator.clipboard.writeText(text);
    console.log(`${type} message copied to clipboard`);

    // Show checkmark for 2 seconds
    copiedStates.value.set(messageId, true);
    setTimeout(() => {
      copiedStates.value.set(messageId, false);
    }, 2000);
  } catch (err) {
    console.error("Failed to copy:", err);
  }
}

/**
 * Check if a message is currently showing copied state
 */
function isCopied(messageId: string): boolean {
  return copiedStates.value.get(messageId) || false;
}

/**
 * Render user message with simple markdown formatting
 */
function renderUserMessage(content: string): string {
  if (!content) return "";

  try {
    // Use marked for user messages too, but simpler
    return marked.parse(content) as string;
  } catch (e) {
    console.error("[ResponseDisplay] User message markdown parsing error:", e);
    // Fallback to plain text with line breaks
    return content.replace(/\n/g, "<br>");
  }
}

/**
 * Render message with entity highlighting and markdown formatting
 */
function renderMessage(content: string): string {
  if (!content) return "";

  // STEP 1: Extract and temporarily replace URN patterns to protect them from markdown processing
  const urnPattern = /<urn:([^:]+):([^>]+)>/g;
  const matches = [...content.matchAll(urnPattern)];
  const urnPlaceholders: Map<string, string> = new Map();
  let rendered = content;

  // Replace URNs with placeholders (reverse order to maintain indices)
  for (let i = matches.length - 1; i >= 0; i--) {
    const match = matches[i];
    if (!match) continue;
    const [fullUrn, type, id] = match;
    if (!fullUrn || !type || !id) continue;
    const displayName = id.replace(/-/g, " ").replace(/_/g, " ");

    // Create unique placeholder using HTML comment (won't be affected by markdown)
    const placeholder = `<!--URN_CHIP_${i}-->`;

    // Create clickable chip (single line)
    const chip = `<button class="entity-chip inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-primary/10 text-primary hover:bg-primary/20 hover:shadow-md transition-all border border-primary/20" data-urn="${fullUrn}" data-type="${type}" data-id="${id}" data-display-name="${displayName}" onclick="window.handleEntityClick('${fullUrn}', '${type}', '${id}', '${displayName}')"><span class="text-xs opacity-70 font-normal">${type}</span><span>${displayName}</span></button>`;

    urnPlaceholders.set(placeholder, chip);

    const index = match.index!;
    rendered =
      rendered.substring(0, index) +
      placeholder +
      rendered.substring(index + fullUrn.length);
  }

  // STEP 2: Process markdown (use full parser for headings, lists, etc.)
  try {
    rendered = marked.parse(rendered) as string;
  } catch (e) {
    console.error("[ResponseDisplay] Markdown parsing error:", e);
    // Fallback to basic formatting
    rendered = rendered
      .replace(
        /^### (.*?)$/gm,
        '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>',
      )
      .replace(
        /^## (.*?)$/gm,
        '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>',
      )
      .replace(
        /^# (.*?)$/gm,
        '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>',
      )
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(
        /`([^`]+)`/g,
        '<code class="px-1 py-0.5 bg-muted rounded text-sm">$1</code>',
      )
      .replace(/\n/g, "<br>");
  }

  // STEP 3: Restore entity chips
  for (const [placeholder, chip] of urnPlaceholders.entries()) {
    rendered = rendered.replace(new RegExp(placeholder, "g"), chip);
  }

  return rendered;
}

/**
 * Handle entity click from rendered HTML
 */
if (process.client) {
  (window as any).handleEntityClick = (
    urn: string,
    type: string,
    id: string,
    displayName: string,
  ) => {
    emit("entityClick", { urn, type, id, displayName });
  };
}

/**
 * Fetch graph statistics on mount
 */
onMounted(async () => {
  try {
    graphStats.value = await $fetch("/api/stats");
  } catch (error) {
    console.error("Failed to fetch graph stats:", error);
  }
});
</script>

<style scoped>
.prose {
  @apply text-foreground;
}

/* User message prose styling (inverted colors for dark bg) */
.prose-invert :deep(p) {
  @apply text-primary-foreground;
}

.prose-invert :deep(strong) {
  @apply text-primary-foreground font-semibold;
}

.prose-invert :deep(em) {
  @apply text-primary-foreground/90 italic;
}

.prose-invert :deep(code) {
  @apply text-primary-foreground bg-primary-foreground/10 border-primary-foreground/20;
}

.prose-invert :deep(a) {
  @apply text-primary-foreground underline;
}

.prose :deep(button.entity-chip) {
  cursor: pointer;
  @apply transform;
}

.prose :deep(button.entity-chip:hover) {
  @apply shadow-md -translate-y-0.5;
}

.prose :deep(h1) {
  @apply text-xl font-bold mt-6 mb-3;
}

.prose :deep(h2) {
  @apply text-lg font-bold mt-5 mb-2.5;
}

.prose :deep(h3) {
  @apply text-base font-semibold mt-4 mb-2;
}

.prose :deep(h4) {
  @apply text-sm font-semibold mt-3 mb-1.5;
}

.prose :deep(p) {
  @apply my-2;
}

.prose :deep(code) {
  @apply px-1.5 py-0.5 bg-muted/80 rounded text-sm font-mono border border-border/50;
}

.prose :deep(pre) {
  @apply p-4 bg-muted/60 rounded-lg my-3 overflow-x-auto border border-border/30 shadow-sm;
}

.prose :deep(pre code) {
  @apply p-0 bg-transparent border-0;
}

.prose :deep(strong) {
  @apply font-semibold;
}

.prose :deep(em) {
  @apply italic;
}

.prose :deep(a) {
  @apply text-primary hover:underline;
}

.prose :deep(ul) {
  @apply list-disc my-2 pl-6;
}

.prose :deep(ol) {
  @apply list-decimal my-2 pl-6;
}

.prose :deep(li) {
  @apply my-1.5 pl-2;
}

/* Modern table styling */
.prose :deep(table) {
  @apply w-full my-4 border-collapse;
  border-spacing: 0;
}

.prose :deep(thead) {
  @apply bg-muted/50 border-b-2 border-border;
}

.prose :deep(th) {
  @apply px-4 py-3 text-left font-semibold text-sm;
  @apply border-b border-border/60;
}

.prose :deep(tbody tr) {
  @apply border-b border-border/30;
  @apply transition-colors duration-150;
}

.prose :deep(tbody tr:hover) {
  @apply bg-muted/20;
}

.prose :deep(tbody tr:last-child) {
  @apply border-b-0;
}

.prose :deep(td) {
  @apply px-4 py-3 text-sm;
}

/* Fade transition for thinking indicator */
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
