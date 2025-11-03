<template>
  <div
    v-if="loading || (thinkingSteps && thinkingSteps.length > 0)"
    class="mb-3"
  >
    <!-- Collapsible thinking section with glass-morphism -->
    <div
      class="bg-muted/20 backdrop-blur-sm rounded-lg border border-muted-foreground/10 overflow-hidden shadow-md shadow-background/5"
    >
      <!-- Header - clickable to expand/collapse -->
      <button
        class="w-full px-4 py-2.5 flex items-center justify-between hover:bg-muted/50 transition-colors text-left"
        @click="expanded = !expanded"
      >
        <div
          class="flex items-center gap-2.5 text-sm font-medium text-muted-foreground"
        >
          <!-- Pulsing dot when loading -->
          <span v-if="loading" class="relative flex h-2.5 w-2.5">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"
            ></span>
            <span
              class="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"
            ></span>
          </span>
          <!-- Lightbulb icon when complete -->
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <span>{{ loading ? "Thinking" : "Thinking process" }}</span>
          <!-- Show elapsed time when loading, step count when complete -->
          <span
            v-if="loading"
            class="font-mono text-xs tabular-nums text-primary/70"
          >
            {{ formatElapsedTime(elapsedTime) }}
          </span>
          <span
            v-else-if="thinkingSteps && thinkingSteps.length > 0"
            class="flex items-center gap-1.5"
          >
            <span
              class="text-xs bg-muted/60 px-2 py-0.5 rounded-full font-normal"
            >
              {{ thinkingSteps.length }} step{{
                thinkingSteps.length > 1 ? "s" : ""
              }}
            </span>
            <span
              v-if="!expanded && thinkingSteps.length > 1"
              class="text-xs font-mono text-primary/70"
            >
              {{ currentStepIndex + 1 }}/{{ thinkingSteps.length }}
            </span>
          </span>
        </div>
        <svg
          class="w-5 h-5 transition-transform duration-200"
          :class="{ 'rotate-180': expanded }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      <!-- Latest thinking step (always visible when collapsed) -->
      <div
        v-if="!expanded && currentStep"
        class="px-4 py-2.5 border-t border-muted-foreground/10"
      >
        <Transition name="fade-thinking" mode="out-in">
          <div
            :key="currentStepIndex"
            class="text-sm text-muted-foreground prose prose-sm max-w-none"
          >
            <div
              v-html="renderThinkingStep(truncate(currentStep.content, 120))"
            />
          </div>
        </Transition>
      </div>

      <!-- All thinking steps (visible when expanded) -->
      <Transition name="expand">
        <div v-if="expanded" class="border-t border-muted-foreground/10">
          <div
            ref="stepsContainer"
            class="max-h-64 overflow-y-auto"
            @scroll="handleStepsScroll"
          >
            <!-- Show steps if available -->
            <div
              v-for="(step, index) in thinkingSteps"
              :key="index"
              class="px-4 py-2.5 text-sm text-muted-foreground border-b border-muted-foreground/5 last:border-b-0 hover:bg-muted/20 transition-colors"
            >
              <div class="flex items-start gap-2.5">
                <span
                  class="text-xs font-mono text-primary/70 mt-0.5 flex-shrink-0 font-medium"
                  >{{ index + 1 }}</span
                >
                <div class="flex-1 prose prose-sm max-w-none">
                  <!-- Tool call display -->
                  <ToolCallDisplay
                    v-if="step.type === 'tool_call'"
                    :tool-name="step.metadata?.toolName || 'Tool'"
                    :description="step.content"
                    :error="step.metadata?.error"
                    :timing="
                      step.metadata?.timing
                        ? `${(step.metadata.timing / 1000).toFixed(2)}s`
                        : undefined
                    "
                    :input="step.metadata?.input"
                    :result="step.metadata?.result"
                  />
                  <!-- Retry message -->
                  <div
                    v-else-if="step.type === 'retry'"
                    class="flex items-center gap-2 text-muted-foreground/80 italic"
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    {{ step.content }}
                  </div>
                  <!-- Regular thinking step -->
                  <div v-else v-html="renderThinkingStep(step.content)" />
                </div>
              </div>
            </div>
            <!-- Show placeholder when loading but no steps yet -->
            <div
              v-if="loading && (!thinkingSteps || thinkingSteps.length === 0)"
              class="px-4 py-2.5 text-sm text-muted-foreground/80 italic"
            >
              Initializing query...
            </div>
          </div>
        </div>
      </Transition>
    </div>
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

interface Props {
  thinkingSteps?: ThinkingStep[];
  loading?: boolean;
  elapsedTime?: number;
}

interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  elapsedTime: 0,
});

const emit = defineEmits<{
  entityClick: [entity: Entity];
}>();

const expanded = ref(false);
const currentStepIndex = ref(0);
const stepsContainer = ref<HTMLElement | null>(null);
const isStepsAtBottom = ref(true);

// Configure marked for inline rendering
marked.setOptions({
  breaks: true,
  gfm: true,
});

/**
 * Check if steps container is scrolled to bottom
 */
function checkIfStepsAtBottom() {
  if (!stepsContainer.value) return true;

  const { scrollTop, scrollHeight, clientHeight } = stepsContainer.value;
  // Consider "at bottom" if within 50px of the bottom
  const threshold = 50;
  return scrollHeight - scrollTop - clientHeight < threshold;
}

/**
 * Handle scroll event on steps container
 */
function handleStepsScroll() {
  isStepsAtBottom.value = checkIfStepsAtBottom();
}

/**
 * Scroll steps container to bottom
 */
function scrollStepsToBottom() {
  if (stepsContainer.value) {
    nextTick(() => {
      if (stepsContainer.value) {
        stepsContainer.value.scrollTop = stepsContainer.value.scrollHeight;
      }
    });
  }
}

// Auto-rotate through thinking steps when collapsed
let rotateInterval: NodeJS.Timeout | null = null;

// Watch thinking steps and auto-scroll if user is at bottom
watch(
  () => props.thinkingSteps,
  (steps) => {
    if (steps && steps.length > 0) {
      currentStepIndex.value = steps.length - 1; // Always show the latest step

      // Auto-scroll if expanded and user is at bottom
      if (expanded.value && isStepsAtBottom.value) {
        scrollStepsToBottom();
      }
    }
  },
  { immediate: true, deep: true },
);

// Auto-expand when loading starts
watch(
  () => props.loading,
  (isLoading) => {
    if (isLoading && !expanded.value) {
      expanded.value = true;
    }
  },
);

// Clean up interval on unmount
onUnmounted(() => {
  if (rotateInterval) clearInterval(rotateInterval);
});

// Current step to display
const currentStep = computed(() => {
  if (!props.thinkingSteps || props.thinkingSteps.length === 0) return null;
  return props.thinkingSteps[currentStepIndex.value];
});

// Truncate text with ellipsis
function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

// Format elapsed time (MM:SS)
function formatElapsedTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Render thinking step with markdown and URN highlighting
 * Only used for 'thinking' type steps now (tool_call and retry handled in template)
 */
function renderThinkingStep(content: string): string {
  if (!content) return "";

  // STEP 1: Extract and temporarily replace URN patterns
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

    // Create unique placeholder
    const placeholder = `<!--URN_${i}-->`;

    // Create clickable styled URN
    const styledUrn = `<button class="entity-chip inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors border border-primary/20" data-urn="${fullUrn}" data-type="${type}" data-id="${id}" data-display-name="${displayName}" onclick="window.handleThinkingEntityClick('${fullUrn}', '${type}', '${id}', '${displayName}')"><span class="text-[10px] opacity-70">${type}</span><span>${displayName}</span></button>`;

    urnPlaceholders.set(placeholder, styledUrn);

    const index = match.index!;
    rendered =
      rendered.substring(0, index) +
      placeholder +
      rendered.substring(index + fullUrn.length);
  }

  // STEP 2: Process markdown
  try {
    rendered = marked.parse(rendered) as string;
  } catch (e) {
    console.error("[ThinkingViewer] Markdown parsing error:", e);
    // Fallback to basic formatting
    rendered = rendered
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(
        /`([^`]+)`/g,
        '<code class="px-1 py-0.5 bg-muted rounded text-xs">$1</code>',
      )
      .replace(/\n/g, "<br>");
  }

  // STEP 3: Restore URN styling
  for (const [placeholder, styledUrn] of urnPlaceholders.entries()) {
    rendered = rendered.replace(new RegExp(placeholder, "g"), styledUrn);
  }

  return rendered;
}

/**
 * Handle entity click from rendered HTML
 */
if (process.client) {
  (window as any).handleThinkingEntityClick = (
    urn: string,
    type: string,
    id: string,
    displayName: string,
  ) => {
    emit("entityClick", { urn, type, id, displayName });
  };
}
</script>

<style scoped>
/* Prose formatting for thinking steps */
.prose {
  @apply text-muted-foreground;
}

.prose :deep(p) {
  @apply my-1;
}

.prose :deep(code) {
  @apply px-1 py-0.5 bg-muted rounded text-xs font-mono;
}

.prose :deep(strong) {
  @apply font-semibold;
}

.prose :deep(em) {
  @apply italic;
}

.prose :deep(ul) {
  @apply list-disc list-inside my-1;
}

.prose :deep(ol) {
  @apply list-decimal list-inside my-1;
}

.prose :deep(li) {
  @apply my-0.5;
}

.prose :deep(button.entity-chip) {
  cursor: pointer;
}

.prose :deep(button.entity-chip:hover) {
  @apply shadow-sm;
}

/* Tool call styling - Beautiful boxed format */
.prose :deep(.tool-call-box) {
  @apply bg-muted/30 rounded-lg border border-border/40 overflow-hidden;
}

.prose :deep(.tool-call-header) {
  @apply flex items-start gap-3 p-3;
}

.prose :deep(.tool-icon) {
  @apply w-5 h-5 flex-shrink-0 text-muted-foreground/70 mt-0.5;
}

.prose :deep(.tool-text) {
  @apply flex-1 min-w-0;
}

.prose :deep(.tool-name) {
  @apply text-sm font-bold text-foreground mb-1;
}

.prose :deep(.tool-description) {
  @apply text-xs text-muted-foreground/80;
}

/* Error chip - full width, beautiful rounded rectangle */
.prose :deep(.tool-error-chip) {
  @apply flex items-center gap-2 px-3 py-2 bg-destructive/10 border-t border-destructive/20 text-destructive;
}

.prose :deep(.error-icon) {
  @apply w-4 h-4 flex-shrink-0;
}

.prose :deep(.error-text) {
  @apply text-xs font-medium flex-1 truncate;
}

/* Retry styling */
.prose :deep(.retry-container) {
  @apply space-y-1.5;
}

.prose :deep(.retry-header) {
  @apply flex items-center gap-2 text-amber-600 dark:text-amber-400;
}

.prose :deep(.retry-icon) {
  @apply w-4 h-4 flex-shrink-0;
}

.prose :deep(.retry-text) {
  @apply text-xs font-medium;
}

/* Spinner animation */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Fade transition for thinking steps */
.fade-thinking-enter-active,
.fade-thinking-leave-active {
  transition: opacity 0.3s ease;
}

.fade-thinking-enter-from,
.fade-thinking-leave-to {
  opacity: 0;
}

/* Expand transition for full thinking list */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 300px;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
