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

    <!-- User Management Table -->
    <div class="flex-1 overflow-auto px-6 py-6">
      <AdminUserTable
        :users="users"
        :loading="usersLoading"
        :total="totalUsers"
        @update-user="handleUpdateUser"
        @delete-user="handleDeleteUser"
        @refresh="fetchUsers"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: "admin",
});

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

// Fetch dashboard stats
async function fetchStats() {
  statsLoading.value = true;
  try {
    dashboardStats.value = await $fetch("/api/admin/stats");
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
