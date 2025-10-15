/**
 * Client-side auth utilities using Better Auth
 */

import { createAuthClient } from "better-auth/client";

let _authClient: ReturnType<typeof createAuthClient> | null = null;

function initAuthClient() {
  if (_authClient) return _authClient;

  // Get base URL
  let baseURL = "http://localhost:3003";
  if (typeof window !== "undefined") {
    baseURL = window.location.origin;
  } else {
    try {
      const config = useRuntimeConfig();
      baseURL = config.public.siteUrl || "http://localhost:3003";
    } catch {
      baseURL = process.env.NUXT_PUBLIC_SITE_URL || "http://localhost:3003";
    }
  }

  // Get base path for auth endpoints
  // This should match the server-side configuration in server/lib/auth.ts
  let nuxtBasePath = "/";
  try {
    const config = useRuntimeConfig();
    nuxtBasePath = config.app.baseURL || "/";
  } catch {
    nuxtBasePath = process.env.NUXT_APP_BASE_URL || "/";
  }

  // Combine with auth path: /api/kartograph + /api/auth = /api/kartograph/api/auth
  let basePath = "/api/auth";
  if (nuxtBasePath && nuxtBasePath !== "/") {
    basePath = `${nuxtBasePath}/api/auth`.replace(/\/+/g, "/");
  }

  console.log("[auth-client] Configuration:", {
    baseURL,
    basePath,
    nuxtBasePath,
  });

  _authClient = createAuthClient({
    baseURL,
    basePath,
  });

  return _authClient;
}

export const authClient = new Proxy({} as ReturnType<typeof createAuthClient>, {
  get(_target, prop) {
    const client = initAuthClient();
    return client[prop as keyof typeof client];
  },
});

export type Session = Awaited<ReturnType<typeof authClient.getSession>>["data"];
export type User = Session extends { user: infer U } ? U : never;
