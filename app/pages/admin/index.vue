<template>
  <div class="h-screen bg-background flex flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b border-border bg-card px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-foreground">Admin Dashboard</h1>
          <p class="text-sm text-muted-foreground">
            User management and system overview
          </p>
        </div>
        <NuxtLink
          to="/"
          class="px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors text-sm font-medium"
        >
          Back to App
        </NuxtLink>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="px-6 py-6 border-b border-border bg-muted/30">
      <AdminStatsCards :stats="dashboardStats" :loading="statsLoading" />
    </div>

    <!-- Tabs Navigation -->
    <div class="border-b border-border bg-card">
      <div class="px-6">
        <nav class="flex gap-8" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="py-4 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2"
            :class="
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            "
          >
            <span>{{ tab.label }}</span>
            <span
              v-if="getTabCount(tab.id) !== null"
              class="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full min-w-[1.5rem]"
              :class="
                activeTab === tab.id
                  ? 'bg-primary/10 text-primary'
                  : 'bg-muted text-muted-foreground'
              "
            >
              {{ getTabCount(tab.id) }}
            </span>
          </button>
        </nav>
      </div>
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-auto px-6 py-6">
      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'">
        <AdminUsageCharts />
      </div>

      <!-- User Management Tab -->
      <div v-else-if="activeTab === 'users'">
        <AdminUserTable
          :users="users"
          :loading="usersLoading"
          :total="totalUsers"
          @update-user="handleUpdateUser"
          @delete-user="handleDeleteUser"
          @refresh="fetchUsers"
        />
      </div>

      <!-- API Tokens Tab -->
      <div v-else-if="activeTab === 'tokens'">
        <AdminApiTokensPanel />
      </div>

      <!-- User Feedback Tab -->
      <div v-else-if="activeTab === 'feedback'">
        <AdminFeedbackPanel />
      </div>

      <!-- Changelog Tab -->
      <div v-else-if="activeTab === 'changelog'">
        <AdminChangelogPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: "admin",
});

// Tab management
const activeTab = ref("overview");

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "User Management" },
  { id: "tokens", label: "API Tokens" },
  { id: "feedback", label: "User Feedback" },
  { id: "changelog", label: "Changelog" },
];

interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  isActive: boolean;
  emailVerified: boolean;
  image: string | null;
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt: Date | null;
  disabledAt: Date | null;
  disabledBy: string | null;
  stats: {
    conversationCount: number;
    messageCount: number;
    apiTokenCount: number;
    activeApiTokenCount: number;
    totalApiCalls: number;
    lastQueryAt: Date | null;
    feedbackCount: number;
    helpfulCount: number;
    unhelpfulCount: number;
    helpfulPercentage: number;
  };
}

interface DashboardStats {
  totalUsers: number;
  activeUsers: number;
  disabledUsers: number;
  adminUsers: number;
  totalConversations: number;
  totalMessages: number;
  totalApiTokens: number;
  activeApiTokens: number;
  totalApiCalls: number;
  stats: {
    usersCreatedLast30Days: number;
    conversationsLast30Days: number;
    messagesLast30Days: number;
    apiCallsLast30Days: number;
  };
  feedback: {
    totalFeedback: number;
    helpfulCount: number;
    unhelpfulCount: number;
    helpfulPercentage: number;
    recentUnhelpfulCount: number;
    feedbackWithTextCount: number;
  };
}

const users = ref<User[]>([]);
const usersLoading = ref(false);
const totalUsers = ref(0);

const dashboardStats = ref<DashboardStats | null>(null);
const statsLoading = ref(false);

const tokenCount = ref(0);
const feedbackCount = ref(0);

// Get count for tab badges
function getTabCount(tabId: string): number | null {
  switch (tabId) {
    case "overview":
      return null; // No count badge for overview
    case "users":
      return totalUsers.value;
    case "tokens":
      return tokenCount.value;
    case "feedback":
      return feedbackCount.value;
    default:
      return null;
  }
}

// Fetch dashboard stats
async function fetchStats() {
  statsLoading.value = true;
  try {
    dashboardStats.value = await $fetch("/api/admin/stats");
    // Update counts for tab badges
    if (dashboardStats.value) {
      tokenCount.value = dashboardStats.value.totalApiTokens;
      feedbackCount.value = dashboardStats.value.feedback.totalFeedback;
    }
  } catch (error) {
    console.error("Failed to fetch stats:", error);
  } finally {
    statsLoading.value = false;
  }
}

// Fetch users
async function fetchUsers() {
  usersLoading.value = true;
  try {
    const response = await $fetch("/api/admin/users", {
      query: {
        limit: 100,
        offset: 0,
        sortBy: "createdAt",
        sortOrder: "desc",
      },
    });
    users.value = response.users;
    totalUsers.value = response.total;
  } catch (error) {
    console.error("Failed to fetch users:", error);
  } finally {
    usersLoading.value = false;
  }
}

// Handle user update (enable/disable, role change)
async function handleUpdateUser(userId: string, updates: any) {
  try {
    await $fetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: updates,
    });
    await fetchUsers();
    await fetchStats();
  } catch (error: any) {
    console.error("Failed to update user:", error);
    alert(error?.data?.message || "Failed to update user");
  }
}

// Handle user deletion
async function handleDeleteUser(userId: string) {
  if (!confirm("Are you sure you want to permanently delete this user?")) {
    return;
  }

  try {
    await $fetch(`/api/admin/users/${userId}?confirm=true`, {
      method: "DELETE",
    });
    await fetchUsers();
    await fetchStats();
  } catch (error: any) {
    console.error("Failed to delete user:", error);
    alert(error?.data?.message || "Failed to delete user");
  }
}

// Load data on mount
onMounted(() => {
  fetchStats();
  fetchUsers();
});
</script>
