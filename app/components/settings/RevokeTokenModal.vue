<template>
  <!-- Modal Backdrop -->
  <Transition name="modal-backdrop">
    <div
      class="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <!-- Modal -->
      <Transition name="modal">
        <div
          class="bg-card/90 backdrop-blur-md border border-border/40 rounded-lg shadow-2xl max-w-md w-full overflow-hidden"
        >
          <!-- Header -->
          <div class="px-6 py-4 border-b border-border/40">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 bg-destructive/20 rounded-full flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-destructive"
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
              </div>
              <h2 class="text-xl font-semibold text-foreground">
                Revoke Token
              </h2>
            </div>
          </div>

          <!-- Content -->
          <div class="px-6 py-6 space-y-4">
            <p class="text-sm text-foreground">
              Are you sure you want to revoke the token
              <strong class="font-semibold">{{ token.name }}</strong
              >?
            </p>

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
                    d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div class="text-xs text-destructive">
                  <p class="font-semibold mb-1">This action cannot be undone</p>
                  <ul class="list-disc list-inside space-y-1">
                    <li>The token will be invalidated immediately</li>
                    <li>Any applications using this token will lose access</li>
                    <li>
                      You'll need to create a new token and reconfigure affected
                      applications
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Token Metadata -->
            <div class="bg-muted/30 rounded-md p-3 space-y-2 text-xs">
              <div class="flex justify-between">
                <span class="text-muted-foreground">Created:</span>
                <span class="text-foreground">{{
                  formatDate(token.createdAt)
                }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Last Used:</span>
                <span class="text-foreground">{{
                  formatRelativeTime(token.lastUsedAt)
                }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Total Queries:</span>
                <span class="text-foreground">{{
                  token.totalQueries.toLocaleString()
                }}</span>
              </div>
            </div>

            <!-- Error Message -->
            <div
              v-if="error"
              class="bg-destructive/10 border border-destructive/20 rounded-md p-3"
            >
              <div class="flex items-center gap-2 text-destructive text-sm">
                <svg
                  class="w-5 h-5 flex-shrink-0"
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
                <span>{{ error }}</span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="px-6 py-4 bg-muted/30 border-t border-border/40 flex gap-3"
          >
            <button
              type="button"
              @click="$emit('close')"
              class="flex-1 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md transition-colors"
              :disabled="loading"
            >
              Cancel
            </button>
            <button
              @click="handleRevoke"
              class="flex-1 px-4 py-2 bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              :disabled="loading"
            >
              <svg
                v-if="loading"
                class="w-4 h-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span>{{ loading ? "Revoking..." : "Revoke Token" }}</span>
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import type { ApiToken } from "~/composables/useTokens";

const props = defineProps<{
  token: ApiToken;
}>();

const emit = defineEmits<{
  close: [];
  confirmed: [];
}>();

const { revokeToken, formatRelativeTime } = useTokens();

const loading = ref(false);
const error = ref<string | null>(null);

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function handleRevoke() {
  loading.value = true;
  error.value = null;

  try {
    await revokeToken(props.token.id);
    emit("confirmed");
    emit("close");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to revoke token";
    console.error("Failed to revoke token:", err);
  } finally {
    loading.value = false;
  }
}

// Close on Escape key
onMounted(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === "Escape" && !loading.value) {
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
