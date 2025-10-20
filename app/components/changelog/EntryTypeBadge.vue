<template>
  <span
    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
    :class="badgeClasses"
  >
    <component :is="icon" class="w-3.5 h-3.5" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import {
  Rocket,
  Database,
  Wrench,
  Settings,
  Server,
} from "lucide-vue-next";

interface Props {
  type: "code" | "data" | "maintenance" | "config" | "system";
  size?: "sm" | "md";
}

const props = withDefaults(defineProps<Props>(), {
  size: "md",
});

const config = {
  code: {
    label: "Release",
    icon: Rocket,
    classes:
      "bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20",
  },
  data: {
    label: "Data Update",
    icon: Database,
    classes:
      "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20",
  },
  maintenance: {
    label: "Maintenance",
    icon: Wrench,
    classes:
      "bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20",
  },
  config: {
    label: "Configuration",
    icon: Settings,
    classes:
      "bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20",
  },
  system: {
    label: "System",
    icon: Server,
    classes:
      "bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20",
  },
};

const { label, icon, classes } = config[props.type];
const badgeClasses = classes;
</script>
