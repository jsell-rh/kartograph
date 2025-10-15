/**
 * Red Hat Identity Header utilities
 *
 * The X-Rh-Identity header is a base64-encoded JSON object containing
 * information about the authenticated Red Hat user.
 */

export interface RhIdentityUser {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  is_org_admin: boolean;
  is_internal: boolean;
  locale?: string;
}

export interface RhIdentity {
  identity: {
    account_number?: string;
    org_id?: string;
    type: string;
    user?: RhIdentityUser;
    internal?: {
      org_id?: string;
    };
  };
}

/**
 * Decode and parse the X-Rh-Identity header
 */
export function decodeRhIdentity(header: string): RhIdentity | null {
  try {
    const decoded = Buffer.from(header, "base64").toString("utf-8");
    return JSON.parse(decoded) as RhIdentity;
  } catch (error) {
    console.error("[rhIdentity] Failed to decode X-Rh-Identity header:", error);
    return null;
  }
}

/**
 * Extract user information from X-Rh-Identity header
 * Returns a standardized user object compatible with better-auth
 */
export function getRhUser(rhIdentity: RhIdentity) {
  const user = rhIdentity.identity.user;
  if (!user) {
    return null;
  }

  return {
    id: user.username, // Use username as unique ID
    email: user.email,
    name:
      user.first_name && user.last_name
        ? `${user.first_name} ${user.last_name}`
        : user.username,
    emailVerified: user.is_active,
    image: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}
