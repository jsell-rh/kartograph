<template>
  <div class="tool-call-display space-y-2">
    <!-- Header with tool name and timing -->
    <div class="flex items-center gap-2 text-muted-foreground">
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
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
        />
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      <span class="text-sm font-medium">{{ toolName }}</span>
      <span
        v-if="timing"
        class="flex items-center gap-1 text-xs font-mono text-primary/80 bg-primary/10 px-2 py-0.5 rounded-full ml-auto"
      >
        <svg
          class="w-3 h-3"
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
        {{ timing }}
      </span>
    </div>

    <!-- Description -->
    <div class="text-sm text-muted-foreground/80 pl-6">
      {{ description }}
    </div>

    <!-- Input Parameters Section -->
    <div v-if="input" class="pl-6">
      <button
        @click="toggleInput"
        class="group flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-1"
      >
        <svg
          class="w-3 h-3 transition-transform duration-200"
          :class="{ 'rotate-90': showInput }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span>Input Parameters</span>
      </button>

      <Transition name="expand-code">
        <div v-if="showInput" class="mt-2 relative group/code">
          <!-- Copy button -->
          <button
            @click="copyToClipboard(formattedInput, 'input')"
            class="absolute top-2 right-2 p-1.5 rounded bg-background/80 hover:bg-background border border-border/50 opacity-0 group-hover/code:opacity-100 transition-opacity z-10"
            :title="copiedInput ? 'Copied!' : 'Copy input'"
          >
            <svg
              v-if="copiedInput"
              class="w-3.5 h-3.5 text-green-500"
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
            <svg
              v-else
              class="w-3.5 h-3.5"
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

          <!-- Syntax-highlighted code -->
          <div
            class="rounded-lg bg-muted/30 backdrop-blur-sm border border-border/40 p-3 font-mono text-xs overflow-x-auto max-h-64 overflow-y-auto"
          >
            <pre v-html="highlightedInput" class="whitespace-pre-wrap break-words"></pre>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Output Section -->
    <div v-if="result" class="pl-6">
      <button
        @click="toggleOutput"
        class="group flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-1"
      >
        <svg
          class="w-3 h-3 transition-transform duration-200"
          :class="{ 'rotate-90': showOutput }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span>Output</span>
        <span class="text-[10px] text-primary/70 bg-primary/10 px-1.5 py-0.5 rounded-full font-normal">
          {{ formatSize(result) }}
        </span>
      </button>

      <Transition name="expand-code">
        <div v-if="showOutput" class="mt-2 relative group/code">
          <!-- Copy button -->
          <button
            @click="copyToClipboard(result, 'output')"
            class="absolute top-2 right-2 p-1.5 rounded bg-background/80 hover:bg-background border border-border/50 opacity-0 group-hover/code:opacity-100 transition-opacity z-10"
            :title="copiedOutput ? 'Copied!' : 'Copy output'"
          >
            <svg
              v-if="copiedOutput"
              class="w-3.5 h-3.5 text-green-500"
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
            <svg
              v-else
              class="w-3.5 h-3.5"
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

          <!-- Syntax-highlighted code with truncation -->
          <div
            class="rounded-lg bg-muted/30 backdrop-blur-sm border border-border/40 p-3 font-mono text-xs overflow-x-auto max-h-80 overflow-y-auto"
          >
            <pre v-html="highlightedOutput" class="whitespace-pre-wrap break-words"></pre>
            <div
              v-if="isTruncated"
              class="mt-3 pt-3 border-t border-border/30 text-center text-muted-foreground italic"
            >
              ... output truncated (showing first {{ maxOutputLength.toLocaleString() }} characters)
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Error display -->
    <div
      v-if="error"
      class="text-sm text-destructive pl-6 flex items-center gap-2"
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
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      Error: {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { codeToHtml } from 'shiki';

interface Props {
  toolName: string;
  description: string;
  error?: string;
  timing?: string;
  input?: any;
  result?: string;
}

const props = defineProps<Props>();

// State
const showInput = ref(false);
const showOutput = ref(false);
const copiedInput = ref(false);
const copiedOutput = ref(false);
const maxOutputLength = 5000;

// Computed
const formattedInput = computed(() => {
  if (!props.input) return '';
  try {
    return JSON.stringify(props.input, null, 2);
  } catch {
    return String(props.input);
  }
});

const isTruncated = computed(() => {
  return props.result && props.result.length > maxOutputLength;
});

const truncatedResult = computed(() => {
  if (!props.result) return '';
  if (props.result.length <= maxOutputLength) return props.result;
  return props.result.substring(0, maxOutputLength);
});

const highlightedInput = ref('');
const highlightedOutput = ref('');

// Syntax highlighting using shiki
async function highlightCode(code: string, language: string = 'json'): Promise<string> {
  try {
    return await codeToHtml(code, {
      lang: language,
      theme: 'github-dark-dimmed',
    });
  } catch (e) {
    // Fallback to plain text if highlighting fails
    return `<code>${escapeHtml(code)}</code>`;
  }
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Watch for input changes and highlight
watch(() => props.input, async (newInput) => {
  if (newInput) {
    highlightedInput.value = await highlightCode(formattedInput.value);
  }
}, { immediate: true });

// Watch for result changes and highlight
watch(() => props.result, async (newResult) => {
  if (newResult) {
    // Try to detect if it's JSON and highlight accordingly
    const isJson = newResult.trim().startsWith('{') || newResult.trim().startsWith('[');
    highlightedOutput.value = await highlightCode(
      truncatedResult.value,
      isJson ? 'json' : 'text'
    );
  }
}, { immediate: true });

// Methods
function toggleInput() {
  showInput.value = !showInput.value;
}

function toggleOutput() {
  showOutput.value = !showOutput.value;
}

async function copyToClipboard(text: string, type: 'input' | 'output') {
  try {
    await navigator.clipboard.writeText(text);
    if (type === 'input') {
      copiedInput.value = true;
      setTimeout(() => (copiedInput.value = false), 2000);
    } else {
      copiedOutput.value = true;
      setTimeout(() => (copiedOutput.value = false), 2000);
    }
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

function formatSize(text: string): string {
  const len = text.length;
  if (len < 1024) return `${len} chars`;
  if (len < 1024 * 1024) return `${(len / 1024).toFixed(1)} KB`;
  return `${(len / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<style scoped>
/* Expand/collapse animation for code blocks */
.expand-code-enter-active,
.expand-code-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-code-enter-from,
.expand-code-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}

.expand-code-enter-to,
.expand-code-leave-from {
  opacity: 1;
  max-height: 500px;
  margin-top: 0.5rem;
}

/* Syntax highlighting overrides for theme consistency */
:deep(pre) {
  margin: 0;
  padding: 0;
  background: transparent !important;
}

:deep(code) {
  background: transparent !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  line-height: 1.5;
}

/* Custom scrollbar for code blocks */
:deep(.overflow-x-auto)::-webkit-scrollbar {
  height: 8px;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-track {
  background: transparent;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 4px;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}
</style>
