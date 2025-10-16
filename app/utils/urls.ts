/**
 * Centralized URL and path handling utilities
 *
 * This module provides a single source of truth for all URL/path construction
 * throughout the application, eliminating duplication and edge case bugs.
 *
 * Environment Variables:
 * - NUXT_PUBLIC_ORIGIN: App origin/host (e.g., "https://example.com")
 * - NUXT_APP_BASE_URL: App base path (e.g., "/api/kartograph") - Nuxt standard
 * - BETTER_AUTH_URL: Deprecated - use NUXT_PUBLIC_ORIGIN + NUXT_APP_BASE_URL instead
 *
 * Runtime Config Mapping:
 * - config.public.appOrigin → NUXT_PUBLIC_ORIGIN
 * - config.public.baseURL → NUXT_APP_BASE_URL (Nuxt standard)
 * - config.app.baseURL → NUXT_APP_BASE_URL (Nuxt standard)
 */

/**
 * Normalize a path by ensuring it starts with / and optionally ends with /
 */
function normalizePath(path: string, trailingSlash: boolean = false): string {
  if (!path) return "/";

  // Ensure leading slash
  let normalized = path.startsWith("/") ? path : `/${path}`;

  // Handle trailing slash
  if (trailingSlash) {
    if (!normalized.endsWith("/")) {
      normalized = `${normalized}/`;
    }
  } else {
    if (normalized.endsWith("/") && normalized !== "/") {
      normalized = normalized.slice(0, -1);
    }
  }

  return normalized;
}

/**
 * Combine multiple path segments safely
 */
function joinPaths(...segments: string[]): string {
  return segments
    .filter((s) => s && s.trim())
    .map((s) => s.replace(/^\/+|\/+$/g, "")) // Remove leading/trailing slashes
    .filter((s) => s) // Remove empty strings
    .join("/");
}

/**
 * App URL configuration
 * This interface represents all the URLs/paths the app needs
 */
export interface AppUrls {
  // Base configuration
  appOrigin: string; // App origin/host (e.g., "https://example.com")
  basePath: string; // App base path (e.g., "/api/kartograph")

  // Auth endpoints
  authBasePath: string; // Full auth API path (e.g., "/api/kartograph/api/auth")
  authOriginUrl: string; // Full auth URL (e.g., "https://example.com/api/kartograph/api/auth")

  // Common pages
  loginPath: string; // Path to login page
  loginUrl: string; // Full URL to login page
  homePath: string; // Path to home page
  homeUrl: string; // Full URL to home page

  // API endpoints
  apiPath: string; // Path to API root (e.g., "/api/kartograph/api")
  mcpPath: string; // Path to MCP endpoint
  mcpUrl: string; // Full URL to MCP endpoint

  // Helper functions
  getFullUrl: (path: string) => string; // Convert path to full URL
  getAppPath: (relativePath: string) => string; // Get app-relative path
}

/**
 * Get app URLs from environment/config
 * Works in both server and client contexts
 */
export function getAppUrls(options?: {
  appOrigin?: string;
  basePath?: string;
}): AppUrls {
  // Determine appOrigin (protocol + host)
  let appOrigin = options?.appOrigin;
  if (!appOrigin) {
    if (typeof window !== "undefined") {
      // Client-side: use window.location.origin
      appOrigin = window.location.origin;
    } else {
      // Server-side: require env var (or fallback to BETTER_AUTH_URL for backwards compatibility)
      appOrigin =
        process.env.NUXT_PUBLIC_ORIGIN ||
        process.env.BETTER_AUTH_URL;

      if (!appOrigin) {
        throw new Error(
          "NUXT_PUBLIC_ORIGIN must be set. " +
          "Configure this in your environment or nuxt.config.ts " +
          "(e.g., NUXT_PUBLIC_ORIGIN=https://example.com)"
        );
      }

      // If BETTER_AUTH_URL is provided (deprecated), extract just the origin
      if (appOrigin.includes("://")) {
        try {
          const url = new URL(appOrigin);
          appOrigin = url.origin;
        } catch (e) {
          throw new Error(
            `Invalid URL in NUXT_PUBLIC_ORIGIN: ${appOrigin}. ` +
            `Must be a valid URL (e.g., "https://example.com")`
          );
        }
      }
    }
  }

  // Ensure appOrigin doesn't have trailing slashes
  appOrigin = appOrigin.replace(/\/+$/, "");

  // Determine basePath (Nuxt standard config)
  let basePath = options?.basePath;
  if (!basePath) {
    basePath = process.env.NUXT_APP_BASE_URL || "/";
  }

  // Normalize basePath (no trailing slash unless it's root)
  basePath = normalizePath(basePath, false);

  // Build all derived URLs
  const authBasePath =
    basePath === "/"
      ? "/api/auth"
      : normalizePath(`${basePath}/api/auth`, false);

  const apiPath =
    basePath === "/" ? "/api" : normalizePath(`${basePath}/api`, false);

  const mcpPath =
    basePath === "/" ? "/api/mcp" : normalizePath(`${basePath}/api/mcp`, false);

  const loginPath =
    basePath === "/" ? "/login" : normalizePath(`${basePath}/login`, false);

  const homePath = basePath;

  // homeUrl needs trailing slash for proper routing
  const homeUrl = basePath === "/"
    ? `${appOrigin}/`
    : `${appOrigin}${basePath}/`;

  return {
    // Base
    appOrigin,
    basePath,

    // Auth
    authBasePath,
    authOriginUrl: `${appOrigin}${authBasePath}`,

    // Pages
    loginPath,
    loginUrl: `${appOrigin}${loginPath}`,
    homePath,
    homeUrl,

    // API
    apiPath,
    mcpPath,
    mcpUrl: `${appOrigin}${mcpPath}`,

    // Helpers
    getFullUrl: (path: string) => {
      const normalizedPath = normalizePath(path, false);
      return `${appOrigin}${normalizedPath}`;
    },

    getAppPath: (relativePath: string) => {
      // Remove leading slash from relative path
      const relative = relativePath.startsWith("/")
        ? relativePath.slice(1)
        : relativePath;

      if (!relative) return basePath;

      return basePath === "/"
        ? normalizePath(`/${relative}`, false)
        : normalizePath(`${basePath}/${relative}`, false);
    },
  };
}

/**
 * Get Better Auth configuration
 * Constructs from NUXT_PUBLIC_ORIGIN + NUXT_APP_BASE_URL
 *
 * Backwards compatible with BETTER_AUTH_URL (deprecated)
 */
export function parseBetterAuthUrl(): { baseURL: string; basePath: string } {
  // Check for deprecated BETTER_AUTH_URL
  const betterAuthUrl = process.env.BETTER_AUTH_URL;

  if (betterAuthUrl) {
    // Log deprecation warning (only server-side)
    if (typeof process !== "undefined" && process.env.NODE_ENV !== "production") {
      console.warn(
        "[URL Utils] BETTER_AUTH_URL is deprecated. " +
        "Use NUXT_PUBLIC_ORIGIN and NUXT_APP_BASE_URL instead."
      );
    }

    try {
      const url = new URL(betterAuthUrl);
      const baseURL = url.origin;

      // If the URL includes a path (e.g., /api/kartograph), combine it with /api/auth
      let basePath = "/api/auth";
      if (url.pathname && url.pathname !== "/") {
        // Normalize pathname to remove trailing slashes before combining
        const normalizedPathname = url.pathname.replace(/\/+$/, "");
        basePath = normalizePath(`${normalizedPathname}/api/auth`, false);
      }

      return { baseURL, basePath };
    } catch (e) {
      throw new Error(
        `Invalid BETTER_AUTH_URL: ${betterAuthUrl}. ` +
        `Must be a valid URL (e.g., "https://example.com/api/kartograph")`
      );
    }
  }

  // Construct from standard env vars
  const urls = getAppUrls();
  return {
    baseURL: urls.appOrigin,
    basePath: urls.authBasePath,
  };
}

/**
 * Get auth client configuration
 * Used by lib/auth-client.ts
 */
export function getAuthClientConfig(): {
  baseURL: string;
  basePath: string;
} {
  const urls = getAppUrls();
  return {
    baseURL: urls.appOrigin,
    basePath: urls.authBasePath,
  };
}
