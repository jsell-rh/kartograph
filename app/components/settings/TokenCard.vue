<template>
  <div
    class="bg-card/60 backdrop-blur-xl border border-border/30 rounded-lg p-4 hover:border-border/50 hover:bg-card/70 transition-all shadow-sm hover:shadow-md"
  >
    <div class="flex items-center justify-between gap-4">
      <!-- Token Info -->
      <div class="flex-1 min-w-0 flex items-center gap-4">
        <!-- Status Indicator & Name -->
        <div class="flex items-center gap-2.5 min-w-0 flex-1">
          <div
            :class="[
              'w-2 h-2 rounded-full flex-shrink-0',
              isExpired
                ? 'bg-destructive'
                : isNeverUsed
                  ? 'bg-muted-foreground/50'
                  : 'bg-green-500',
            ]"
            :title="statusText"
          />
          <h3 class="text-base font-semibold text-foreground truncate">
            {{ token.name }}
          </h3>
        </div>

        <!-- Metadata - Horizontal -->
        <div class="hidden md:flex items-center gap-6 text-xs">
          <div class="flex items-center gap-1.5 text-muted-foreground">
            <span class="opacity-60">Queries:</span>
            <span class="font-medium text-foreground">{{
              token.totalQueries.toLocaleString()
            }}</span>
          </div>
          <div class="flex items-center gap-1.5 text-muted-foreground">
            <span class="opacity-60">Last used:</span>
            <span class="font-medium text-foreground">{{
              formatRelativeTime(token.lastUsedAt)
            }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="opacity-60 text-muted-foreground">Expires:</span>
            <span
              :class="[
                'font-medium',
                isExpired ? 'text-destructive' : 'text-foreground',
              ]"
            >
              {{ formatExpiryDate(token.expiresAt) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-2">
        <button
          v-if="!isExpired && !token.revokedAt"
          @click="$emit('revoke')"
          class="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
          title="Revoke token"
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
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
        <div
          v-if="token.revokedAt"
          class="flex items-center gap-1.5 text-xs text-muted-foreground px-3 py-1.5 bg-muted/50 rounded-md"
        >
          <svg
            class="w-3.5 h-3.5"
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
          <span>Revoked</span>
        </div>
      </div>
    </div>

    <!-- Mobile Metadata (shown on small screens) -->
    <div
      class="md:hidden mt-3 pt-3 border-t border-border/30 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground"
    >
      <div class="flex items-center gap-1">
        <span class="opacity-60">Queries:</span>
        <span class="font-medium text-foreground">{{
          token.totalQueries.toLocaleString()
        }}</span>
      </div>
      <div class="flex items-center gap-1">
        <span class="opacity-60">Last used:</span>
        <span class="font-medium text-foreground">{{
          formatRelativeTime(token.lastUsedAt)
        }}</span>
      </div>
      <div class="flex items-center gap-1">
        <span class="opacity-60">Expires:</span>
        <span
          :class="[
            'font-medium',
            isExpired ? 'text-destructive' : 'text-foreground',
          ]"
        >
          {{ formatExpiryDate(token.expiresAt) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ApiToken } from "~/composables/useTokens";

const props = defineProps<{
  token: ApiToken;
}>();

defineEmits<{
  revoke: [];
}>();

const { formatRelativeTime, formatExpiryDate } = useTokens();

const isExpired = computed(() => {
  const expiryDate = new Date(props.token.expiresAt);
  return expiryDate < new Date();
});

const isNeverUsed = computed(() => {
  return !props.token.lastUsedAt;
});

const statusText = computed(() => {
  if (props.token.revokedAt) return "Revoked";
  if (isExpired.value) return "Expired";
  if (isNeverUsed.value) return "Never used";
  return "Active";
});

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
</script>
