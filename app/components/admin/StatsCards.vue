<template>
  <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <div
      v-for="i in 4"
      :key="i"
      class="bg-card border border-border rounded-lg p-6 animate-pulse"
    >
      <div class="h-4 bg-muted rounded w-1/2 mb-4"></div>
      <div class="h-8 bg-muted rounded w-3/4"></div>
    </div>
  </div>

  <div v-else-if="stats" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Total Users -->
    <div
      class="bg-card border border-border rounded-lg p-6 hover:border-primary/50 transition-colors"
    >
      <div class="text-sm font-medium text-muted-foreground mb-2">
        Total Users
      </div>
      <div class="text-3xl font-bold text-foreground">
        {{ stats.totalUsers }}
      </div>
      <div class="text-xs text-muted-foreground mt-2">
        {{ stats.stats.usersCreatedLast30Days }} added last 30 days
      </div>
    </div>

    <!-- Active Users -->
    <div
      class="bg-card border border-border rounded-lg p-6 hover:border-green-500/50 transition-colors"
    >
      <div class="text-sm font-medium text-muted-foreground mb-2">
        Active Users
      </div>
      <div class="text-3xl font-bold text-green-600">
        {{ stats.activeUsers }}
      </div>
      <div class="text-xs text-muted-foreground mt-2">
        {{ stats.disabledUsers }} disabled
      </div>
    </div>

    <!-- Conversations -->
    <div
      class="bg-card border border-border rounded-lg p-6 hover:border-blue-500/50 transition-colors"
    >
      <div class="text-sm font-medium text-muted-foreground mb-2">
        Conversations
      </div>
      <div class="text-3xl font-bold text-blue-600">
        {{ stats.totalConversations }}
      </div>
      <div class="text-xs text-muted-foreground mt-2">
        {{ stats.totalMessages }} messages total
      </div>
    </div>

    <!-- Feedback -->
    <div
      class="bg-card border border-border rounded-lg p-6 hover:border-purple-500/50 transition-colors"
    >
      <div class="text-sm font-medium text-muted-foreground mb-2">
        Feedback
      </div>
      <div class="text-3xl font-bold text-purple-600">
        {{ stats.feedback.helpfulPercentage }}%
      </div>
      <div class="text-xs text-muted-foreground mt-2">
        {{ stats.feedback.totalFeedback }} total submissions
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Stats {
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

interface Props {
  stats: Stats | null;
  loading: boolean;
}

defineProps<Props>();
</script>
