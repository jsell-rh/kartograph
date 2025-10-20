<template>
  <Dialog :open="true" @update:open="handleClose">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Delete Changelog Entry</DialogTitle>
        <DialogDescription>
          Are you sure you want to delete this entry? This action cannot be
          undone.
        </DialogDescription>
      </DialogHeader>

      <div class="py-4">
        <div class="bg-muted/50 border border-border rounded-lg p-4">
          <div class="flex items-start gap-3">
            <ChangelogEntryTypeBadge :type="entry.type" />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-foreground">
                {{ entry.title }}
              </p>
              <p v-if="entry.description" class="text-xs text-muted-foreground mt-1">
                {{ entry.description.substring(0, 100)
                }}{{ entry.description.length > 100 ? "..." : "" }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <DialogFooter>
        <button
          @click="handleClose"
          type="button"
          class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          @click="handleConfirm"
          type="button"
          :disabled="deleting"
          class="px-4 py-2 text-sm bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ deleting ? "Deleting..." : "Delete Entry" }}
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "~/components/ui/dialog";
import ChangelogEntryTypeBadge from "./EntryTypeBadge.vue";
import type { ChangelogEntry } from "~/server/db/schema";

interface Props {
  entry: ChangelogEntry;
}

defineProps<Props>();
const emit = defineEmits<{
  close: [];
  confirm: [];
}>();

const deleting = ref(false);

const handleConfirm = () => {
  emit("confirm");
};

const handleClose = () => {
  emit("close");
};
</script>
