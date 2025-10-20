<template>
  <Dialog :open="true" @update:open="handleClose">
    <DialogContent class="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>
          {{ mode === "create" ? "Create Changelog Entry" : "Edit Changelog Entry" }}
        </DialogTitle>
        <DialogDescription>
          {{
            mode === "create"
              ? "Add a new operational update or system event"
              : "Update the changelog entry details"
          }}
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-4">
        <!-- Type -->
        <div>
          <label class="text-sm font-medium text-foreground mb-2 block">
            Type <span class="text-destructive">*</span>
          </label>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="type in entryTypes"
              :key="type.value"
              @click="formData.type = type.value"
              class="px-4 py-3 rounded-lg border-2 transition-all flex items-center gap-2"
              :class="
                formData.type === type.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              "
            >
              <component :is="type.icon" class="w-4 h-4" :class="type.iconColor" />
              <span class="text-sm font-medium">{{ type.label }}</span>
            </button>
          </div>
        </div>

        <!-- Title -->
        <div>
          <label for="title" class="text-sm font-medium text-foreground mb-2 block">
            Title <span class="text-destructive">*</span>
          </label>
          <input
            id="title"
            v-model="formData.title"
            type="text"
            placeholder="e.g., Loaded 2,500 new service mappings"
            maxlength="255"
            class="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            :class="errors.title ? 'border-destructive' : ''"
          />
          <p v-if="errors.title" class="text-xs text-destructive mt-1">
            {{ errors.title }}
          </p>
          <p class="text-xs text-muted-foreground mt-1">
            {{ formData.title.length }}/255 characters
          </p>
        </div>

        <!-- Description -->
        <div>
          <label
            for="description"
            class="text-sm font-medium text-foreground mb-2 block"
          >
            Description (Markdown supported)
          </label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="4"
            placeholder="Optional detailed description in markdown..."
            class="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-y"
          />
          <p class="text-xs text-muted-foreground mt-1">
            Supports markdown formatting
          </p>
        </div>

        <!-- Metadata (conditional based on type) -->
        <div v-if="formData.type === 'data'">
          <label class="text-sm font-medium text-foreground mb-2 block">
            Data Update Details
          </label>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label
                for="affectedRecords"
                class="text-xs text-muted-foreground mb-1 block"
              >
                Records Affected
              </label>
              <input
                id="affectedRecords"
                v-model.number="formData.metadata.affectedRecords"
                type="number"
                placeholder="e.g., 2500"
                class="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label
                for="dataSource"
                class="text-xs text-muted-foreground mb-1 block"
              >
                Data Source
              </label>
              <input
                id="dataSource"
                v-model="formData.metadata.dataSource"
                type="text"
                placeholder="e.g., prod-cluster-01"
                class="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </div>

        <!-- Timestamp -->
        <div>
          <label for="timestamp" class="text-sm font-medium text-foreground mb-2 block">
            Date & Time
          </label>
          <input
            id="timestamp"
            v-model="formData.timestamp"
            type="datetime-local"
            class="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <p class="text-xs text-muted-foreground mt-1">
            Leave empty to use current date/time
          </p>
        </div>

        <!-- Options -->
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <input
              id="pinned"
              v-model="formData.pinned"
              type="checkbox"
              class="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary"
            />
            <label for="pinned" class="text-sm text-foreground cursor-pointer">
              Pin to top of changelog
            </label>
          </div>

          <div class="flex items-center gap-3">
            <input
              id="visibility"
              v-model="isPublic"
              type="checkbox"
              class="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary"
            />
            <label for="visibility" class="text-sm text-foreground cursor-pointer">
              Make visible to all users (uncheck for admin-only)
            </label>
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
          @click="handleSave"
          type="button"
          :disabled="saving"
          class="px-4 py-2 text-sm bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? "Saving..." : mode === "create" ? "Create Entry" : "Save Changes" }}
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "~/components/ui/dialog";
import {
  Database,
  Wrench,
  Settings,
  Server,
} from "lucide-vue-next";
import type { ChangelogEntry } from "~/server/db/schema";

interface Props {
  entry?: ChangelogEntry | null;
  mode: "create" | "edit";
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  save: [];
}>();

const saving = ref(false);
const errors = reactive<{ title?: string }>({});

const entryTypes = [
  {
    value: "data",
    label: "Data Update",
    icon: Database,
    iconColor: "text-blue-600 dark:text-blue-400",
  },
  {
    value: "maintenance",
    label: "Maintenance",
    icon: Wrench,
    iconColor: "text-orange-600 dark:text-orange-400",
  },
  {
    value: "config",
    label: "Configuration",
    icon: Settings,
    iconColor: "text-green-600 dark:text-green-400",
  },
  {
    value: "system",
    label: "System Event",
    icon: Server,
    iconColor: "text-gray-600 dark:text-gray-400",
  },
];

const formData = reactive({
  type: (props.entry?.type as any) || "data",
  title: props.entry?.title || "",
  description: props.entry?.description || "",
  timestamp: props.entry?.timestamp
    ? new Date(props.entry.timestamp).toISOString().slice(0, 16)
    : "",
  metadata: {
    affectedRecords: (props.entry?.metadata as any)?.affectedRecords || null,
    dataSource: (props.entry?.metadata as any)?.dataSource || "",
    severity: (props.entry?.metadata as any)?.severity || "info",
  },
  pinned: props.entry?.pinned || false,
  visibility: props.entry?.visibility || "public",
});

const isPublic = computed({
  get: () => formData.visibility === "public",
  set: (value) => {
    formData.visibility = value ? "public" : "admin";
  },
});

const validate = () => {
  errors.title = "";

  if (!formData.title.trim()) {
    errors.title = "Title is required";
    return false;
  }

  if (formData.title.length > 255) {
    errors.title = "Title must be less than 255 characters";
    return false;
  }

  return true;
};

const handleSave = async () => {
  if (!validate()) return;

  saving.value = true;
  try {
    const payload = {
      type: formData.type,
      title: formData.title.trim(),
      description: formData.description.trim() || null,
      timestamp: formData.timestamp ? new Date(formData.timestamp).toISOString() : null,
      metadata: {
        affectedRecords: formData.metadata.affectedRecords || undefined,
        dataSource: formData.metadata.dataSource || undefined,
        severity: formData.metadata.severity,
      },
      pinned: formData.pinned,
      visibility: formData.visibility,
    };

    if (props.mode === "edit" && props.entry) {
      await $fetch(`/api/admin/changelog/${props.entry.id}`, {
        method: "PATCH",
        body: payload,
      });
    } else {
      await $fetch("/api/admin/changelog", {
        method: "POST",
        body: payload,
      });
    }

    emit("save");
  } catch (error: any) {
    console.error("Failed to save changelog entry:", error);
    alert(error.data?.message || "Failed to save changelog entry");
  } finally {
    saving.value = false;
  }
};

const handleClose = () => {
  emit("close");
};
</script>
