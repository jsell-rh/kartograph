/**
 * Server middleware to protect API endpoints
 *
 * Supports dual authentication:
 * - Production: crcauth injects X-Rh-Identity header (Red Hat SSO)
 * - Local dev: better-auth session cookies
 *
 * All API routes except /api/auth/* require authentication
 */

import { getSession } from "../utils/auth";

export default defineEventHandler(async (event) => {
  const path = event.path;

  // Public paths that don't require authentication
  const publicPaths = [
    "/api/auth", // Better-auth endpoints (local dev only)
    "/api/stats", // Public stats endpoint
    "/api/mcp", // MCP server (uses token auth middleware)
    "/api/health", // Health check for Kubernetes probes
  ];

  // Skip auth check if:
  // 1. Path matches a public API endpoint
  if (publicPaths.some((p) => path.startsWith(p))) {
    return;
  }

  // 2. Not an API route (pages, assets, etc.)
  if (!path.startsWith("/api/")) {
    return;
  }

  // 3. Static assets (have file extensions)
  if (/\.\w+$/.test(path)) {
    return;
  }

  // 4. Nuxt internal routes
  if (path.startsWith("/_nuxt") || path.startsWith("/__nuxt")) {
    return;
  }

  // All other /api/* endpoints require authentication
  // getSession() checks X-Rh-Identity first (production), then better-auth (local)
  const session = await getSession(event);

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      message: "Unauthorized",
    });
  }
});
