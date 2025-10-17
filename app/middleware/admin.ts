/**
 * Admin Route Middleware
 *
 * Protects /admin routes by checking if the user has admin role.
 * Redirects non-admin users to the home page.
 */

export default defineNuxtRouteMiddleware(async (to, from) => {
  // Only protect /admin routes
  if (!to.path.startsWith("/admin")) {
    return;
  }

  const authStore = useAuthStore();

  // Ensure user is loaded
  if (!authStore.user) {
    await authStore.fetchUser();
  }

  // Check if user is admin
  if (!authStore.user || authStore.user.role !== "admin") {
    return navigateTo("/");
  }
});
