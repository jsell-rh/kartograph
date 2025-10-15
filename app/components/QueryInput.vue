<template>
  <div class="space-y-4">
    <div class="relative">
      <textarea
        ref="textareaRef"
        v-model="query"
        :disabled="loading"
        placeholder="Ask anything about the knowledge graph... (e.g., 'Which service does /upload point to?')"
        class="w-full min-h-[100px] p-4 pr-12 rounded-lg border-2 bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all shadow-sm"
        @keydown="handleKeydown"
      />
      <div
        class="absolute bottom-3 right-3 text-xs text-muted-foreground/70 bg-background/80 px-2 py-1 rounded"
      >
        Press Enter to send, Shift+Enter for new line
      </div>
    </div>

    <div class="flex justify-between items-center">
      <div class="text-sm font-medium">
        <template v-if="loading">
          <span class="inline-flex items-center gap-2 text-primary">
            <span class="animate-pulse text-base">●</span>
            Querying knowledge graph...
          </span>
        </template>
        <template v-else>
          <span class="text-muted-foreground/80">Ready</span>
        </template>
      </div>

      <div class="flex gap-2">
        <!-- Stop button (shown when loading) -->
        <button
          v-if="loading"
          class="px-6 py-2.5 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-all font-medium shadow-sm hover:shadow-md flex items-center gap-2"
          @click="emit('stop')"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <rect x="6" y="6" width="12" height="12" rx="1" stroke-width="2" />
          </svg>
          Stop
        </button>

        <!-- Submit button (shown when not loading) -->
        <button
          v-else
          :disabled="!query.trim()"
          class="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm hover:shadow-md"
          @click="handleSubmit"
        >
          Ask
        </button>
      </div>
    </div>

    <!-- Example queries -->
    <Transition name="slide-fade">
      <div
        v-if="!loading && query.length === 0"
        class="overflow-hidden pt-4 border-t"
      >
        <p class="text-sm font-medium text-muted-foreground mb-3">
          Try these examples:
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="example in examples"
            :key="example"
            class="text-sm px-3.5 py-2 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:shadow-sm transition-all border border-border/50"
            @click="query = example"
          >
            {{ example }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
interface Props {
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const emit = defineEmits<{
  submit: [query: string];
  stop: [];
}>();

const query = ref("");
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const examples = [
  "Which service does /upload point to?",
  "Show me all services owned by the SRE team",
  "What are the SLOs for acs-fleet-manager?",
  "Find all namespaces running on cluster appsrep09ue1",
  "Who has access to the telemeter service?",
];

function handleSubmit() {
  if (query.value.trim() && !props.loading) {
    emit("submit", query.value.trim());
    query.value = "";
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
}

// Auto-focus on mount
onMounted(() => {
  textareaRef.value?.focus();
});
</script>

<style scoped>
/* Smooth slide-fade transition for examples */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateY(-10px);
  opacity: 0;
  max-height: 0;
}

.slide-fade-enter-to {
  transform: translateY(0);
  opacity: 1;
  max-height: 500px;
}

.slide-fade-leave-from {
  transform: translateY(0);
  opacity: 1;
  max-height: 500px;
}

.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
  max-height: 0;
}
</style>
