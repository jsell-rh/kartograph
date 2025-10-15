<template>
  <div class="min-h-screen bg-background">
    <!-- Header -->
    <header
      class="sticky top-0 z-40 bg-card/80 backdrop-blur-md border-b border-border/40"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-4">
            <NuxtLink
              to="/"
              class="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
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
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              Back
            </NuxtLink>
            <h1 class="text-2xl font-semibold text-foreground">Settings</h1>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Tabs Navigation -->
      <div class="border-b border-border/40 mb-8">
        <nav class="flex gap-8">
          <button
            class="pb-4 px-1 border-b-2 border-primary text-sm font-medium text-foreground transition-colors"
          >
            API Tokens
          </button>
          <!-- Future tabs can go here -->
        </nav>
      </div>

      <!-- API Tokens Tab Content -->
      <div class="space-y-6">
        <!-- Header with Create Button -->
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-semibold text-foreground">API Tokens</h2>
            <p class="text-sm text-muted-foreground mt-1">
              Manage API tokens for accessing the Kartograph MCP server
            </p>
          </div>
          <button
            @click="showCreateModal = true"
            class="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors flex items-center gap-2"
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

        <!-- Token Tabs -->
        <div class="border-b border-border/40">
          <nav class="flex gap-6">
            <button
              @click="activeTokenTab = 'active'"
              :class="[
                'pb-3 px-1 border-b-2 text-sm font-medium transition-colors',
                activeTokenTab === 'active'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              ]"
            >
              Active
              <span
                v-if="activeTokens.length > 0"
                class="ml-2 px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs"
              >
                {{ activeTokens.length }}
              </span>
            </button>
            <button
              @click="activeTokenTab = 'revoked'"
              :class="[
                'pb-3 px-1 border-b-2 text-sm font-medium transition-colors',
                activeTokenTab === 'revoked'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              ]"
            >
              Revoked
              <span
                v-if="revokedTokens.length > 0"
                class="ml-2 px-2 py-0.5 bg-muted text-muted-foreground rounded-full text-xs"
              >
                {{ revokedTokens.length }}
              </span>
            </button>
          </nav>
        </div>

        <!-- Token List - Active Tab -->
        <div v-if="activeTokenTab === 'active'">
          <TokenList
            :tokens="activeTokens"
            :loading="isLoading"
            @create-token="showCreateModal = true"
            @revoke-token="handleRevokeClick"
          />
        </div>

        <!-- Token List - Revoked Tab -->
        <div v-else>
          <TokenList
            :tokens="revokedTokens"
            :loading="isLoading"
            :show-revoked="true"
            @create-token="showCreateModal = true"
            @revoke-token="handleRevokeClick"
          />
        </div>
      </div>
    </main>

    <!-- Modals -->
    <CreateTokenModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @token-created="handleTokenCreated"
    />

    <TokenCreatedModal
      v-if="createdToken"
      :token="createdToken.token"
      :name="createdToken.name"
      :expires-at="createdToken.expiresAt"
      @close="handleTokenCreatedClose"
    />

    <RevokeTokenModal
      v-if="tokenToRevoke"
      :token="tokenToRevoke"
      @close="tokenToRevoke = null"
      @confirmed="handleRevokeConfirmed"
    />
  </div>
</template>

<script setup lang="ts">
import type { ApiToken, CreateTokenResponse } from "~/composables/useTokens";
import TokenList from "~/components/settings/TokenList.vue";
import TokenCard from "~/components/settings/TokenCard.vue";
import CreateTokenModal from "~/components/settings/CreateTokenModal.vue";
import TokenCreatedModal from "~/components/settings/TokenCreatedModal.vue";
import RevokeTokenModal from "~/components/settings/RevokeTokenModal.vue";

const showCreateModal = ref(false);
const createdToken = ref<CreateTokenResponse | null>(null);
const tokenToRevoke = ref<ApiToken | null>(null);
const tokenListRef = ref<InstanceType<typeof TokenList> | null>(null);
const activeTokenTab = ref<"active" | "revoked">("active");

const { success } = useToast();
const { tokens, loading, fetchTokens } = useTokens();

// Track initial load to show skeleton on first render
const isInitialLoad = ref(true);

// Combined loading state (loading OR initial load)
const isLoading = computed(() => loading.value || isInitialLoad.value);

// Separate active and revoked tokens
const activeTokens = computed(() => {
  return tokens.value.filter((token) => !token.revokedAt);
});

const revokedTokens = computed(() => {
  return tokens.value.filter((token) => token.revokedAt);
});

function handleTokenCreated(response: CreateTokenResponse) {
  showCreateModal.value = false;
  createdToken.value = response;
}

async function handleTokenCreatedClose() {
  createdToken.value = null;
  // Refresh the token list after closing the success modal
  await fetchTokens();
}

function handleRevokeClick(token: ApiToken) {
  tokenToRevoke.value = token;
}

async function handleRevokeConfirmed() {
  tokenToRevoke.value = null;
  success("Token revoked successfully");
  // Refresh the token list after revoking
  await fetchTokens();
}

// Fetch tokens on mount
onMounted(async () => {
  await fetchTokens();
  // Clear initial load flag after first fetch completes
  isInitialLoad.value = false;
});
</script>
