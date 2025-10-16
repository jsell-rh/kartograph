/**
 * Plugin to inject auth configuration into window for use by auth-client
 * This runs on client-side only and makes runtime config available to the auth client
 */

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig();
  const appUrls = useAppUrls();

  // Inject config into window so auth-client.ts can access it
  if (typeof window !== "undefined") {
    (window as any).__AUTH_CONFIG__ = {
      appOrigin: appUrls.appOrigin,
      basePath: appUrls.authBasePath,
      baseURL: config.public.baseURL,
    };

    console.log("[auth-config] Injected auth config into window:", (window as any).__AUTH_CONFIG__);
  }
});
