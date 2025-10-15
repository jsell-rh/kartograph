<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-4">
    <div class="w-full max-w-md">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-2">🗺️ Kartograph</h1>
        <p class="text-muted-foreground">Knowledge Graph Query Interface</p>
      </div>

      <!-- Auth card -->
      <div class="bg-card border rounded-lg shadow-lg p-6">
        <!-- Tabs (only show if password auth is enabled) -->
        <div
          v-if="config.public.authPasswordEnabled"
          class="flex gap-2 mb-6 bg-muted p-1 rounded-lg"
        >
          <button
            @click="activeTab = 'signin'"
            :class="[
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              activeTab === 'signin'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            ]"
          >
            Sign In
          </button>
          <button
            @click="activeTab = 'signup'"
            :class="[
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              activeTab === 'signup'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            ]"
          >
            Sign Up
          </button>
        </div>

        <!-- Error message -->
        <div
          v-if="error"
          class="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md"
        >
          <p class="text-sm text-destructive">{{ error }}</p>
        </div>

        <!-- GitHub SSO Button -->
        <button
          @click="handleGitHubSignIn"
          :disabled="loading"
          class="w-full mb-6 flex items-center justify-center gap-3 py-3 px-4 bg-[#24292F] text-white rounded-md font-medium hover:bg-[#24292F]/90 focus:outline-none focus:ring-2 focus:ring-[#24292F] focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md"
        >
          <svg
            class="w-5 h-5"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fill-rule="evenodd"
              d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z"
              clip-rule="evenodd"
            />
          </svg>
          <span v-if="loading">Connecting to GitHub...</span>
          <span v-else>Continue with GitHub</span>
        </button>

        <!-- Divider (only show if password auth is enabled) -->
        <div v-if="config.public.authPasswordEnabled" class="relative mb-6">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-border"></div>
          </div>
          <div class="relative flex justify-center text-sm">
            <span class="px-2 bg-card text-muted-foreground"
              >Or continue with email</span
            >
          </div>
        </div>

        <!-- Sign In Form (only show if password auth is enabled) -->
        <form
          v-if="config.public.authPasswordEnabled && activeTab === 'signin'"
          @submit.prevent="handleSignIn"
          class="space-y-4"
        >
          <div>
            <label
              for="signin-email"
              class="block text-sm font-medium text-foreground mb-1.5"
            >
              Email
            </label>
            <input
              id="signin-email"
              v-model="signInEmail"
              type="email"
              required
              class="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label
              for="signin-password"
              class="block text-sm font-medium text-foreground mb-1.5"
            >
              Password
            </label>
            <input
              id="signin-password"
              v-model="signInPassword"
              type="password"
              required
              class="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 px-4 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="loading">Signing in...</span>
            <span v-else>Sign In</span>
          </button>
        </form>

        <!-- Sign Up Form (only show if password auth is enabled) -->
        <form
          v-if="config.public.authPasswordEnabled && activeTab === 'signup'"
          @submit.prevent="handleSignUp"
          class="space-y-4"
        >
          <div>
            <label
              for="signup-name"
              class="block text-sm font-medium text-foreground mb-1.5"
            >
              Name
            </label>
            <input
              id="signup-name"
              v-model="signUpName"
              type="text"
              required
              class="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="John Doe"
            />
          </div>
          <div>
            <label
              for="signup-email"
              class="block text-sm font-medium text-foreground mb-1.5"
            >
              Email
            </label>
            <input
              id="signup-email"
              v-model="signUpEmail"
              type="email"
              required
              class="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label
              for="signup-password"
              class="block text-sm font-medium text-foreground mb-1.5"
            >
              Password
            </label>
            <input
              id="signup-password"
              v-model="signUpPassword"
              type="password"
              required
              minlength="8"
              class="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="••••••••"
            />
            <p class="text-xs text-muted-foreground mt-1">
              Minimum 8 characters
            </p>
          </div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 px-4 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="loading">Creating account...</span>
            <span v-else>Sign Up</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { authClient } from "~/lib/auth-client";
import { useAuthStore } from "~/stores/auth";

definePageMeta({
  layout: false,
});

const config = useRuntimeConfig();
const authStore = useAuthStore();
const route = useRoute();

const activeTab = ref<"signin" | "signup">("signin");
const loading = ref(false);
const error = ref("");

// Check for error in query params (from OAuth redirect)
onMounted(() => {
  if (route.query.error) {
    error.value = route.query.error as string;
  }
});

// Sign in form
const signInEmail = ref("");
const signInPassword = ref("");

// Sign up form
const signUpName = ref("");
const signUpEmail = ref("");
const signUpPassword = ref("");

async function handleSignIn() {
  loading.value = true;
  error.value = "";

  try {
    const result = await authClient.signIn.email({
      email: signInEmail.value,
      password: signInPassword.value,
    });

    // Update auth store with user info
    if (result.data?.user) {
      await authStore.signIn({
        id: result.data.user.id,
        name: result.data.user.name || "User",
        email: result.data.user.email || "",
      });
    }

    // Redirect to home on success (respects baseURL configuration)
    await navigateTo(config.public.baseURL);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to sign in";
  } finally {
    loading.value = false;
  }
}

async function handleSignUp() {
  loading.value = true;
  error.value = "";

  try {
    const result = await authClient.signUp.email({
      name: signUpName.value,
      email: signUpEmail.value,
      password: signUpPassword.value,
    });

    // Update auth store with user info
    if (result.data?.user) {
      await authStore.signIn({
        id: result.data.user.id,
        name: result.data.user.name || signUpName.value,
        email: result.data.user.email || signUpEmail.value,
      });
    }

    // Redirect to home on success (respects baseURL configuration)
    await navigateTo(config.public.baseURL);
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to create account";
  } finally {
    loading.value = false;
  }
}

async function handleGitHubSignIn() {
  loading.value = true;
  error.value = "";

  try {
    // Redirect to baseURL after OAuth completes
    await authClient.signIn.social({
      provider: "github",
      callbackURL: config.public.baseURL,
    });
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to sign in with GitHub";
    loading.value = false;
  }
}
</script>
