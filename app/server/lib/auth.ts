/**
 * Better Auth configuration with Drizzle adapter
 */

import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "../db/client";
import * as schema from "../db/schema";
import { validateEmailDomain } from "../utils/auth";
import { eq } from "drizzle-orm";

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

// Check if password auth is enabled
const passwordAuthEnabled = process.env.AUTH_PASSWORD_ENABLED !== "false"; // pragma: allowlist secret

// Get the app base path for post-OAuth redirects
const appBasePath = process.env.NUXT_APP_BASE_URL || "/";

// Check if email domain validation is enabled
const hasEmailDomainRestrictions =
  process.env.AUTH_ALLOWED_EMAIL_DOMAINS &&
  process.env.AUTH_ALLOWED_EMAIL_DOMAINS.trim() !== "";

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
    enabled: passwordAuthEnabled,
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
  ...(hasEmailDomainRestrictions && {
    hooks: {
      before: createAuthMiddleware(async (ctx) => {
        // Apply email domain validation to sign-up (password) and sign-in (OAuth)
        if (ctx.path === "/sign-up/email") {
          // For password sign-up, email is in the body
          const email = ctx.body?.email;

          if (email) {
            const validationError = validateEmailDomain(email);
            if (validationError) {
              throw new Error(validationError);
            }
          }
        }
      }),
      after: createAuthMiddleware(async (ctx) => {
        // Validate email domain after OAuth callback (when user is created/logged in)
        console.log("[EMAIL VALIDATION] After hook triggered, path:", ctx.path);

        // OAuth callback path is /callback/:id (where :id is the provider like github)
        if (ctx.path.startsWith("/callback/")) {
          console.log("[EMAIL VALIDATION] OAuth callback path matched");

          // After OAuth, newSession contains the session with user data
          const newSession = (ctx.context as any)?.newSession;
          const session = (ctx.context as any)?.session;

          console.log("[EMAIL VALIDATION] newSession exists?", !!newSession);
          console.log("[EMAIL VALIDATION] session exists?", !!session);

          // Extract email from session
          let email: string | undefined;
          let userId: string | undefined;

          if (newSession?.user) {
            email = newSession.user.email;
            userId = newSession.user.id;
            console.log("[EMAIL VALIDATION] Found user in newSession");
          } else if (session?.user) {
            email = session.user.email;
            userId = session.user.id;
            console.log("[EMAIL VALIDATION] Found user in session");
          }

          console.log("[EMAIL VALIDATION] Email extracted:", email);
          console.log("[EMAIL VALIDATION] User ID:", userId);

          if (email) {
            const validationError = validateEmailDomain(email);
            console.log("[EMAIL VALIDATION] Validation result:", validationError);

            if (validationError) {
              console.log(
                "[EMAIL VALIDATION] BLOCKING USER - deleting account and redirecting to login",
              );

              // Delete the just-created user if email domain is not allowed
              if (userId) {
                console.log("[EMAIL VALIDATION] Deleting user:", userId);
                await db.delete(schema.users).where(eq(schema.users.id, userId));
              }

              // Redirect to login page with error message instead of throwing
              const loginUrl = `${appBasePath}login?error=${encodeURIComponent(validationError)}`;
              console.log("[EMAIL VALIDATION] Redirecting to:", loginUrl);

              return ctx.redirect(loginUrl);
            } else {
              console.log(
                "[EMAIL VALIDATION] Email domain allowed - user can proceed",
              );
            }
          } else {
            console.log(
              "[EMAIL VALIDATION] WARNING: No email found in OAuth callback",
            );
          }
        }
      }),
    },
  }),
});
