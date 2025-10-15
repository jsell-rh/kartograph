/**
 * Auth store with localStorage persistence
 * Provides optimistic authentication checks and user session management
 */

import { defineStore } from "pinia";
import { authClient } from "~/lib/auth-client";

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  lastSync: number | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    lastSync: null,
  }),

  getters: {
    userInitials: (state): string => {
      if (!state.user?.name) return "U";
      const parts = state.user.name.split(" ").filter((p) => p.length > 0);
      if (parts.length >= 2) {
        return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
      }
      return state.user.name.slice(0, 2).toUpperCase();
    },
  },

  actions: {
    /**
     * Initialize auth from localStorage (optimistic check)
     */
    async initializeAuth() {
      if (process.server) return;

      // Try to load from localStorage first (fast)
      const storedUser = localStorage.getItem("kartograph_user");
      const storedAuth = localStorage.getItem("kartograph_auth");

      if (storedUser && storedAuth === "true") {
        try {
          this.user = JSON.parse(storedUser);
          this.isAuthenticated = true;
        } catch (e) {
          // Invalid stored data, clear it
          localStorage.removeItem("kartograph_user");
          localStorage.removeItem("kartograph_auth");
        }
      }

      // Then validate with server in background
      await this.syncWithServer();
    },

    /**
     * Sync with server to validate session
     */
    async syncWithServer() {
      if (process.server) return;

      this.isLoading = true;

      try {
        const session = await authClient.getSession();

        if (session.data?.user) {
          // Session is valid, update store and localStorage
          this.user = {
            id: session.data.user.id,
            name: session.data.user.name || "User",
            email: session.data.user.email || "",
          };
          this.isAuthenticated = true;
          this.lastSync = Date.now();

          // Persist to localStorage
          localStorage.setItem("kartograph_user", JSON.stringify(this.user));
          localStorage.setItem("kartograph_auth", "true");
        } else {
          // No valid session, clear everything
          this.clearAuth();
        }
      } catch (error) {
        console.error("Failed to sync auth with server:", error);
        // On error, clear auth to be safe
        this.clearAuth();
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * Sign in (called after successful auth)
     */
    async signIn(user: User) {
      this.user = user;
      this.isAuthenticated = true;
      this.lastSync = Date.now();

      // Persist to localStorage
      localStorage.setItem("kartograph_user", JSON.stringify(user));
      localStorage.setItem("kartograph_auth", "true");
    },

    /**
     * Sign out
     */
    async signOut() {
      try {
        await authClient.signOut();
      } catch (error) {
        console.error("Sign out error:", error);
      }

      this.clearAuth();
    },

    /**
     * Clear auth state and localStorage
     */
    clearAuth() {
      this.user = null;
      this.isAuthenticated = false;
      this.lastSync = null;

      if (process.client) {
        localStorage.removeItem("kartograph_user");
        localStorage.removeItem("kartograph_auth");
      }
    },
  },
});
