/**
 * Composable for API Token Management
 *
 * Provides state and operations for managing API tokens
 */

export interface ApiToken {
  id: string;
  name: string;
  totalQueries: number;
  lastUsedAt: string | null;
  expiresAt: string;
  createdAt: string;
  revokedAt: string | null;
  isActive: boolean;
}

export interface CreateTokenRequest {
  name: string;
  expiryDays?: number;
}

export interface CreateTokenResponse {
  success: boolean;
  token: string;
  id: string;
  name: string;
  expiresAt: string;
  warning: string;
}

export const useTokens = () => {
  const tokens = ref<ApiToken[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Fetch all tokens for current user
   */
  async function fetchTokens() {
    loading.value = true;
    error.value = null;

    try {
      const response = await $fetch<{ tokens: ApiToken[] }>("/api/tokens");
      tokens.value = response.tokens;
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Failed to fetch tokens";
      console.error("Failed to fetch tokens:", err);
    } finally {
      loading.value = false;
    }
  }

  /**
   * Create a new API token
   */
  async function createToken(
    name: string,
    expiryDays?: number,
  ): Promise<CreateTokenResponse> {
    loading.value = true;
    error.value = null;

    try {
      const response = await $fetch<CreateTokenResponse>("/api/tokens", {
        method: "POST",
        body: { name, expiryDays },
      });

      // Refresh token list to include new token
      await fetchTokens();

      return response;
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Failed to create token";
      console.error("Failed to create token:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Revoke (soft delete) an API token
   */
  async function revokeToken(id: string): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      await $fetch(`/api/tokens/${id}`, {
        method: "DELETE",
      });

      // Remove from local list
      tokens.value = tokens.value.filter((token) => token.id !== id);
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Failed to revoke token";
      console.error("Failed to revoke token:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Format relative time for display
   */
  function formatRelativeTime(dateString: string | null): string {
    if (!dateString) return "Never";

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60)
      return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;

    return date.toLocaleDateString();
  }

  /**
   * Format expiry date
   */
  function formatExpiryDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays < 0) return "Expired";
    if (diffDays === 0) return "Expires today";
    if (diffDays === 1) return "Expires tomorrow";
    if (diffDays < 30) return `Expires in ${diffDays} days`;

    return `Expires ${date.toLocaleDateString()}`;
  }

  return {
    tokens,
    loading,
    error,
    fetchTokens,
    createToken,
    revokeToken,
    formatRelativeTime,
    formatExpiryDate,
  };
};
