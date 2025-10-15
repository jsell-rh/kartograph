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
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-semibold text-foreground">
                Create API Token
              </h2>
              <button
                @click="$emit('close')"
                class="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleSubmit" class="px-6 py-6 space-y-5">
            <!-- Token Name -->
            <div>
              <label
                for="token-name"
                class="block text-sm font-medium text-foreground mb-2"
              >
                Token Name <span class="text-destructive">*</span>
              </label>
              <input
                id="token-name"
                v-model="form.name"
                type="text"
                placeholder="e.g., Claude Code, My Local Agent"
                maxlength="100"
                required
                class="w-full px-3 py-2 bg-background border border-border/40 rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              />
              <p class="mt-1 text-xs text-muted-foreground">
                A descriptive name to identify where this token is used
              </p>
            </div>

            <!-- Expiry Days -->
            <div>
              <label
                for="token-expiry"
                class="block text-sm font-medium text-foreground mb-2"
              >
                Expires In
              </label>
              <select
                id="token-expiry"
                v-model="form.expiryDays"
                class="w-full px-3 py-2 bg-background border border-border/40 rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              >
                <option :value="30">30 days</option>
                <option :value="90">90 days (default)</option>
                <option :value="180">180 days (6 months)</option>
                <option :value="365">365 days (1 year)</option>
              </select>
              <p class="mt-1 text-xs text-muted-foreground">
                Token will automatically expire after this period
              </p>
            </div>

            <!-- Info Box -->
            <div
              class="bg-blue-500/10 border border-blue-500/20 rounded-md p-3"
            >
              <div class="flex gap-2">
                <svg
                  class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div class="text-xs text-blue-800">
                  You'll only be able to view the token once after creation.
                  Store it securely.
                </div>
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

            <!-- Actions -->
            <div class="flex gap-3 pt-2">
              <button
                type="button"
                @click="$emit('close')"
                class="flex-1 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md transition-colors"
                :disabled="loading"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                :disabled="loading || !form.name.trim()"
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
                <span>{{ loading ? "Creating..." : "Create Token" }}</span>
              </button>
            </div>
          </form>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import type { CreateTokenResponse } from "~/composables/useTokens";

const emit = defineEmits<{
  close: [];
  "token-created": [response: CreateTokenResponse];
}>();

const { createToken } = useTokens();

const form = reactive({
  name: "",
  expiryDays: 90,
});

const loading = ref(false);
const error = ref<string | null>(null);

async function handleSubmit() {
  if (!form.name.trim()) {
    error.value = "Token name is required";
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const response = await createToken(form.name, form.expiryDays);
    emit("token-created", response);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to create token";
    console.error("Failed to create token:", err);
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
