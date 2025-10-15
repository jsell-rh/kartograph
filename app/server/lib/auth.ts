/**
 * Better Auth configuration with Drizzle adapter
 */

import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "../db/client";
import * as schema from "../db/schema";

// GitHub OAuth configuration
const githubClientId =
  process.env.NUXT_GITHUB_CLIENT_ID || process.env.GITHUB_CLIENT_ID;
const githubClientSecret =
  process.env.NUXT_GITHUB_CLIENT_SECRET || process.env.GITHUB_CLIENT_SECRET;

// Parse the full URL to extract origin and path
const fullAuthUrl = process.env.BETTER_AUTH_URL || "http://localhost:3000";
let baseURL = fullAuthUrl;
let basePath = "/api/auth";

try {
  const url = new URL(fullAuthUrl);
  baseURL = url.origin; // e.g., https://kartograph-abc123.apps.openshift.example.com
  // If the URL includes a path (e.g., /api/kartograph), combine it with /api/auth
  if (url.pathname && url.pathname !== "/") {
    basePath = `${url.pathname}/api/auth`.replace(/\/+/g, "/"); // e.g., /api/kartograph/api/auth
  }
} catch (e) {
  console.warn("Unable to parse BETTER_AUTH_URL, using defaults");
}

// Parse additional trusted origins from environment variable
const envTrustedOrigins = process.env.BETTER_AUTH_TRUSTED_ORIGINS
  ? process.env.BETTER_AUTH_TRUSTED_ORIGINS.split(",").map((url) => url.trim())
  : [];

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: "sqlite",
    schema: {
      user: schema.users,
      session: schema.sessions,
      account: schema.accounts,
      verification: schema.verifications,
    },
  }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Simplified for PoC
  },
  socialProviders: {
    ...(githubClientId && githubClientSecret
      ? {
          github: {
            clientId: githubClientId,
            clientSecret: githubClientSecret,
          },
        }
      : {}),
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session every 24 hours
  },
  baseURL,
  basePath,
  secret:
    process.env.BETTER_AUTH_SECRET || "your-secret-key-change-in-production",
  trustedOrigins: [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3010",
    "http://localhost:3020",
    ...envTrustedOrigins,
  ],
});
