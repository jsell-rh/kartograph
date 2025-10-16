/**
 * Global auth middleware
 *
 * Protects all routes except /login
 */

import { authClient } from "~/lib/auth-client";
import { getAppUrls } from "~/utils/urls";

export default defineNuxtRouteMiddleware(async (to) => {
  const urls = getAppUrls();

  // Skip middleware on login page
  if (to.path === urls.loginPath) {
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
        return navigateTo(urls.loginPath);
      }
    }
  } else {
    // Client-side: use auth client
    const result = await authClient.getSession();

    if (!result.data?.user) {
      return navigateTo(urls.loginPath);
    }
  }
});
