<template>
  <Dialog :open="isOpen" @update:open="handleClose">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle class="text-2xl flex items-center gap-2">
          <span class="text-3xl">✨</span>
          What's New in Kartograph
          <span class="text-sm font-normal text-muted-foreground ml-2"
            >v{{ version }}</span
          >
        </DialogTitle>
        <DialogDescription>
          Here's what's new in this version
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
        <!-- Loading or error state -->
        <div v-if="features.length === 0 && improvements.length === 0 && bugFixes.length === 0 && operationalEntries.length === 0" class="text-center py-8 text-muted-foreground">
          <p>Loading changelog...</p>
        </div>

        <!-- Recent Operational Updates -->
        <div v-if="operationalEntries.length > 0" class="bg-gradient-to-r from-purple-500/10 to-violet-500/10 rounded-lg p-4 border border-purple-500/20">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-foreground">Recent Operational Updates</h3>
          </div>
          <div class="grid gap-y-2.5 pl-2" style="grid-template-columns: auto 1fr;">
            <template v-for="entry in operationalEntries" :key="entry.id">
              <div class="pr-3 whitespace-nowrap">
                <ChangelogEntryTypeBadge :type="entry.type" class="mt-0.5" />
              </div>
              <div class="min-w-0">
                <p class="text-sm text-foreground/90 font-medium">{{ entry.title }}</p>
                <p v-if="entry.description" class="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                  {{ entry.description }}
                </p>
                <p class="text-xs text-muted-foreground mt-1">
                  {{ formatRelativeTime(entry.timestamp) }}
                </p>
              </div>
            </template>
          </div>
        </div>

        <!-- Features -->
        <div v-if="features.length > 0" class="bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-lg p-4 border border-green-500/20">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-foreground">New Features</h3>
          </div>
          <ul class="space-y-2.5">
            <li
              v-for="(feature, index) in features"
              :key="index"
              class="text-sm text-foreground/90 flex items-start gap-3 pl-2"
            >
              <span class="text-green-600 dark:text-green-400 mt-0.5 font-bold">✓</span>
              <span>{{ feature }}</span>
            </li>
          </ul>
        </div>

        <!-- Improvements -->
        <div v-if="improvements.length > 0" class="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-lg p-4 border border-blue-500/20">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-foreground">Improvements</h3>
          </div>
          <ul class="space-y-2.5">
            <li
              v-for="(improvement, index) in improvements"
              :key="index"
              class="text-sm text-foreground/90 flex items-start gap-3 pl-2"
            >
              <span class="text-blue-600 dark:text-blue-400 mt-0.5 font-bold">↑</span>
              <span>{{ improvement }}</span>
            </li>
          </ul>
        </div>

        <!-- Bug Fixes -->
        <div v-if="bugFixes.length > 0" class="bg-gradient-to-r from-orange-500/10 to-amber-500/10 rounded-lg p-4 border border-orange-500/20">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 rounded-full bg-orange-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-foreground">Bug Fixes</h3>
          </div>
          <ul class="space-y-2.5">
            <li
              v-for="(fix, index) in bugFixes"
              :key="index"
              class="text-sm text-foreground/90 flex items-start gap-3 pl-2"
            >
              <span class="text-orange-600 dark:text-orange-400 mt-0.5 font-bold">🐛</span>
              <span>{{ fix }}</span>
            </li>
          </ul>
        </div>
      </div>

      <DialogFooter class="flex-col sm:flex-row gap-3">
        <NuxtLink
          to="/changelog"
          @click="handleClose"
          class="flex-1 px-4 py-2 text-sm bg-muted hover:bg-muted/80 text-foreground rounded-md transition-colors text-center"
        >
          View Full Changelog →
        </NuxtLink>
        <button
          @click="handleClose"
          class="flex-1 px-4 py-2 text-sm bg-primary hover:bg-primary/90 text-primary-foreground rounded-md transition-colors"
        >
          Got it!
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "~/components/ui/dialog";
import ChangelogEntryTypeBadge from "~/components/changelog/EntryTypeBadge.vue";
import changelog from "~/utils/changelog";
import type { ChangelogEntry } from "~/server/db/schema";

interface Props {
  version: string;
  open?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
});

const emit = defineEmits<{
  close: [];
}>();

const isOpen = ref(props.open);

// Watch for prop changes and fetch operational entries when opening
watch(() => props.open, (newVal) => {
  isOpen.value = newVal;
  if (newVal) {
    fetchOperationalEntries();
  }
});

// Load changelog data (from committed TypeScript module)
const features = ref<string[]>(changelog.features || []);
const improvements = ref<string[]>(changelog.improvements || []);
const bugFixes = ref<string[]>(changelog.bugFixes || []);

// Operational changelog entries
const operationalEntries = ref<ChangelogEntry[]>([]);

// Fetch operational entries from last 14 days
async function fetchOperationalEntries() {
  try {
    const fourteenDaysAgo = new Date();
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

    const response = await $fetch("/api/changelog", {
      query: {
        limit: 10, // Show max 10 recent operational updates
        offset: 0,
      },
    });

    // Filter to only show entries created in last 14 days
    // Use createdAt instead of timestamp since timestamp can be manually set
    operationalEntries.value = response.entries.filter((entry: ChangelogEntry) => {
      const entryDate = new Date(entry.createdAt);
      return entryDate >= fourteenDaysAgo;
    });
  } catch (error) {
    console.error("Failed to fetch operational changelog entries:", error);
    operationalEntries.value = [];
  }
}

// Format relative time
function formatRelativeTime(date: Date | string) {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // If timestamp is in the future, show absolute date
  if (diffMs < 0) {
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return diffMinutes <= 1 ? "Just now" : `${diffMinutes} minutes ago`;
    }
    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    const diffWeeks = Math.floor(diffDays / 7);
    return diffWeeks === 1 ? "1 week ago" : `${diffWeeks} weeks ago`;
  }
}

async function handleClose() {
  isOpen.value = false;
  emit("close");

  // Mark changelog as seen
  try {
    await $fetch("/api/user/changelog-seen", {
      method: "POST",
    });
  } catch (error) {
    // Silently fail - not critical if this fails
    console.error("Failed to mark changelog as seen:", error);
  }
}

// Fetch operational entries on mount if already open
onMounted(() => {
  if (props.open) {
    fetchOperationalEntries();
  }
});
</script>
