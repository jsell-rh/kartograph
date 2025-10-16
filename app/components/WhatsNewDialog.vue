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
        <div v-if="features.length === 0 && improvements.length === 0 && bugFixes.length === 0" class="text-center py-8 text-muted-foreground">
          <p>Loading changelog...</p>
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

      <DialogFooter>
        <button
          @click="handleClose"
          class="px-4 py-2 text-sm bg-primary hover:bg-primary/90 text-primary-foreground rounded-md transition-colors"
        >
          Got it!
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "~/components/ui/dialog";

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

// Watch for prop changes
watch(() => props.open, (newVal) => {
  isOpen.value = newVal;
});

// Load changelog from generated JSON file (imported directly, not fetched)
const features = ref<string[]>([]);
const improvements = ref<string[]>([]);
const bugFixes = ref<string[]>([]);

// Import and load changelog when component mounts
onMounted(async () => {
  try {
    // Import the changelog directly so it works regardless of base URL
    // This is bundled with the app rather than fetched from public/
    const changelog = await import("~/public/changelog.json");
    features.value = changelog.default?.features || changelog.features || [];
    improvements.value = changelog.default?.improvements || changelog.improvements || [];
    bugFixes.value = changelog.default?.bugFixes || changelog.bugFixes || [];
  } catch (error) {
    console.error("Failed to load changelog:", error);
    // Fallback to empty arrays
  }
});

function handleClose() {
  isOpen.value = false;
  emit("close");
}
</script>
