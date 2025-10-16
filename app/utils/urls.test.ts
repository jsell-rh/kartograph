/**
 * Tests for URL utility functions
 *
 * Covers all edge cases and permutations of env var configurations
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { getAppUrls, parseBetterAuthUrl, getAuthClientConfig } from "./urls";

// Save original env
let originalEnv: NodeJS.ProcessEnv;

beforeEach(() => {
  originalEnv = { ...process.env };
});

afterEach(() => {
  process.env = originalEnv;
});

describe("getAppUrls", () => {
  describe("with basePath = / (root)", () => {
    it("should generate correct URLs for root deployment", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/",
      });

      expect(urls.appOrigin).toBe("https://example.com");
      expect(urls.basePath).toBe("/");
      expect(urls.authBasePath).toBe("/api/auth");
      expect(urls.authOriginUrl).toBe("https://example.com/api/auth");
      expect(urls.loginPath).toBe("/login");
      expect(urls.loginUrl).toBe("https://example.com/login");
      expect(urls.homePath).toBe("/");
      expect(urls.homeUrl).toBe("https://example.com/");
      expect(urls.apiPath).toBe("/api");
      expect(urls.mcpPath).toBe("/api/mcp");
      expect(urls.mcpUrl).toBe("https://example.com/api/mcp");
    });

    it("should handle appOrigin with trailing slash", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com/",
        basePath: "/",
      });

      expect(urls.appOrigin).toBe("https://example.com");
      expect(urls.authOriginUrl).toBe("https://example.com/api/auth");
    });
  });

  describe("with basePath = /api/kartograph", () => {
    it("should generate correct URLs for subpath deployment", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/api/kartograph",
      });

      expect(urls.appOrigin).toBe("https://example.com");
      expect(urls.basePath).toBe("/api/kartograph");
      expect(urls.authBasePath).toBe("/api/kartograph/api/auth");
      expect(urls.authOriginUrl).toBe("https://example.com/api/kartograph/api/auth");
      expect(urls.loginPath).toBe("/api/kartograph/login");
      expect(urls.loginUrl).toBe("https://example.com/api/kartograph/login");
      expect(urls.homePath).toBe("/api/kartograph");
      expect(urls.homeUrl).toBe("https://example.com/api/kartograph");
      expect(urls.apiPath).toBe("/api/kartograph/api");
      expect(urls.mcpPath).toBe("/api/kartograph/api/mcp");
      expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
    });

    it("should handle basePath with trailing slash", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/api/kartograph/",
      });

      // Should normalize to no trailing slash
      expect(urls.basePath).toBe("/api/kartograph");
      expect(urls.authBasePath).toBe("/api/kartograph/api/auth");
    });

    it("should handle basePath without leading slash", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "api/kartograph",
      });

      // Should add leading slash
      expect(urls.basePath).toBe("/api/kartograph");
    });

    it("should handle basePath without leading slash AND with trailing slash", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "api/kartograph/",
      });

      // Should add leading slash and remove trailing slash
      expect(urls.basePath).toBe("/api/kartograph");
      expect(urls.authBasePath).toBe("/api/kartograph/api/auth");
    });
  });

  describe("trailing slash edge cases", () => {
    describe("appOrigin trailing slashes", () => {
      it("should remove trailing slash from appOrigin", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com/",
          basePath: "/api/kartograph",
        });

        expect(urls.appOrigin).toBe("https://example.com");
        expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
      });

      it("should handle multiple trailing slashes on appOrigin", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com///",
          basePath: "/api/kartograph",
        });

        expect(urls.appOrigin).toBe("https://example.com");
      });
    });

    describe("basePath trailing slashes", () => {
      it("should remove trailing slash from basePath (except root)", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph/",
        });

        expect(urls.basePath).toBe("/api/kartograph");
        expect(urls.homePath).toBe("/api/kartograph");
        expect(urls.loginPath).toBe("/api/kartograph/login");
      });

      it("should keep single slash for root basePath", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/",
        });

        expect(urls.basePath).toBe("/");
        expect(urls.homePath).toBe("/");
      });

      it("should normalize double slash to single slash for root", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "//",
        });

        expect(urls.basePath).toBe("/");
      });
    });

    describe("combined appOrigin and basePath trailing slashes", () => {
      it("should handle both with trailing slashes", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com/",
          basePath: "/api/kartograph/",
        });

        expect(urls.appOrigin).toBe("https://example.com");
        expect(urls.basePath).toBe("/api/kartograph");
        expect(urls.homeUrl).toBe("https://example.com/api/kartograph");
        // Should not have double slashes
        expect(urls.homeUrl).not.toContain("//api");
      });

      it("should handle neither with trailing slashes", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph",
        });

        expect(urls.homeUrl).toBe("https://example.com/api/kartograph");
        expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
      });

      it("should handle mixed trailing slashes (origin yes, base no)", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com/",
          basePath: "/api/kartograph",
        });

        expect(urls.homeUrl).toBe("https://example.com/api/kartograph");
        expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
      });

      it("should handle mixed trailing slashes (origin no, base yes)", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph/",
        });

        expect(urls.homeUrl).toBe("https://example.com/api/kartograph");
        expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
      });
    });

    describe("helper functions with trailing slashes", () => {
      it("getFullUrl should handle paths with trailing slashes", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph",
        });

        expect(urls.getFullUrl("/settings/")).toBe("https://example.com/settings");
        expect(urls.getFullUrl("settings/")).toBe("https://example.com/settings");
      });

      it("getAppPath should handle paths with trailing slashes for root", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/",
        });

        expect(urls.getAppPath("/settings/")).toBe("/settings");
        expect(urls.getAppPath("settings/")).toBe("/settings");
      });

      it("getAppPath should handle paths with trailing slashes for subpath", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph",
        });

        expect(urls.getAppPath("/settings/")).toBe("/api/kartograph/settings");
        expect(urls.getAppPath("settings/")).toBe("/api/kartograph/settings");
      });

      it("getAppPath should not create double slashes", () => {
        const urls = getAppUrls({
          appOrigin: "https://example.com",
          basePath: "/api/kartograph/",
        });

        const result = urls.getAppPath("/api/query");
        expect(result).toBe("/api/kartograph/api/query");
        expect(result).not.toContain("//");
      });
    });
  });

  describe("with different protocols", () => {
    it("should work with http", () => {
      const urls = getAppUrls({
        appOrigin: "http://localhost:3000",
        basePath: "/api/kartograph",
      });

      expect(urls.appOrigin).toBe("http://localhost:3000");
      expect(urls.mcpUrl).toBe("http://localhost:3000/api/kartograph/api/mcp");
    });

    it("should work with https", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/api/kartograph",
      });

      expect(urls.appOrigin).toBe("https://example.com");
      expect(urls.mcpUrl).toBe("https://example.com/api/kartograph/api/mcp");
    });
  });

  describe("helper functions", () => {
    it("getFullUrl should construct full URLs correctly", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/api/kartograph",
      });

      expect(urls.getFullUrl("/settings")).toBe("https://example.com/settings");
      expect(urls.getFullUrl("settings")).toBe("https://example.com/settings");
    });

    it("getAppPath should construct app-relative paths correctly for root", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/",
      });

      expect(urls.getAppPath("/settings")).toBe("/settings");
      expect(urls.getAppPath("settings")).toBe("/settings");
      expect(urls.getAppPath("/api/query")).toBe("/api/query");
      expect(urls.getAppPath("")).toBe("/");
    });

    it("getAppPath should construct app-relative paths correctly for subpath", () => {
      const urls = getAppUrls({
        appOrigin: "https://example.com",
        basePath: "/api/kartograph",
      });

      expect(urls.getAppPath("/settings")).toBe("/api/kartograph/settings");
      expect(urls.getAppPath("settings")).toBe("/api/kartograph/settings");
      expect(urls.getAppPath("/api/query")).toBe("/api/kartograph/api/query");
      expect(urls.getAppPath("")).toBe("/api/kartograph");
    });
  });

  describe("from environment variables", () => {
    it("should read from NUXT_PUBLIC_ORIGIN and NUXT_APP_BASE_URL", () => {
      process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
      process.env.NUXT_APP_BASE_URL = "/api/kartograph";

      const urls = getAppUrls();

      expect(urls.appOrigin).toBe("https://example.com");
      expect(urls.basePath).toBe("/api/kartograph");
    });

    it("should fallback to BETTER_AUTH_URL for appOrigin (backwards compat)", () => {
      delete process.env.NUXT_PUBLIC_ORIGIN;
      process.env.BETTER_AUTH_URL = "https://example.com/api/kartograph";
      process.env.NUXT_APP_BASE_URL = "/api/kartograph";

      const urls = getAppUrls();

      expect(urls.appOrigin).toBe("https://example.com");
    });

    it("should throw error when NUXT_PUBLIC_ORIGIN is missing (server-side)", () => {
      delete process.env.NUXT_PUBLIC_ORIGIN;
      delete process.env.BETTER_AUTH_URL;

      expect(() => getAppUrls()).toThrow("NUXT_PUBLIC_ORIGIN must be set");
    });

    it("should default basePath to / when NUXT_APP_BASE_URL is missing", () => {
      process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
      delete process.env.NUXT_APP_BASE_URL;

      const urls = getAppUrls();

      expect(urls.basePath).toBe("/");
    });
  });
});

describe("parseBetterAuthUrl", () => {
  describe("with BETTER_AUTH_URL (deprecated)", () => {
    it("should parse full URL with subpath", () => {
      process.env.BETTER_AUTH_URL = "https://example.com/api/kartograph";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/kartograph/api/auth");
    });

    it("should parse full URL without subpath", () => {
      process.env.BETTER_AUTH_URL = "https://example.com";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/auth");
    });

    it("should handle trailing slash in URL", () => {
      process.env.BETTER_AUTH_URL = "https://example.com/api/kartograph/";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/kartograph/api/auth");
    });

    it("should handle URL without trailing slash", () => {
      process.env.BETTER_AUTH_URL = "https://example.com/api/kartograph";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/kartograph/api/auth");
    });

    it("should handle URL with multiple trailing slashes", () => {
      process.env.BETTER_AUTH_URL = "https://example.com/api/kartograph///";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/kartograph/api/auth");
    });

    it("should handle root URL with trailing slash", () => {
      process.env.BETTER_AUTH_URL = "https://example.com/";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/auth");
    });

    it("should throw error for invalid BETTER_AUTH_URL", () => {
      process.env.BETTER_AUTH_URL = "not-a-valid-url";

      expect(() => parseBetterAuthUrl()).toThrow("Invalid BETTER_AUTH_URL");
    });
  });

  describe("without BETTER_AUTH_URL (standard config)", () => {
    it("should construct from NUXT_PUBLIC_ORIGIN and NUXT_APP_BASE_URL", () => {
      delete process.env.BETTER_AUTH_URL;
      process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
      process.env.NUXT_APP_BASE_URL = "/api/kartograph";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/kartograph/api/auth");
    });

    it("should work with root basePath", () => {
      delete process.env.BETTER_AUTH_URL;
      process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
      process.env.NUXT_APP_BASE_URL = "/";

      const result = parseBetterAuthUrl();

      expect(result.baseURL).toBe("https://example.com");
      expect(result.basePath).toBe("/api/auth");
    });
  });
});

describe("getAuthClientConfig", () => {
  it("should return config suitable for Better Auth client", () => {
    process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
    process.env.NUXT_APP_BASE_URL = "/api/kartograph";

    const config = getAuthClientConfig();

    expect(config.baseURL).toBe("https://example.com");
    expect(config.basePath).toBe("/api/kartograph/api/auth");
  });

  it("should work with root deployment", () => {
    process.env.NUXT_PUBLIC_ORIGIN = "https://example.com";
    process.env.NUXT_APP_BASE_URL = "/";

    const config = getAuthClientConfig();

    expect(config.baseURL).toBe("https://example.com");
    expect(config.basePath).toBe("/api/auth");
  });
});
