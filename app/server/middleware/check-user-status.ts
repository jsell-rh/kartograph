/**
 * Global User Status Check Middleware
 *
 * Checks if authenticated users are active (not disabled) on every request.
 * Disabled users are immediately logged out and blocked from accessing the application.
 *
 * Skips:
 * - Auth endpoints (/api/auth/*)
 * - Health checks (/api/health)
 * - Static assets (_nuxt/*, favicon.ico)
 */

export default defineEventHandler(async (event) => {
  const path = event.path;

  // Skip auth routes and public endpoints
  if (
    path.startsWith("/api/auth") ||
    path.startsWith("/api/health") ||
    path.startsWith("/_nuxt") ||
    path === "/favicon.ico" ||
    path.endsWith(".ico") ||
    path.endsWith(".png") ||
    path.endsWith(".svg")
  ) {
    return;
  }

  // Check if user is active (will throw 403 if disabled)
  await requireActiveUser(event);
});
