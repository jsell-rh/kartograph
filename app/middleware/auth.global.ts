/**
 * Global auth middleware
 *
 * Protects all routes except /login
 */

import { authClient } from "~/lib/auth-client";

export default defineNuxtRouteMiddleware(async (to) => {
  // Skip middleware on login page (use route name instead of path to avoid base path issues)
  if (to.path.endsWith('/login')) {
    return;
  }

  // Check if user is authenticated
  // On server-side during SSR, use server utilities
  // On client-side, use auth client
  let session;

  if (import.meta.server) {
    // Server-side: use server utilities from event context
    const event = useRequestEvent();
    if (event) {
      const { getSession } = await import("~/server/utils/auth");
      session = await getSession(event);

      if (!session?.user) {
        // Use route-relative path - Nuxt will handle base path automatically
        return navigateTo('/login');
      }
    }
  } else {
    // Client-side: use auth client
    const result = await authClient.getSession();

    if (!result.data?.user) {
      // Use route-relative path - Nuxt will handle base path automatically
      return navigateTo('/login');
    }
  }
});
