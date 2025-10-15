<template>
  <div class="min-h-screen flex flex-col">
    <div class="flex-1">
      <NuxtPage />
    </div>
    <footer
      class="py-2 px-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-800"
    >
      <div class="max-w-7xl mx-auto flex justify-between items-center">
        <span>{{ config.public.appName }}</span>
        <span class="font-mono">v{{ config.public.version }}</span>
      </div>
    </footer>
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig();
</script>
