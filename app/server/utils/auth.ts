/**
 * Server-side auth utilities
 *
 * Supports dual authentication:
 * - Production: X-Rh-Identity header from crcauth (Red Hat SSO)
 * - Local dev: better-auth sessions
 */

import { auth } from "../lib/auth";
import type { H3Event } from "h3";
import { decodeRhIdentity, getRhUser } from "./rhIdentity";
import { db } from "../db/client";
import { users } from "../db/schema";
import { eq } from "drizzle-orm";

/**
 * Get current session from request
 *
 * Checks for crcauth (X-Rh-Identity header) first, then falls back to better-auth
 */
export async function getSession(event: H3Event) {
  // Check for Red Hat Identity header (production with crcauth)
  // Only accept X-Rh-Identity header if explicitly enabled via env var (security)
  const enableRhIdentity = process.env.ENABLE_RH_IDENTITY_HEADER === "true";
  const rhIdentityHeader = event.node.req.headers["x-rh-identity"] as
    | string
    | undefined;

  if (enableRhIdentity && rhIdentityHeader) {
    const rhIdentity = decodeRhIdentity(rhIdentityHeader);
    if (rhIdentity) {
      const rhUserData = getRhUser(rhIdentity);
      if (rhUserData) {
        // Check if user exists in database, create if not
        let dbUser = await db.query.users.findFirst({
          where: eq(users.id, rhUserData.id),
        });

        if (!dbUser) {
          // Auto-create user from RH SSO
          await db.insert(users).values({
            id: rhUserData.id,
            email: rhUserData.email,
            name: rhUserData.name,
            emailVerified: rhUserData.emailVerified,
            image: rhUserData.image,
            createdAt: new Date(),
            updatedAt: new Date(),
          });

          dbUser = await db.query.users.findFirst({
            where: eq(users.id, rhUserData.id),
          });
        } else {
          // Update user info if changed
          await db
            .update(users)
            .set({
              email: rhUserData.email,
              name: rhUserData.name,
              emailVerified: rhUserData.emailVerified,
              updatedAt: new Date(),
            })
            .where(eq(users.id, rhUserData.id));
        }

        // Return a session-like object compatible with better-auth
        return {
          session: {
            id: `rh-${rhUserData.id}`,
            userId: rhUserData.id,
            expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
            token: "rh-sso",
            ipAddress: "",
            userAgent: "",
          },
          user: dbUser || rhUserData,
        };
      }
    }
  }

  // Fall back to better-auth (local development)
  try {
    const session = await auth.api.getSession({
      headers: event.node.req.headers as any, // better-auth headers type compatibility
    });
    return session;
  } catch (error) {
    return null;
  }
}

/**
 * Require authentication - throws if not authenticated
 */
export async function requireAuth(event: H3Event) {
  const session = await getSession(event);

  if (!session || !session.user) {
    throw createError({
      statusCode: 401,
      message: "Unauthorized - Please log in",
    });
  }

  return session;
}

/**
 * Validate email domain against allowed domains configuration
 *
 * @param email - Email address to validate
 * @returns Error message if validation fails, null if passes
 */
export function validateEmailDomain(email: string): string | null {
  const allowedDomainsEnv = process.env.NUXT_AUTH_ALLOWED_EMAIL_DOMAINS || process.env.AUTH_ALLOWED_EMAIL_DOMAINS || "";

  console.log("[validateEmailDomain] Input email:", email);
  console.log("[validateEmailDomain] ALLOWED_EMAIL_DOMAINS:", allowedDomainsEnv);

  // If no domains configured, allow all
  if (!allowedDomainsEnv || allowedDomainsEnv.trim() === "") {
    console.log("[validateEmailDomain] No restrictions configured - allowing all");
    return null;
  }

  const allowedDomains = allowedDomainsEnv
    .split(",")
    .map((d) => d.trim().toLowerCase())
    .filter((d) => d.length > 0);

  console.log("[validateEmailDomain] Allowed domains:", allowedDomains);

  if (allowedDomains.length === 0) {
    console.log("[validateEmailDomain] No valid domains after parsing - allowing all");
    return null;
  }

  const emailLower = email.toLowerCase();
  const emailDomain = emailLower.split("@")[1];

  console.log("[validateEmailDomain] Email domain extracted:", emailDomain);

  if (!emailDomain) {
    return "Invalid email address format";
  }

  const isAllowed = allowedDomains.some((domain) => emailDomain === domain);

  console.log("[validateEmailDomain] Is allowed?", isAllowed);

  if (!isAllowed) {
    return `Emails ending in @${emailDomain} are not permitted to access this application.`;
  }

  return null;
}
