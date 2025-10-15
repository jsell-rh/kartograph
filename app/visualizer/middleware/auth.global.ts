/**
 * Global client-side auth middleware
 * Redirects unauthenticated users to login page
 * Uses Pinia auth store for optimistic checks (no reload flicker)
 */

import { useAuthStore } from "~/stores/auth";

export default defineNuxtRouteMiddleware(async (to) => {
  // Skip on server-side
  if (process.server) return;

  // Allow access to login page
  if (to.path === "/login") return;

  const authStore = useAuthStore();

  // Initialize auth on first access (loads from localStorage)
  if (!authStore.lastSync) {
    await authStore.initializeAuth();
  }

  // Optimistic check - use cached auth state for instant navigation
  if (authStore.isAuthenticated) {
    // Sync with server in background (non-blocking)
    // This validates the session without blocking navigation
    authStore.syncWithServer().catch(() => {
      // If validation fails, redirect to login
      navigateTo("/login");
    });
    return;
  }

  // Not authenticated according to cache, redirect to login
  return navigateTo("/login");
});
