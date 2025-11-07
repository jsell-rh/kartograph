/**
 * Better Auth configuration with Drizzle adapter
 */

import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "../db/client";
import * as schema from "../db/schema";
import { validateEmailDomain } from "../utils/auth";
import { parseBetterAuthUrl, getAppUrls } from "~/utils/urls";
import { createLogger } from "./logger";
import { eq } from "drizzle-orm";

const log = createLogger("auth");

// GitHub OAuth configuration
const githubClientId =
  process.env.NUXT_GITHUB_CLIENT_ID || process.env.GITHUB_CLIENT_ID;
const githubClientSecret =
  process.env.NUXT_GITHUB_CLIENT_SECRET || process.env.GITHUB_CLIENT_SECRET;

// Get Better Auth configuration from centralized utility
const { baseURL, basePath } = parseBetterAuthUrl();
log.info({ baseURL, basePath }, "Better Auth configuration loaded");

// Get app URLs for redirects
const appUrls = getAppUrls();
log.info({ loginPath: appUrls.loginPath, homePath: appUrls.homePath }, "App URLs configured");

// Parse additional trusted origins from environment variable
const envTrustedOrigins = process.env.BETTER_AUTH_TRUSTED_ORIGINS
  ? process.env.BETTER_AUTH_TRUSTED_ORIGINS.split(",").map((url) => url.trim())
  : [];

// Check if password auth is enabled
const passwordAuthEnabled = (process.env.NUXT_AUTH_PASSWORD_ENABLED || process.env.AUTH_PASSWORD_ENABLED) !== "false"; // pragma: allowlist secret

// Check if email domain validation is enabled
const allowedDomainsEnv = process.env.NUXT_AUTH_ALLOWED_EMAIL_DOMAINS || process.env.AUTH_ALLOWED_EMAIL_DOMAINS || "";
const hasEmailDomainRestrictions = allowedDomainsEnv.trim() !== "";

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
            getUserInfo: async (token) => {
              if (!token.accessToken) {
                throw new Error("No access token available");
              }

              // Fetch basic user info
              const userResponse = await fetch("https://api.github.com/user", {
                headers: {
                  Authorization: `Bearer ${token.accessToken}`,
                },
              });
              const userProfile = await userResponse.json();

              // Fetch ALL user emails (requires 'user:email' scope)
              const emailsResponse = await fetch("https://api.github.com/user/emails", {
                headers: {
                  Authorization: `Bearer ${token.accessToken}`,
                },
              });
              const emails = await emailsResponse.json();

              // Find the best email to use based on allowed domains
              let selectedEmail = userProfile.email;
              let emailVerified = false;

              if (hasEmailDomainRestrictions && Array.isArray(emails)) {
                log.debug({ emails }, "Fetched all GitHub emails");

                // Filter for verified emails
                const verifiedEmails = emails.filter((e: any) => e.verified);

                // Check if any verified email matches allowed domains
                for (const emailObj of verifiedEmails) {
                  const validationError = validateEmailDomain(emailObj.email);
                  if (!validationError) {
                    // This email is allowed!
                    selectedEmail = emailObj.email;
                    emailVerified = true;
                    log.info({ selectedEmail }, "Found allowed email in GitHub account");
                    break;
                  }
                }
              } else if (Array.isArray(emails)) {
                // No domain restrictions - use primary verified email if available
                const primaryEmail = emails.find((e: any) => e.primary && e.verified);
                if (primaryEmail) {
                  selectedEmail = primaryEmail.email;
                  emailVerified = true;
                }
              }

              return {
                user: {
                  id: userProfile.id.toString(),
                  name: userProfile.name || userProfile.login,
                  email: selectedEmail,
                  image: userProfile.avatar_url,
                  emailVerified,
                },
                data: {
                  ...userProfile,
                  allEmails: emails,
                },
              };
            },
          },
        }
      : {}),
  },
  user: {
    additionalFields: {
      role: {
        type: "string",
        required: false,
        defaultValue: "user",
      },
    },
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
    ...envTrustedOrigins,
  ],
  hooks: {
    ...(hasEmailDomainRestrictions && {
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
    }),
    after: createAuthMiddleware(async (ctx) => {
      // Update lastLoginAt on successful login (sign-in or OAuth callback)
      const isLoginPath = ctx.path === "/sign-in/email" || ctx.path.startsWith("/callback/");

      if (isLoginPath) {
        const newSession = (ctx.context as any)?.newSession;
        const session = (ctx.context as any)?.session;

        let userId: string | undefined;
        let email: string | undefined;

        if (newSession?.user) {
          userId = newSession.user.id;
          email = newSession.user.email;
        } else if (session?.user) {
          userId = session.user.id;
          email = session.user.email;
        }

        // Update lastLoginAt for the user
        if (userId) {
          await db
            .update(schema.users)
            .set({ lastLoginAt: new Date() })
            .where(eq(schema.users.id, userId));

          log.debug({ userId }, "Updated lastLoginAt");
        }

        // Email domain validation (if enabled)
        if (hasEmailDomainRestrictions && ctx.path.startsWith("/callback/")) {
          if (email) {
            const validationError = validateEmailDomain(email);

            if (validationError) {
              log.warn({ userId, email, error: validationError }, "Blocking user - email domain not allowed");

              // Delete the just-created user if email domain is not allowed
              if (userId) {
                await db.delete(schema.users).where(eq(schema.users.id, userId));
                log.info({ userId }, "Deleted disallowed user account");
              }

              // Redirect to login page with error message instead of throwing
              const loginUrl = `${appUrls.loginPath}?error=${encodeURIComponent(validationError)}`;
              return ctx.redirect(loginUrl);
            } else {
              log.debug({ userId, email }, "Email domain validation passed");
            }
          } else {
            log.warn({ path: ctx.path }, "No email found in OAuth callback");
          }
        }
      }
    }),
  },
});
