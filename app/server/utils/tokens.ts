/**
 * API Token Utilities
 *
 * Functions for generating, hashing, and validating API tokens
 * used for MCP server authentication.
 */

import crypto from "crypto";

/**
 * Generate a new API token with the format: cart_<base64url(24 random bytes)>
 *
 * @returns Object with plaintext token and its SHA-256 hash
 *
 * @example
 * const { token, hash } = generateToken()
 * // token: "cart_example123456789012345678901"
 * // hash: "a3f5d9c2e8b1f7a4c6e9d2b5f8a1c4e7..."
 */
export function generateToken(): { token: string; hash: string } {
  // Generate 24 random bytes (192 bits of entropy)
  const randomBytes = crypto.randomBytes(24);

  // Encode as base64url (URL-safe, no padding)
  const token = `cart_${randomBytes.toString("base64url")}`;

  // Hash for storage
  const hash = hashToken(token);

  return { token, hash };
}

/**
 * Hash a token using SHA-256
 *
 * @param token - Plaintext token to hash
 * @returns SHA-256 hash of the token (hex encoded)
 */
export function hashToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

/**
 * Validate token format
 *
 * @param token - Token to validate
 * @returns True if token matches expected format
 */
export function isValidTokenFormat(token: string): boolean {
  // Token should be: cart_ + base64url characters
  // base64url characters: A-Z, a-z, 0-9, -, _
  // 24 bytes base64url encoded = 32 characters (sometimes 33 with padding variations)
  const pattern = /^cart_[A-Za-z0-9_-]{32,33}$/;
  return pattern.test(token);
}
