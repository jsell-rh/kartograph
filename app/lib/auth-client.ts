/**
 * Client-side auth utilities using Better Auth
 */

import { createAuthClient } from "better-auth/client";
import { getAppUrls } from "~/utils/urls";

let _authClient: ReturnType<typeof createAuthClient> | null = null;

function initAuthClient() {
  if (_authClient) return _authClient;

  let baseURL: string;
  let basePath: string;

  if (typeof window !== "undefined") {
    // Client-side: get config from window (injected by plugin)
    const authConfig = (window as any).__AUTH_CONFIG__;

    if (authConfig) {
      baseURL = authConfig.appOrigin;
      basePath = authConfig.basePath;
      console.log("[auth-client] Using injected config:", authConfig);
    } else {
      // Fallback if plugin hasn't run yet (shouldn't happen)
      console.warn("[auth-client] No injected config found, using fallback");
      const urls = getAppUrls({
        appOrigin: window.location.origin,
        basePath: "/",
      });
      baseURL = urls.appOrigin;
      basePath = urls.authBasePath;
    }
  } else {
    // Server-side: use process.env
    const urls = getAppUrls();
    baseURL = urls.appOrigin;
    basePath = urls.authBasePath;
  }

  console.log("[auth-client] Initializing with:", {
    baseURL,
    basePath,
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
