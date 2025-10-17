<template>
  <div class="bg-card border border-border rounded-lg">
    <!-- Header -->
    <div class="p-6 border-b border-border">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-foreground">User Management</h2>
        <button
          @click="emit('refresh')"
          class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
        >
          Refresh
        </button>
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

    <!-- Users Table -->
    <div v-else-if="users.length > 0" class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-muted/50 border-b border-border">
          <tr>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              User
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Role
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Status
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Activity
            </th>
            <th class="text-left px-6 py-3 text-sm font-semibold text-foreground">
              Last Login
            </th>
            <th class="text-right px-6 py-3 text-sm font-semibold text-foreground">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="user in users"
            :key="user.id"
            class="border-b border-border hover:bg-muted/30 transition-colors"
          >
            <!-- User Info -->
            <td class="px-6 py-4">
              <div>
                <div class="font-medium text-foreground">{{ user.name }}</div>
                <div class="text-sm text-muted-foreground">{{ user.email }}</div>
              </div>
            </td>

            <!-- Role -->
            <td class="px-6 py-4">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="
                  user.role === 'admin'
                    ? 'bg-purple-100 text-purple-800'
                    : 'bg-gray-100 text-gray-800'
                "
              >
                {{ user.role }}
              </span>
            </td>

            <!-- Status -->
            <td class="px-6 py-4">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="
                  user.isActive
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                "
              >
                {{ user.isActive ? "Active" : "Disabled" }}
              </span>
            </td>

            <!-- Activity -->
            <td class="px-6 py-4">
              <div class="text-sm text-muted-foreground">
                {{ user.stats.conversationCount }} conversations •
                {{ user.stats.messageCount }} messages
              </div>
            </td>

            <!-- Last Login -->
            <td class="px-6 py-4">
              <div
                class="text-sm text-muted-foreground"
                :title="getFullTimestamp(user.lastLoginAt)"
              >
                {{ formatDate(user.lastLoginAt) }}
              </div>
            </td>

            <!-- Actions -->
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <!-- Toggle Active/Disabled -->
                <button
                  v-if="user.isActive"
                  @click="emit('updateUser', user.id, { isActive: false })"
                  class="px-3 py-1.5 text-sm bg-red-100 text-red-800 hover:bg-red-200 rounded transition-colors"
                >
                  Disable
                </button>
                <button
                  v-else
                  @click="emit('updateUser', user.id, { isActive: true })"
                  class="px-3 py-1.5 text-sm bg-green-100 text-green-800 hover:bg-green-200 rounded transition-colors"
                >
                  Enable
                </button>

                <!-- Toggle Role -->
                <button
                  v-if="user.role === 'user'"
                  @click="emit('updateUser', user.id, { role: 'admin' })"
                  class="px-3 py-1.5 text-sm bg-purple-100 text-purple-800 hover:bg-purple-200 rounded transition-colors"
                >
                  Make Admin
                </button>
                <button
                  v-else
                  @click="emit('updateUser', user.id, { role: 'user' })"
                  class="px-3 py-1.5 text-sm bg-gray-100 text-gray-800 hover:bg-gray-200 rounded transition-colors"
                >
                  Remove Admin
                </button>

                <!-- Delete -->
                <button
                  @click="emit('deleteUser', user.id)"
                  class="px-3 py-1.5 text-sm bg-red-50 text-red-700 hover:bg-red-100 rounded transition-colors"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else class="p-12 text-center text-muted-foreground">
      No users found
    </div>
  </div>
</template>

<script setup lang="ts">
interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  isActive: boolean;
  lastLoginAt: Date | null;
  stats: {
    conversationCount: number;
    messageCount: number;
    apiTokenCount: number;
    activeApiTokenCount: number;
    totalApiCalls: number;
    feedbackCount: number;
    helpfulCount: number;
    unhelpfulCount: number;
    helpfulPercentage: number;
  };
}

interface Props {
  users: User[];
  loading: boolean;
  total: number;
}

defineProps<Props>();

const emit = defineEmits<{
  updateUser: [userId: string, updates: any];
  deleteUser: [userId: string];
  refresh: [];
}>();

// Format date for last login display
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
  if (!date) return "User has never logged in";

  return new Date(date).toLocaleString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
</script>
