<template>
  <div class="h-full bg-background flex flex-col overflow-hidden">
    <!-- Header with glass-morphism (matching main app style) -->
    <header
      class="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60 shadow-lg shadow-background/5"
    >
      <div class="px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-foreground">Changelog</h1>
          <p class="text-sm text-muted-foreground">
            See what's new in Kartograph
          </p>
        </div>

        <div class="flex items-center gap-3">
          <!-- Filter buttons -->
          <button
            v-for="filter in filters"
            :key="filter.id"
            @click="activeFilter = filter.id"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            :class="
              activeFilter === filter.id
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            "
          >
            {{ filter.label }}
          </button>

          <NuxtLink
            to="/"
            class="px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors text-sm font-medium"
          >
            Back to App
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- Content with top padding for fixed header -->
    <div class="flex-1 overflow-auto px-6 pt-24 pb-6">
      <!-- Loading state -->
      <div v-if="loading" class="max-w-4xl mx-auto space-y-6">
        <div v-for="i in 5" :key="i" class="animate-pulse">
          <div class="h-6 bg-muted rounded w-1/4 mb-4"></div>
          <div class="h-32 bg-muted rounded mb-2"></div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="groupedEntries.length === 0"
        class="max-w-4xl mx-auto text-center py-20"
      >
        <div class="text-6xl mb-4">📝</div>
        <h2 class="text-2xl font-bold text-foreground mb-2">
          No changelog entries yet
        </h2>
        <p class="text-muted-foreground">
          Check back soon for updates and new features!
        </p>
      </div>

      <!-- Timeline -->
      <div v-else class="max-w-4xl mx-auto space-y-8">
        <!-- Grouped by month -->
        <div v-for="group in groupedEntries" :key="group.month">
          <h2
            class="text-lg font-semibold text-foreground mb-4 sticky top-0 bg-background/80 backdrop-blur-sm py-2 z-10"
          >
            {{ group.month }}
          </h2>

          <div class="space-y-4">
            <ChangelogEntryCard
              v-for="entry in group.entries"
              :key="entry.id"
              :entry="entry"
            />
          </div>
        </div>

        <!-- Load More -->
        <div v-if="hasMore" class="text-center py-6">
          <button
            @click="loadMore"
            :disabled="loadingMore"
            class="px-6 py-3 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loadingMore ? "Loading..." : "Load More" }}
          </button>
        </div>

        <!-- End message -->
        <div v-else-if="entries.length > 0" class="text-center py-6 text-muted-foreground">
          <p class="text-sm">You've reached the beginning of our changelog</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import type { ChangelogEntry } from "~/server/db/schema";
import ChangelogEntryCard from "~/components/changelog/EntryCard.vue";

definePageMeta({
  layout: false, // Use custom layout without sidebar
});

// State
const entries = ref<ChangelogEntry[]>([]);
const loading = ref(false);
const loadingMore = ref(false);
const total = ref(0);
const limit = ref(50);
const offset = ref(0);
const hasMore = ref(false);

// Filter
const activeFilter = ref("");

const filters = [
  { id: "", label: "All" },
  { id: "data", label: "Data" },
  { id: "maintenance", label: "Maintenance" },
  { id: "config", label: "Config" },
  { id: "system", label: "System" },
];

// Group entries by month
const groupedEntries = computed(() => {
  const groups: Record<string, ChangelogEntry[]> = {};

  entries.value.forEach((entry) => {
    const date = new Date(entry.timestamp);
    const monthKey = date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
    });

    if (!groups[monthKey]) {
      groups[monthKey] = [];
    }
    groups[monthKey].push(entry);
  });

  // Convert to array and sort by date (newest first)
  return Object.entries(groups).map(([month, entries]) => ({
    month,
    entries,
  }));
});

// Fetch entries
const fetchEntries = async (append = false) => {
  if (append) {
    loadingMore.value = true;
  } else {
    loading.value = true;
    offset.value = 0;
  }

  try {
    const params: any = {
      limit: limit.value,
      offset: append ? offset.value : 0,
    };

    if (activeFilter.value) {
      params.type = activeFilter.value;
    }

    const response = await $fetch("/api/changelog", {
      query: params,
    });

    if (append) {
      entries.value = [...entries.value, ...response.entries];
    } else {
      entries.value = response.entries;
    }

    total.value = response.total;
    hasMore.value = response.hasMore;
  } catch (error) {
    console.error("Failed to fetch changelog entries:", error);
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

// Load more entries
const loadMore = () => {
  offset.value += limit.value;
  fetchEntries(true);
};

// Watch filter changes
watch(activeFilter, () => {
  fetchEntries(false);
});

// Initial fetch
onMounted(() => {
  fetchEntries();
});
</script>
