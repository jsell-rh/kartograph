// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from "nuxt/config";
import { execSync } from "child_process";
import { readFileSync } from "fs";

// Get version from package.json or environment
const pkg = JSON.parse(readFileSync("./package.json", "utf-8"));
const version = process.env.APP_VERSION || pkg.version;

// Get git commit hash from environment (Docker build) or git command (local dev)
let gitCommit = process.env.GIT_COMMIT || "unknown";
if (gitCommit === "unknown") {
  try {
    gitCommit = execSync("git rev-parse --short HEAD", {
      encoding: "utf-8",
    }).trim();
  } catch (e) {
    console.warn('Unable to get git commit hash, using "unknown"');
  }
}

// Combine into full version string: e.g., "0.1.0+abc123"
const fullVersion = `${version}+${gitCommit}`;

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },

  modules: ["@nuxtjs/tailwindcss", "@pinia/nuxt"],

  future: {
    compatibilityVersion: 4,
  },

  nitro: {
    experimental: {
      openAPI: true,
    },
    // Include migrations folder in production build
    publicAssets: [
      {
        baseURL: "/migrations",
        dir: "server/db/migrations",
        maxAge: 0,
      },
    ],
    serverAssets: [
      {
        baseName: "migrations",
        dir: "server/db/migrations",
      },
    ],
  },

  devServer: {
    port: Number(process.env.PORT) || 3003,
  },

  app: {
    // Configure base path for deployment behind API gateway
    baseURL: process.env.NUXT_APP_BASE_URL || "/",
    cdnURL: process.env.NUXT_APP_CDN_URL,
  },

  runtimeConfig: {
    anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
    vertexProjectId: process.env.VERTEX_PROJECT_ID || "",
    vertexRegion: process.env.VERTEX_REGION || "us-east5",
    googleApplicationCredentials:
      process.env.GOOGLE_APPLICATION_CREDENTIALS || "",
    dgraphUrl: process.env.DGRAPH_URL || "http://localhost:8080",
    betterAuthSecret:
      process.env.BETTER_AUTH_SECRET || "your-secret-key-change-in-production",

    // MCP Server Configuration
    auditLogRetentionDays: Number(process.env.AUDIT_LOG_RETENTION_DAYS) || 90,
    apiTokenRateLimit: Number(process.env.API_TOKEN_RATE_LIMIT) || 100,
    apiTokenMaxExpiryDays: Number(process.env.API_TOKEN_MAX_EXPIRY_DAYS) || 365,
    apiTokenDefaultExpiryDays:
      Number(process.env.API_TOKEN_DEFAULT_EXPIRY_DAYS) || 90,

    // Authentication Configuration
    authPasswordEnabled:
      process.env.AUTH_PASSWORD_ENABLED !== "false", // pragma: allowlist secret
    authAllowedEmailDomains: process.env.AUTH_ALLOWED_EMAIL_DOMAINS || "", // Comma-separated list (e.g., "redhat.com,ibm.com")

    public: {
      appName: "Kartograph",
      appDescription: "Knowledge Graph Query Interface",
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || "http://localhost:3003",
      baseURL: process.env.NUXT_APP_BASE_URL || "/",
      version: fullVersion,
      gitCommit: gitCommit,
      // Expose auth config to client
      authPasswordEnabled:
        process.env.AUTH_PASSWORD_ENABLED !== "false", // pragma: allowlist secret
    },
  },
});
