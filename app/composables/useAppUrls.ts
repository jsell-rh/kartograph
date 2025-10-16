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

  return getAppUrls({
    appOrigin: config.public.appOrigin,
    basePath: config.public.baseURL,
  });
}
