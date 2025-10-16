/**
 * Vue composable for accessing app URLs
 *
 * This composable provides reactive access to app URLs in Vue components.
 * It uses the centralized utils/urls.ts for all URL generation.
 *
 * Usage in components:
 * ```ts
 * const { loginUrl, homePath, mcpUrl, getAppPath } = useAppUrls()
 * ```
 */

import type { AppUrls } from "~/utils/urls";
import { getAppUrls } from "~/utils/urls";

export function useAppUrls(): AppUrls {
  const config = useRuntimeConfig();

  // Priority: app.baseURL (server-rendered) > public.baseURL (can be build-time)
  // This matches the logic in plugins/auth-config.client.ts
  const basePath = config.app?.baseURL ||
                  (config.public.baseURL !== "/" ? config.public.baseURL : null) ||
                  "/";

  return getAppUrls({
    appOrigin: config.public.appOrigin || (typeof window !== "undefined" ? window.location.origin : ""),
    basePath,
  });
}
