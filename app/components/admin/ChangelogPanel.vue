<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-foreground">
          Operational Changelog
        </h2>
        <p class="text-sm text-muted-foreground mt-1">
          Manage operational updates and system events
        </p>
      </div>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2"
      >
        <PlusIcon class="w-4 h-4" />
        Create Entry
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div
        class="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors cursor-pointer"
        @click="filterType = ''"
        :class="filterType === '' ? 'border-primary' : ''"
      >
        <div class="text-sm font-medium text-muted-foreground mb-1">
          Total Entries
        </div>
        <div class="text-2xl font-bold text-foreground">
          {{ stats.total || 0 }}
        </div>
      </div>
      <div
        v-for="type in entryTypes"
        :key="type.value"
        class="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors cursor-pointer"
        @click="filterType = type.value"
        :class="filterType === type.value ? 'border-primary' : ''"
      >
        <div class="text-sm font-medium text-muted-foreground mb-1">
          {{ type.label }}
        </div>
        <div class="text-2xl font-bold" :class="type.colorClass">
          {{ stats.typeCounts?.[type.value] || 0 }}
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <div class="relative flex-1 min-w-[200px]">
        <SearchIcon
          class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search entries..."
          class="w-full pl-10 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          @input="debouncedFetch"
        />
      </div>

      <select
        v-model="filterVisibility"
        @change="fetchEntries"
        class="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">All Visibility</option>
        <option value="public">Public Only</option>
        <option value="admin">Admin Only</option>
      </select>

      <select
        v-model="filterPinned"
        @change="fetchEntries"
        class="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">All</option>
        <option value="true">Pinned Only</option>
        <option value="false">Unpinned Only</option>
      </select>

      <button
        @click="fetchEntries"
        class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
      >
        Refresh
      </button>
    </div>

    <!-- Entries Table -->
    <div class="bg-card border border-border rounded-lg overflow-hidden">
      <!-- Loading State -->
      <div v-if="loading" class="p-6">
        <div class="space-y-4">
          <div v-for="i in 5" :key="i" class="animate-pulse">
            <div class="h-16 bg-muted rounded"></div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="entries.length === 0"
        class="p-12 text-center text-muted-foreground"
      >
        <DatabaseIcon class="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p class="text-lg font-medium">No changelog entries found</p>
        <p class="text-sm mt-2">
          Create your first operational changelog entry to get started
        </p>
      </div>

      <!-- Entries List -->
      <div v-else>
        <table class="w-full">
          <thead class="bg-muted/50 border-b border-border">
            <tr>
              <th
                class="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
              >
                Type
              </th>
              <th
                class="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
              >
                Title
              </th>
              <th
                class="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
              >
                Author
              </th>
              <th
                class="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
              >
                Date
              </th>
              <th
                class="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
              >
                Visibility
              </th>
              <th
                class="px-4 py-3 text-right text-sm font-medium text-muted-foreground"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="entry in entries"
              :key="entry.id"
              class="hover:bg-muted/30 transition-colors"
            >
              <td class="px-4 py-3">
                <ChangelogEntryTypeBadge :type="entry.type" />
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-foreground font-medium">{{
                    entry.title
                  }}</span>
                  <PinIcon
                    v-if="entry.pinned"
                    class="w-3 h-3 text-primary fill-primary"
                  />
                </div>
                <div
                  v-if="entry.description"
                  class="text-xs text-muted-foreground mt-1 line-clamp-1"
                >
                  {{ entry.description.substring(0, 80)
                  }}{{ entry.description.length > 80 ? "..." : "" }}
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-muted-foreground">
                {{ entry.authorName || "System" }}
              </td>
              <td class="px-4 py-3 text-sm text-muted-foreground">
                {{ formatDate(entry.timestamp) }}
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                  :class="
                    entry.visibility === 'public'
                      ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                      : 'bg-orange-500/10 text-orange-600 dark:text-orange-400'
                  "
                >
                  {{ entry.visibility === "public" ? "Public" : "Admin Only" }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="editEntry(entry)"
                    class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                    title="Edit entry"
                  >
                    <EditIcon class="w-4 h-4" />
                  </button>
                  <button
                    @click="confirmDelete(entry)"
                    class="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors"
                    title="Delete entry"
                  >
                    <TrashIcon class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div
          v-if="total > limit"
          class="px-4 py-3 border-t border-border flex items-center justify-between"
        >
          <div class="text-sm text-muted-foreground">
            Showing {{ offset + 1 }} to {{ Math.min(offset + limit, total) }}
            of {{ total }} entries
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="previousPage"
              :disabled="offset === 0"
              class="px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              @click="nextPage"
              :disabled="!hasMore"
              class="px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <ChangelogEntryModal
      v-if="showCreateModal || showEditModal"
      :entry="editingEntry"
      :mode="showEditModal ? 'edit' : 'create'"
      @close="closeModals"
      @save="handleSave"
    />

    <!-- Delete Confirmation Dialog -->
    <ChangelogDeleteDialog
      v-if="showDeleteDialog"
      :entry="deletingEntry"
      @close="showDeleteDialog = false"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import {
  PlusIcon,
  SearchIcon,
  EditIcon,
  TrashIcon,
  PinIcon,
  Database as DatabaseIcon,
} from "lucide-vue-next";
import type { ChangelogEntry } from "~/server/db/schema";
import ChangelogEntryTypeBadge from "../changelog/EntryTypeBadge.vue";

// State
const entries = ref<ChangelogEntry[]>([]);
const loading = ref(false);
const total = ref(0);
const limit = ref(50);
const offset = ref(0);
const hasMore = ref(false);
const stats = ref<{
  total: number;
  typeCounts: Record<string, number>;
}>({ total: 0, typeCounts: {} });

// Filters
const filterType = ref("");
const filterVisibility = ref("");
const filterPinned = ref("");
const searchQuery = ref("");

// Modals
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDeleteDialog = ref(false);
const editingEntry = ref<ChangelogEntry | null>(null);
const deletingEntry = ref<ChangelogEntry | null>(null);

// Entry types configuration
const entryTypes = [
  {
    value: "data",
    label: "Data",
    colorClass: "text-blue-600 dark:text-blue-400",
  },
  {
    value: "maintenance",
    label: "Maintenance",
    colorClass: "text-orange-600 dark:text-orange-400",
  },
  {
    value: "config",
    label: "Config",
    colorClass: "text-green-600 dark:text-green-400",
  },
  {
    value: "system",
    label: "System",
    colorClass: "text-gray-600 dark:text-gray-400",
  },
];

// Fetch entries
const fetchEntries = async () => {
  loading.value = true;
  try {
    const params: any = {
      limit: limit.value,
      offset: offset.value,
    };

    if (filterType.value) params.type = filterType.value;
    if (filterVisibility.value) params.visibility = filterVisibility.value;
    if (filterPinned.value) params.pinned = filterPinned.value;
    if (searchQuery.value) params.search = searchQuery.value;

    const response = await $fetch("/api/admin/changelog", {
      query: params,
    });

    entries.value = response.entries;
    total.value = response.total;
    hasMore.value = response.hasMore;
    stats.value = {
      total: response.total,
      typeCounts: response.stats?.typeCounts || {},
    };
  } catch (error) {
    console.error("Failed to fetch changelog entries:", error);
  } finally {
    loading.value = false;
  }
};

// Debounced fetch for search
let debounceTimeout: ReturnType<typeof setTimeout>;
const debouncedFetch = () => {
  clearTimeout(debounceTimeout);
  debounceTimeout = setTimeout(() => {
    offset.value = 0; // Reset to first page on search
    fetchEntries();
  }, 300);
};

// Pagination
const nextPage = () => {
  if (hasMore.value) {
    offset.value += limit.value;
    fetchEntries();
  }
};

const previousPage = () => {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit.value);
    fetchEntries();
  }
};

// Entry actions
const editEntry = (entry: ChangelogEntry) => {
  editingEntry.value = entry;
  showEditModal.value = true;
};

const confirmDelete = (entry: ChangelogEntry) => {
  deletingEntry.value = entry;
  showDeleteDialog.value = true;
};

const handleSave = async () => {
  closeModals();
  await fetchEntries();
};

const handleDelete = async () => {
  if (!deletingEntry.value) return;

  try {
    await $fetch(`/api/admin/changelog/${deletingEntry.value.id}`, {
      method: "DELETE",
    });
    showDeleteDialog.value = false;
    deletingEntry.value = null;
    await fetchEntries();
  } catch (error) {
    console.error("Failed to delete changelog entry:", error);
  }
};

const closeModals = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  editingEntry.value = null;
};

// Format date helper
const formatDate = (date: Date | string) => {
  const d = new Date(date);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Watch filter type for instant filter
watch(filterType, () => {
  offset.value = 0;
  fetchEntries();
});

// Initial fetch
onMounted(() => {
  fetchEntries();
});
</script>
