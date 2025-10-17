<template>
  <div class="bg-card border border-border rounded-lg">
    <!-- Header -->
    <div class="p-6 border-b border-border">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-foreground">API Tokens</h2>
          <p class="text-sm text-muted-foreground mt-1">
            Manage all API tokens across users
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Filter by status -->
          <select
            v-model="filterStatus"
            @change="fetchTokens"
            class="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Tokens</option>
            <option value="active">Active Only</option>
            <option value="revoked">Revoked Only</option>
            <option value="expired">Expired Only</option>
          </select>

          <button
            @click="fetchTokens"
            class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="p-6 border-b border-border bg-muted/20">
      <div class="grid grid-cols-4 gap-4">
        <div class="bg-card p-4 rounded-lg border border-border">
          <div class="text-2xl font-bold text-foreground">
            {{ stats.totalTokens }}
          </div>
          <div class="text-sm text-muted-foreground">Total Tokens</div>
        </div>
        <div class="bg-card p-4 rounded-lg border border-green-200">
          <div class="text-2xl font-bold text-green-600">
            {{ stats.activeTokens }}
          </div>
          <div class="text-sm text-muted-foreground">Active</div>
        </div>
        <div class="bg-card p-4 rounded-lg border border-orange-200">
          <div class="text-2xl font-bold text-orange-600">
            {{ stats.expiredTokens }}
          </div>
          <div class="text-sm text-muted-foreground">Expired</div>
        </div>
        <div class="bg-card p-4 rounded-lg border border-red-200">
          <div class="text-2xl font-bold text-red-600">
            {{ stats.revokedTokens }}
          </div>
          <div class="text-sm text-muted-foreground">Revoked</div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-6">
      <div class="space-y-4">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 animate-pulse">
          <div class="h-10 bg-muted rounded w-full"></div>
        </div>
      </div>
    </div>

    <!-- Tokens Table -->
    <div v-else-if="tokens.length > 0" class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-muted/50 border-b border-border">
          <tr>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Token Name
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Owner
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Usage
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Last Used
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Expires
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="token in tokens"
            :key="token.id"
            class="border-b border-border hover:bg-muted/30 transition-colors"
          >
            <!-- Token Name -->
            <td class="px-6 py-4">
              <div class="font-medium text-foreground">{{ token.name }}</div>
              <div class="text-xs text-muted-foreground font-mono">
                {{ token.id.substring(0, 8) }}...
              </div>
            </td>

            <!-- Owner -->
            <td class="px-6 py-4">
              <div class="text-sm text-foreground">{{ token.user.name }}</div>
              <div class="text-xs text-muted-foreground">
                {{ token.user.email }}
              </div>
            </td>

            <!-- Usage -->
            <td class="px-6 py-4">
              <div class="text-sm font-medium text-foreground">
                {{ token.totalQueries.toLocaleString() }}
              </div>
              <div class="text-xs text-muted-foreground">queries</div>
            </td>

            <!-- Last Used -->
            <td class="px-6 py-4">
              <div
                class="text-sm text-muted-foreground"
                :title="getFullTimestamp(token.lastUsedAt)"
              >
                {{ formatDate(token.lastUsedAt) }}
              </div>
            </td>

            <!-- Expires -->
            <td class="px-6 py-4">
              <div
                class="text-sm text-muted-foreground"
                :title="getFullTimestamp(token.expiresAt)"
              >
                {{ formatDate(token.expiresAt) }}
              </div>
            </td>

            <!-- Status -->
            <td class="px-6 py-4">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="getStatusClass(token.status)"
              >
                {{ token.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else class="p-12 text-center text-muted-foreground">
      No tokens found
    </div>

    <!-- Pagination -->
    <div
      v-if="tokens.length > 0"
      class="p-4 border-t border-border bg-muted/20 flex items-center justify-between"
    >
      <div class="text-sm text-muted-foreground">
        Showing {{ tokens.length }} of {{ total }} tokens
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="previousPage"
          :disabled="offset === 0"
          class="px-3 py-1.5 text-sm bg-background border border-border rounded hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          @click="nextPage"
          :disabled="!hasMore"
          class="px-3 py-1.5 text-sm bg-background border border-border rounded hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Token {
  id: string;
  name: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
  totalQueries: number;
  lastUsedAt: Date | null;
  expiresAt: Date;
  createdAt: Date;
  revokedAt: Date | null;
  status: "active" | "expired" | "revoked";
}

interface TokenStats {
  totalTokens: number;
  activeTokens: number;
  revokedTokens: number;
  expiredTokens: number;
}

const tokens = ref<Token[]>([]);
const loading = ref(false);
const total = ref(0);
const hasMore = ref(false);
const offset = ref(0);
const limit = 20;
const filterStatus = ref<"all" | "active" | "revoked" | "expired">("all");
const stats = ref<TokenStats>({
  totalTokens: 0,
  activeTokens: 0,
  revokedTokens: 0,
  expiredTokens: 0,
});

// Fetch tokens from API
async function fetchTokens() {
  loading.value = true;
  try {
    const response = await $fetch("/api/admin/tokens", {
      query: {
        limit,
        offset: offset.value,
        status: filterStatus.value !== "all" ? filterStatus.value : undefined,
      },
    });
    tokens.value = response.tokens;
    total.value = response.total;
    hasMore.value = response.hasMore;
    stats.value = response.stats;
  } catch (error) {
    console.error("Failed to fetch tokens:", error);
  } finally {
    loading.value = false;
  }
}

// Pagination
function nextPage() {
  if (hasMore.value) {
    offset.value += limit;
    fetchTokens();
  }
}

function previousPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit);
    fetchTokens();
  }
}

// Format date
function formatDate(date: Date | null): string {
  if (!date) return "Never";

  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Get full timestamp for tooltip
function getFullTimestamp(date: Date | null): string {
  if (!date) return "Never used";

  return new Date(date).toLocaleString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// Get status badge class
function getStatusClass(status: string): string {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800";
    case "expired":
      return "bg-orange-100 text-orange-800";
    case "revoked":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

// Load tokens on mount
onMounted(() => {
  fetchTokens();
});
</script>
