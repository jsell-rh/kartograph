<template>
  <div
    class="group relative bg-card border border-border rounded-lg p-5 hover:border-primary/30 transition-all duration-200 overflow-hidden"
    :class="borderColorClass"
  >
    <!-- Colored left border accent -->
    <div
      class="absolute left-0 top-0 bottom-0 w-1 transition-all duration-200 group-hover:w-1.5"
      :class="accentColorClass"
    ></div>

    <!-- Content -->
    <div class="space-y-3">
      <!-- Header: Type badge, pin icon, timestamp -->
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-2">
          <ChangelogEntryTypeBadge :type="entry.type" />
          <PinIcon
            v-if="entry.pinned"
            class="w-3.5 h-3.5 text-primary fill-primary"
          />
        </div>
        <time class="text-xs text-muted-foreground whitespace-nowrap">
          {{ formatTimestamp(entry.timestamp) }}
        </time>
      </div>

      <!-- Title -->
      <h3 class="text-base font-semibold text-foreground leading-snug">
        {{ entry.title }}
      </h3>

      <!-- Description (markdown) -->
      <div
        v-if="entry.description"
        class="prose prose-sm dark:prose-invert max-w-none text-muted-foreground"
        v-html="renderedDescription"
      ></div>

      <!-- Metadata badges (for data updates) -->
      <div v-if="hasMetadata" class="flex flex-wrap gap-2 pt-2">
        <span
          v-if="metadata.affectedRecords"
          class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
        >
          <DatabaseIcon class="w-3 h-3 mr-1.5" />
          {{ formatNumber(metadata.affectedRecords) }} records
        </span>
        <span
          v-if="metadata.dataSource"
          class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-muted text-muted-foreground border border-border"
        >
          <ServerIcon class="w-3 h-3 mr-1.5" />
          {{ metadata.dataSource }}
        </span>
      </div>

      <!-- Author (if available) -->
      <div v-if="entry.authorName" class="flex items-center gap-2 text-xs text-muted-foreground pt-1">
        <UserIcon class="w-3 h-3" />
        <span>{{ entry.authorName }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { PinIcon, Database as DatabaseIcon, Server as ServerIcon, User as UserIcon } from "lucide-vue-next";
import ChangelogEntryTypeBadge from "./EntryTypeBadge.vue";
import type { ChangelogEntry } from "~/server/db/schema";
import { marked } from "marked";

interface Props {
  entry: ChangelogEntry;
}

const props = defineProps<Props>();

// Type-based styling
const borderColorClass = computed(() => {
  switch (props.entry.type) {
    case "code":
      return "hover:bg-purple-500/5";
    case "data":
      return "hover:bg-blue-500/5";
    case "maintenance":
      return "hover:bg-orange-500/5";
    case "config":
      return "hover:bg-green-500/5";
    case "system":
      return "hover:bg-gray-500/5";
    default:
      return "";
  }
});

const accentColorClass = computed(() => {
  switch (props.entry.type) {
    case "code":
      return "bg-purple-500";
    case "data":
      return "bg-blue-500";
    case "maintenance":
      return "bg-orange-500";
    case "config":
      return "bg-green-500";
    case "system":
      return "bg-gray-500";
    default:
      return "bg-primary";
  }
});

// Metadata handling
const metadata = computed(() => (props.entry.metadata || {}) as any);
const hasMetadata = computed(() => {
  return metadata.value.affectedRecords || metadata.value.dataSource;
});

// Markdown rendering
const renderedDescription = computed(() => {
  if (!props.entry.description) return "";
  try {
    return marked.parse(props.entry.description, { breaks: true });
  } catch (error) {
    console.error("Failed to render markdown:", error);
    return props.entry.description;
  }
});

// Format timestamp
const formatTimestamp = (date: Date | string) => {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // If within last 7 days, show relative time
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
  }

  // Otherwise show formatted date
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Format large numbers
const formatNumber = (num: number) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toLocaleString();
};
</script>

<style scoped>
/* Ensure proper prose styling for markdown content */
:deep(.prose) {
  @apply text-sm;
}

:deep(.prose p) {
  @apply my-2;
}

:deep(.prose ul),
:deep(.prose ol) {
  @apply my-2;
}

:deep(.prose li) {
  @apply my-1;
}

:deep(.prose code) {
  @apply bg-muted px-1.5 py-0.5 rounded text-xs;
}

:deep(.prose pre) {
  @apply bg-muted p-3 rounded-lg overflow-x-auto;
}

:deep(.prose a) {
  @apply text-primary hover:underline;
}

:deep(.prose h1),
:deep(.prose h2),
:deep(.prose h3),
:deep(.prose h4) {
  @apply text-foreground font-semibold mt-4 mb-2;
}

:deep(.prose blockquote) {
  @apply border-l-4 border-muted-foreground/30 pl-4 italic;
}
</style>
