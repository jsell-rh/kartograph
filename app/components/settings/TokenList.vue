<template>
  <div class="space-y-4">
    <!-- Loading State -->
    <div v-if="loading" class="grid gap-4">
      <!-- Token skeleton cards -->
      <div
        v-for="i in 3"
        :key="i"
        class="bg-card/80 backdrop-blur-md border border-border/40 rounded-lg p-6 animate-pulse"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex-1">
            <div class="h-5 bg-muted/50 rounded w-1/3 mb-3"></div>
            <div class="h-4 bg-muted/40 rounded w-2/3"></div>
          </div>
          <div class="h-9 w-20 bg-muted/50 rounded"></div>
        </div>

        <!-- Details grid -->
        <div class="grid grid-cols-2 gap-4 pt-4 border-t border-border/40">
          <div>
            <div class="h-3 bg-muted/40 rounded w-16 mb-2"></div>
            <div class="h-4 bg-muted/50 rounded w-24"></div>
          </div>
          <div>
            <div class="h-3 bg-muted/40 rounded w-20 mb-2"></div>
            <div class="h-4 bg-muted/50 rounded w-28"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div
      v-else-if="error"
      class="bg-destructive/10 border border-destructive/20 rounded-lg p-4"
    >
      <div class="flex items-center gap-2 text-destructive">
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
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span class="font-medium">{{ error }}</span>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="displayTokens.length === 0"
      class="bg-card/80 backdrop-blur-md border border-border/40 rounded-lg p-12 text-center"
    >
      <svg
        class="w-16 h-16 mx-auto text-muted-foreground/50 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
        />
      </svg>
      <h3 class="text-lg font-medium text-foreground mb-2">
        {{ showRevoked ? "No Revoked Tokens" : "No API Tokens" }}
      </h3>
      <p class="text-sm text-muted-foreground mb-6">
        {{
          showRevoked
            ? "Revoked tokens will appear here"
            : "Create your first API token to start using the Kartograph MCP server"
        }}
      </p>
      <button
        v-if="!showRevoked"
        @click="$emit('create-token')"
        class="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors inline-flex items-center gap-2"
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
            d="M12 4v16m8-8H4"
          />
        </svg>
        Create Token
      </button>
    </div>

    <!-- Token Cards Grid -->
    <div v-else class="grid gap-4">
      <TokenCard
        v-for="token in displayTokens"
        :key="token.id"
        :token="token"
        @revoke="$emit('revoke-token', token)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ApiToken } from "~/composables/useTokens";
import TokenCard from "./TokenCard.vue";

const props = defineProps<{
  tokens?: ApiToken[];
  showRevoked?: boolean;
  loading?: boolean;
}>();

defineEmits<{
  "create-token": [];
  "revoke-token": [token: ApiToken];
}>();

const {
  tokens: allTokens,
  loading: internalLoading,
  error,
  fetchTokens,
} = useTokens();

// Use provided tokens or fetch all tokens
const displayTokens = computed(() =>
  props.tokens !== undefined ? props.tokens : allTokens.value,
);

// Use provided loading state or internal loading state
const loading = computed(() =>
  props.loading !== undefined ? props.loading : internalLoading.value,
);

// Fetch tokens on mount if not provided
onMounted(async () => {
  if (props.tokens === undefined) {
    await fetchTokens();
  }
});
</script>
