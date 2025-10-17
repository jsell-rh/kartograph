<template>
  <div class="bg-card border border-border rounded-lg">
    <!-- Header -->
    <div class="p-6 border-b border-border">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-foreground">User Feedback</h2>
          <p class="text-sm text-muted-foreground mt-1">
            View feedback submitted by users to improve responses
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Filter by rating -->
          <select
            v-model="filterRating"
            @change="fetchFeedback"
            class="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Feedback</option>
            <option value="helpful">Helpful Only</option>
            <option value="unhelpful">Unhelpful Only</option>
          </select>

          <button
            @click="fetchFeedback"
            class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-6">
      <div class="space-y-6">
        <div v-for="i in 3" :key="i" class="animate-pulse">
          <div class="h-4 bg-muted rounded w-1/4 mb-3"></div>
          <div class="h-20 bg-muted rounded mb-2"></div>
          <div class="h-20 bg-muted rounded mb-2"></div>
          <div class="h-12 bg-muted rounded"></div>
        </div>
      </div>
    </div>

    <!-- Feedback List -->
    <div v-else-if="feedback.length > 0" class="divide-y divide-border">
      <div
        v-for="item in feedback"
        :key="item.id"
        class="p-6 hover:bg-muted/20 transition-colors"
      >
        <!-- Feedback Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <!-- Rating Badge -->
            <span
              class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
              :class="
                item.rating === 'helpful'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              "
            >
              <span class="mr-1">
                {{ item.rating === "helpful" ? "👍" : "👎" }}
              </span>
              {{ item.rating === "helpful" ? "Helpful" : "Unhelpful" }}
            </span>

            <!-- User Info -->
            <div class="text-sm">
              <span class="font-medium text-foreground">
                {{ item.user.name }}
              </span>
              <span class="text-muted-foreground">
                ({{ item.user.email }})
              </span>
            </div>
          </div>

          <!-- Timestamp -->
          <div class="text-sm text-muted-foreground">
            {{ formatDate(item.createdAt) }}
          </div>
        </div>

        <!-- User Query -->
        <div class="mb-4">
          <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            User Query
          </div>
          <div
            class="p-4 bg-muted/50 rounded-lg border border-border/50 text-sm text-foreground whitespace-pre-wrap"
          >
            {{ item.userQuery }}
          </div>
        </div>

        <!-- Assistant Response -->
        <div class="mb-4">
          <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Assistant Response
          </div>
          <div
            class="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200/50 dark:border-blue-800/50 text-sm text-foreground whitespace-pre-wrap max-h-64 overflow-y-auto"
          >
            {{ item.assistantResponse }}
          </div>
        </div>

        <!-- Feedback Text (if provided) -->
        <div v-if="item.feedbackText" class="mb-4">
          <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            User Feedback
          </div>
          <div
            class="p-4 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200/50 dark:border-amber-800/50 text-sm text-foreground whitespace-pre-wrap"
          >
            {{ item.feedbackText }}
          </div>
        </div>

        <!-- Conversation Link -->
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
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
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Conversation ID: {{ item.conversationId }}</span>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="p-12 text-center">
      <div class="flex flex-col items-center gap-3">
        <div class="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center">
          <svg
            class="w-8 h-8 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
            />
          </svg>
        </div>
        <div>
          <p class="text-foreground font-medium">No feedback yet</p>
          <p class="text-sm text-muted-foreground mt-1">
            User feedback will appear here when submitted
          </p>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="feedback.length > 0"
      class="p-4 border-t border-border bg-muted/20 flex items-center justify-between"
    >
      <div class="text-sm text-muted-foreground">
        Showing {{ feedback.length }} of {{ total }} items
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
interface FeedbackItem {
  id: string;
  messageId: string;
  conversationId: string;
  rating: "helpful" | "unhelpful";
  feedbackText: string | null;
  userQuery: string;
  assistantResponse: string;
  createdAt: Date;
  user: {
    id: string;
    name: string;
    email: string;
  };
}

const feedback = ref<FeedbackItem[]>([]);
const loading = ref(false);
const total = ref(0);
const hasMore = ref(false);
const offset = ref(0);
const limit = 20;
const filterRating = ref<"all" | "helpful" | "unhelpful">("all");

// Fetch feedback from API
async function fetchFeedback() {
  loading.value = true;
  try {
    const response = await $fetch("/api/admin/feedback", {
      query: {
        limit,
        offset: offset.value,
        rating: filterRating.value !== "all" ? filterRating.value : undefined,
      },
    });
    feedback.value = response.feedback;
    total.value = response.total;
    hasMore.value = response.hasMore;
  } catch (error) {
    console.error("Failed to fetch feedback:", error);
  } finally {
    loading.value = false;
  }
}

// Pagination
function nextPage() {
  if (hasMore.value) {
    offset.value += limit;
    fetchFeedback();
  }
}

function previousPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit);
    fetchFeedback();
  }
}

// Format date
function formatDate(date: Date): string {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;

  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Load feedback on mount
onMounted(() => {
  fetchFeedback();
});
</script>
