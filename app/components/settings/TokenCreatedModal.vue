<template>
  <!-- Modal Backdrop -->
  <Transition name="modal-backdrop">
    <div
      class="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <!-- Modal -->
      <Transition name="modal">
        <div
          class="bg-card/90 backdrop-blur-md border border-border/40 rounded-lg shadow-2xl max-w-2xl w-full overflow-hidden"
        >
          <!-- Header -->
          <div class="px-6 py-4 border-b border-border/40 bg-green-500/10">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-green-500"
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
              </div>
              <div>
                <h2 class="text-xl font-semibold text-foreground">
                  Token Created Successfully!
                </h2>
                <p class="text-sm text-muted-foreground">{{ name }}</p>
              </div>
            </div>
          </div>

          <!-- Content -->
          <div class="px-6 py-6 space-y-5">
            <!-- Warning Box -->
            <div
              class="bg-destructive/10 border border-destructive/20 rounded-md p-4"
            >
              <div class="flex gap-3">
                <svg
                  class="w-5 h-5 text-destructive flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <div>
                  <p class="text-sm font-semibold text-destructive mb-1">
                    Save This Token Now
                  </p>
                  <p class="text-xs text-destructive/90">
                    You won't be able to see this token again. Make sure to copy
                    it to a secure location before closing this window.
                  </p>
                </div>
              </div>
            </div>

            <!-- Token Display -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">
                API Token
              </label>
              <div class="relative">
                <input
                  :value="token"
                  readonly
                  class="w-full px-3 py-2 pr-24 bg-background border border-border/40 rounded-md text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                />
                <button
                  @click="copyToken"
                  class="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 bg-primary hover:bg-primary/90 text-primary-foreground text-xs rounded transition-colors"
                >
                  {{ tokenCopied ? "Copied!" : "Copy" }}
                </button>
              </div>
            </div>

            <!-- Claude Code Config -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">
                Claude Code Setup Command
              </label>
              <div class="relative">
                <pre
                  class="bg-background border border-border/40 rounded-md p-3 text-xs font-mono text-foreground overflow-x-auto"
                  >{{ claudeConfig }}</pre
                >
                <button
                  @click="copyConfig"
                  class="absolute right-3 top-3 px-3 py-1 bg-primary hover:bg-primary/90 text-primary-foreground text-xs rounded transition-colors"
                >
                  {{ configCopied ? "Copied!" : "Copy" }}
                </button>
              </div>
              <p class="mt-2 text-xs text-muted-foreground">
                Run this command in your terminal to add the Kartograph MCP
                server to Claude Code
              </p>
              <details class="mt-2">
                <summary
                  class="text-xs text-muted-foreground cursor-pointer hover:text-foreground"
                >
                  💡 Configuration tips
                </summary>
                <ul
                  class="mt-2 text-xs text-muted-foreground space-y-1 ml-4 list-disc"
                >
                  <li>
                    Use
                    <code class="px-1 py-0.5 bg-muted rounded"
                      >--scope local</code
                    >
                    for current project only (default)
                  </li>
                  <li>
                    Use
                    <code class="px-1 py-0.5 bg-muted rounded"
                      >--scope project</code
                    >
                    to share via .mcp.json file
                  </li>
                  <li>
                    Use
                    <code class="px-1 py-0.5 bg-muted rounded"
                      >--scope user</code
                    >
                    for all your projects
                  </li>
                </ul>
              </details>
            </div>

            <!-- Metadata -->
            <div class="grid grid-cols-2 gap-4 pt-2">
              <div>
                <div class="text-xs text-muted-foreground mb-1">Expires</div>
                <div class="text-sm text-foreground">
                  {{ formatExpiry(expiresAt) }}
                </div>
              </div>
              <div>
                <div class="text-xs text-muted-foreground mb-1">Rate Limit</div>
                <div class="text-sm text-foreground">100 queries/hour</div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="px-6 py-4 bg-muted/30 border-t border-border/40 flex items-center justify-between"
          >
            <div class="flex items-center gap-2 text-xs text-muted-foreground">
              <input
                id="acknowledge"
                v-model="acknowledged"
                type="checkbox"
                class="w-4 h-4 rounded border-border/40 text-primary focus:ring-primary/50"
              />
              <label for="acknowledge">
                I have saved this token securely
              </label>
            </div>
            <button
              @click="handleClose"
              :disabled="!acknowledged"
              class="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Done
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup lang="ts">
const props = defineProps<{
  token: string;
  name: string;
  expiresAt: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const acknowledged = ref(false);
const tokenCopied = ref(false);
const configCopied = ref(false);

const urls = useAppUrls();

const claudeConfig = computed(() => {
  return `claude mcp add --transport http kartograph ${urls.mcpUrl} \\
  --header "Authorization: Bearer ${props.token}"`;
});

async function copyToken() {
  try {
    await navigator.clipboard.writeText(props.token);
    tokenCopied.value = true;
    setTimeout(() => {
      tokenCopied.value = false;
    }, 2000);
  } catch (err) {
    console.error("Failed to copy token:", err);
  }
}

async function copyConfig() {
  try {
    await navigator.clipboard.writeText(claudeConfig.value);
    configCopied.value = true;
    setTimeout(() => {
      configCopied.value = false;
    }, 2000);
  } catch (err) {
    console.error("Failed to copy config:", err);
  }
}

function formatExpiry(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function handleClose() {
  if (acknowledged.value) {
    emit("close");
  }
}

// Prevent closing via Escape if not acknowledged
onMounted(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === "Escape" && acknowledged.value) {
      emit("close");
    }
  };
  window.addEventListener("keydown", handleEscape);
  onUnmounted(() => window.removeEventListener("keydown", handleEscape));
});
</script>

<style scoped>
/* Modal Backdrop Transitions */
.modal-backdrop-enter-active,
.modal-backdrop-leave-active {
  transition: opacity 0.2s ease;
}

.modal-backdrop-enter-from,
.modal-backdrop-leave-to {
  opacity: 0;
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
