/**
 * Plugin to inject auth configuration into window for use by auth-client
 * This runs on client-side only and makes runtime config available to the auth client
 */

export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === "undefined") return;

  // Get the base URL from Nuxt's app config (set during SSR)
  // This reads from the server-rendered payload, not the baked-in bundle config
  const baseURL = nuxtApp.$config.public.baseURL || nuxtApp.$config.app.baseURL || "/";
  const appOrigin = nuxtApp.$config.public.appOrigin || window.location.origin;

  console.log("[auth-config] Runtime config from server:", {
    "nuxtApp.$config.public.baseURL": nuxtApp.$config.public.baseURL,
    "nuxtApp.$config.app.baseURL": nuxtApp.$config.app.baseURL,
    "nuxtApp.$config.public.appOrigin": nuxtApp.$config.public.appOrigin,
    "final baseURL": baseURL,
    "final appOrigin": appOrigin,
  });

  // Calculate auth base path (baseURL + /api/auth)
  const authBasePath =
    baseURL === "/"
      ? "/api/auth"
      : `${baseURL.replace(/\/+$/, "")}/api/auth`;

  // Inject config into window so auth-client.ts can access it
  (window as any).__AUTH_CONFIG__ = {
    appOrigin,
    basePath: authBasePath,
    baseURL,
  };

  console.log("[auth-config] Injected auth config into window:", (window as any).__AUTH_CONFIG__);
});
