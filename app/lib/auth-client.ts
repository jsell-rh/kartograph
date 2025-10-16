/**
 * Client-side auth utilities using Better Auth
 */

import { createAuthClient } from "better-auth/client";
import { getAuthClientConfig } from "~/utils/urls";

let _authClient: ReturnType<typeof createAuthClient> | null = null;

function initAuthClient() {
  if (_authClient) return _authClient;

  // Get auth configuration from centralized utility
  const { baseURL, basePath } = getAuthClientConfig();

  console.log("[auth-client] Configuration:", {
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
