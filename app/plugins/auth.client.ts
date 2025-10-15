/**
 * Client-side auth plugin
 * Initializes auth store from localStorage on app startup
 */

export default defineNuxtPlugin(async () => {
  const authStore = useAuthStore();

  // Initialize auth from localStorage and sync with server
  await authStore.initializeAuth();
});
