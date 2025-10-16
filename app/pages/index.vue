<template>
  <div class="h-screen bg-background flex flex-col overflow-hidden">
    <!-- Header with glass-morphism -->
    <header
      class="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60 shadow-lg shadow-background/5"
    >
      <div class="px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="text-3xl">🗺️</div>
          <div>
            <h1 class="text-2xl font-bold text-foreground">Kartograph</h1>
            <p class="text-sm text-muted-foreground">
              Knowledge Graph Conversation
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="startNewConversation"
            class="px-4 py-2 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-all font-medium shadow-sm hover:shadow-md flex items-center gap-2 border border-primary/20"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Conversation
          </button>

          <!-- User profile dropdown -->
          <div class="relative" ref="userMenuRef">
            <button
              @click="showUserMenu = !showUserMenu"
              class="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium hover:opacity-90 transition-all shadow-sm"
              title="User menu"
            >
              {{ userInitials }}
            </button>

            <!-- Dropdown menu -->
            <Transition name="dropdown">
              <div
                v-if="showUserMenu"
                class="absolute right-0 mt-2 w-56 bg-card/90 backdrop-blur-md border border-border/40 rounded-lg shadow-xl overflow-hidden z-50"
              >
                <div class="px-4 py-3 border-b bg-muted/50">
                  <p class="text-sm font-medium text-foreground">
                    {{ userName }}
                  </p>
                  <p class="text-xs text-muted-foreground truncate">
                    {{ userEmail }}
                  </p>
                </div>
                <div class="py-2">
                  <NuxtLink
                    to="/settings"
                    class="w-full px-4 py-2 text-left text-sm hover:bg-muted transition-colors flex items-center gap-2 text-muted-foreground hover:text-foreground"
                    @click="showUserMenu = false"
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                    Settings
                  </NuxtLink>
                  <button
                    @click="handleSignOut"
                    class="w-full px-4 py-2 text-left text-sm hover:bg-muted transition-colors flex items-center gap-2 text-muted-foreground hover:text-destructive"
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                      />
                    </svg>
                    Logout
                  </button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </header>

    <!-- Main content - Split panel layout -->
    <main class="flex-1 flex overflow-hidden absolute inset-0 top-[73px]">
      <!-- Conversation sidebar -->
      <Transition name="slide-sidebar">
        <div
          v-if="showSidebar"
          class="w-64 flex-shrink-0 border-r border-border bg-card"
        >
          <ConversationSidebar
            @select-conversation="loadConversation"
            @toggle-sidebar="showSidebar = false"
          />
        </div>
      </Transition>

      <!-- Left panel: Conversation -->
      <div class="flex-1 flex flex-col overflow-hidden">
        <div class="flex-1 overflow-y-auto px-6 pt-24 pb-8">
          <div class="max-w-4xl mx-auto space-y-6">
            <!-- Show sidebar button when hidden -->
            <button
              v-if="!showSidebar"
              @click="showSidebar = true"
              class="fixed top-24 left-4 z-40 p-2 bg-background border border-border rounded-lg hover:bg-muted transition-all shadow-md"
              title="Show conversation history"
            >
              <svg
                class="w-5 h-5 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 5l7 7-7 7M5 5l7 7-7 7"
                />
              </svg>
            </button>
            <!-- Messages display -->
            <div class="min-h-[400px]">
              <ResponseDisplay
                :messages="messages"
                :entities="entities"
                :loading="isLoading"
                :loading-conversation="loadingConversation"
                :current-thinking-steps="currentThinkingSteps"
                @entity-click="handleEntityClick"
              />
            </div>
          </div>
        </div>

        <!-- Query input - sticky at bottom with glass-morphism -->
        <div
          class="border-t border-border/40 bg-background/70 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70 p-4 shadow-[0_-4px_12px_rgba(0,0,0,0.05)]"
        >
          <div class="max-w-4xl mx-auto">
            <QueryInput
              :loading="isLoading"
              @submit="handleSubmit"
              @stop="stopQuery"
            />
          </div>
        </div>
      </div>

      <!-- Resize handle -->
      <div
        v-if="showGraphExplorer"
        class="w-1 bg-border hover:bg-primary cursor-col-resize transition-colors relative group"
        @mousedown="startResize"
      >
        <div class="absolute inset-y-0 -left-1 -right-1"></div>
        <div
          class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-12 bg-primary/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
        ></div>
      </div>

      <!-- Right panel: Graph Explorer -->
      <Transition name="slide-in">
        <div
          v-if="showGraphExplorer"
          :style="{ width: `${graphPanelWidth}%` }"
          class="flex-shrink-0 min-w-[400px] max-w-[70vw] h-full pt-[73px]"
        >
          <div class="h-full">
            <GraphExplorer :selected-entity="selectedEntity" />
          </div>
        </div>
      </Transition>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "~/stores/auth";
import { useConversationStore } from "~/stores/conversation";

interface ThinkingStep {
  type: "thinking" | "tool_call" | "retry";
  content: string;
  metadata?: {
    toolName?: string;
    description?: string;
    timing?: number;
    error?: string;
  };
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  thinkingSteps?: ThinkingStep[];
  elapsedSeconds?: number;
}

interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

// State
const messages = ref<Message[]>([]);
const entities = ref<Entity[]>([]);
const isLoading = ref(false);
const loadingConversation = ref(false);
const currentThinkingSteps = ref<ThinkingStep[]>([]);
const selectedEntity = ref<Entity | null>(null);
const showUserMenu = ref(false);
const showGraphExplorer = ref(false);

// Resizable panel state
const graphPanelWidth = ref(50); // percentage
const isResizing = ref(false);

// Stores
const authStore = useAuthStore();
const conversationStore = useConversationStore();
const urls = useAppUrls();

// User session from store
const userName = computed(() => authStore.user?.name || "User");
const userEmail = computed(() => authStore.user?.email || "");
const userInitials = computed(() => authStore.userInitials);

// Sidebar state
const showSidebar = ref(true);

// Click outside directive
const vClickOutside = {
  mounted(el: any, binding: any) {
    el.clickOutsideEvent = (event: Event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value();
      }
    };
    document.addEventListener("click", el.clickOutsideEvent);
  },
  unmounted(el: any) {
    document.removeEventListener("click", el.clickOutsideEvent);
  },
};

// SSE connection
let eventSource: EventSource | null = null;
let abortController: AbortController | null = null;
let queryStartTime = 0;

/**
 * Start a new conversation
 */
async function startNewConversation() {
  // Stop any ongoing query
  stopQuery();

  // Clear messages and entities FIRST (before creating new conversation)
  messages.value = [];
  entities.value = [];
  currentThinkingSteps.value = [];
  selectedEntity.value = null;
  showGraphExplorer.value = false;

  // Create new conversation in store
  const newConv = await conversationStore.createConversation();
}

/**
 * Load an existing conversation
 */
async function loadConversation(id: string) {
  // Stop any ongoing query
  stopQuery();

  // Set loading state
  loadingConversation.value = true;

  try {
    // Fetch conversation with messages
    const conversation = await conversationStore.fetchConversation(id);

    if (conversation && conversation.messages) {
      // Load messages into view
      messages.value = conversation.messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.createdAt,
        thinkingSteps: msg.thinkingSteps,
        elapsedSeconds: msg.elapsedSeconds,
      }));

      // Extract entities from all messages
      entities.value = conversation.messages.flatMap(
        (msg) => msg.entities || [],
      );

      // Clear current thinking
      currentThinkingSteps.value = [];
      selectedEntity.value = null;
    }

    // Set as active conversation
    conversationStore.setActiveConversation(id);
  } finally {
    // Clear loading state
    loadingConversation.value = false;
  }
}

/**
 * Handle query submission
 */
async function handleSubmit(query: string) {
  if (isLoading.value || !query.trim()) return;

  // Ensure we have an active conversation - create one if needed
  if (!conversationStore.activeConversationId) {
    const newConv = await conversationStore.createConversation();
    if (!newConv) {
      console.error("Failed to create conversation");
      return;
    }
  }

  // Add user message
  messages.value.push({
    role: "user",
    content: query,
    timestamp: new Date(),
  });

  // Start loading
  isLoading.value = true;
  currentThinkingSteps.value = [];
  queryStartTime = Date.now();

  try {
    // Create new abort controller for this request
    abortController = new AbortController();

    // Prepare conversation history (exclude metadata, only role + content)
    // Don't include the message we just added (it's sent as 'prompt')
    const conversationHistory = messages.value.slice(0, -1).map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    // Make POST request to query endpoint with history
    const apiUrl = urls.getAppPath("/api/query");

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: query,
        conversationHistory,
        conversationId: conversationStore.activeConversationId,
      }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }

    // Process SSE stream
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let assistantMessage = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      // Decode and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const chunk of lines) {
        if (!chunk.trim() || chunk.startsWith(":")) continue;

        // Parse SSE message (event and data are on separate lines)
        const chunkLines = chunk.split("\n");
        let eventType = "";
        let dataLine = "";

        for (const line of chunkLines) {
          if (line.startsWith("event:")) {
            eventType = line.substring(6).trim();
          } else if (line.startsWith("data:")) {
            dataLine = line.substring(5).trim();
          }
        }

        if (!eventType || !dataLine) continue;

        const data = JSON.parse(dataLine);

        // Handle different event types
        switch (eventType) {
          case "text":
            // Append text delta to assistant message
            // Note: This accumulates across ALL turns, we'll use the last thinking event for final message
            assistantMessage += data.delta;
            break;

          case "thinking":
            // Each turn sends a thinking event with the full text of that turn's response
            // Store all thinking text for the thinking viewer
            if (data.text && data.text.trim()) {
              currentThinkingSteps.value.push({
                type: "thinking",
                content: data.text,
              });
            }
            break;

          case "tool_call":
            // Store tool call as structured data
            currentThinkingSteps.value.push({
              type: "tool_call",
              content: data.description || "Executing query...",
              metadata: {
                toolName: data.name,
                description: data.description,
              },
            });
            break;

          case "tool_complete":
            // Update last tool call with timing metadata
            if (currentThinkingSteps.value.length > 0) {
              const lastIndex = currentThinkingSteps.value.length - 1;
              const lastStep = currentThinkingSteps.value[lastIndex];
              // Only add timing if it's a tool call
              if (lastStep.type === "tool_call") {
                lastStep.metadata = {
                  ...lastStep.metadata,
                  timing: data.elapsedMs,
                };
              }
            }
            break;

          case "tool_error":
            // Update last tool call with error metadata
            if (currentThinkingSteps.value.length > 0) {
              const lastIndex = currentThinkingSteps.value.length - 1;
              const lastStep = currentThinkingSteps.value[lastIndex];
              if (lastStep.type === "tool_call") {
                lastStep.metadata = {
                  ...lastStep.metadata,
                  error: data.error,
                };
              }
            }
            break;

          case "retry":
            // Find and update existing retry message or add new one
            const existingRetryIndex = currentThinkingSteps.value.findIndex(
              (step) => step.type === "retry",
            );
            if (existingRetryIndex >= 0) {
              // Update existing retry message
              currentThinkingSteps.value[existingRetryIndex].content =
                data.message;
            } else {
              // Add new retry message
              currentThinkingSteps.value.push({
                type: "retry",
                content: data.message,
              });
            }
            break;

          case "context_truncated":
            // Notify user that conversation history was truncated
            currentThinkingSteps.value.push({
              type: "retry",
              content: data.message,
            });
            break;

          case "entities":
            // Add entities
            if (data.entities && Array.isArray(data.entities)) {
              entities.value.push(...data.entities);
            }
            break;

          case "done":
            // Query complete
            if (data.success) {
              // Calculate elapsed time
              const elapsedSeconds = Math.floor(
                (Date.now() - queryStartTime) / 1000,
              );

              // Get the LAST thinking step as the final response (last turn without tool calls)
              // This is the final user-facing message, not intermediate reasoning
              const thinkingSteps = currentThinkingSteps.value.filter(
                (s) => s.type === "thinking",
              );
              const finalResponse =
                thinkingSteps.length > 0
                  ? thinkingSteps[thinkingSteps.length - 1].content
                  : assistantMessage || "No response received";

              // For thinking viewer: show intermediate thinking steps and tool calls
              // Exclude the final response (last thinking step) and retries
              const thinkingOnly = currentThinkingSteps.value.filter(
                (step, index) => {
                  // Exclude retry messages
                  if (step.type === "retry") return false;

                  // If it's a thinking step, exclude if it's the last one (the final response)
                  if (step.type === "thinking") {
                    const thinkingSteps = currentThinkingSteps.value.filter(
                      (s) => s.type === "thinking",
                    );
                    const lastThinkingIndex =
                      currentThinkingSteps.value.lastIndexOf(
                        thinkingSteps[thinkingSteps.length - 1],
                      );
                    return index !== lastThinkingIndex;
                  }

                  // Keep all tool calls
                  return true;
                },
              );

              // Add assistant message
              messages.value.push({
                role: "assistant",
                content: finalResponse,
                timestamp: new Date(),
                thinkingSteps: thinkingOnly,
                elapsedSeconds,
              });

              // Add entities if provided
              if (data.entities && Array.isArray(data.entities)) {
                entities.value.push(...data.entities);
              }
            } else {
              // Handle error
              const errorMessage = data.error || "Unknown error occurred";
              // Filter out retries for error case too
              const thinkingForError = currentThinkingSteps.value.filter(
                (step) => step.type !== "retry",
              );
              messages.value.push({
                role: "assistant",
                content: `Error: ${errorMessage}`,
                timestamp: new Date(),
                thinkingSteps: thinkingForError,
              });
            }
            break;
        }
      }
    }
  } catch (error) {
    // Check if it was an abort
    if (error instanceof Error && error.name === "AbortError") {
      console.log("Query aborted by user");
      messages.value.push({
        role: "assistant",
        content: "Query stopped by user.",
        timestamp: new Date(),
        thinkingSteps: [...currentThinkingSteps.value],
      });
    } else {
      console.error("Query error:", error);
      messages.value.push({
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        timestamp: new Date(),
      });
    }
  } finally {
    // Clean up
    isLoading.value = false;
    currentThinkingSteps.value = [];
    abortController = null;
  }
}

/**
 * Stop the current query
 */
function stopQuery() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }

  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  isLoading.value = false;
}

/**
 * Handle entity click
 */
function handleEntityClick(entity: Entity) {
  selectedEntity.value = entity;
  showGraphExplorer.value = true;
  console.log("Entity clicked:", entity);
}

/**
 * Start resizing graph panel
 */
function startResize(e: MouseEvent) {
  e.preventDefault();
  isResizing.value = true;
  document.body.classList.add("resizing");

  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!isResizing.value) return;

    const containerWidth = window.innerWidth;
    const newWidth =
      ((containerWidth - moveEvent.clientX) / containerWidth) * 100;

    // Constrain between 20% and 70%
    graphPanelWidth.value = Math.max(20, Math.min(70, newWidth));
  };

  const onMouseUp = () => {
    isResizing.value = false;
    document.body.classList.remove("resizing");
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

/**
 * Handle sign out
 */
async function handleSignOut() {
  await authStore.signOut();
  await navigateTo(urls.loginPath);
}

// Watch for active conversation changes (e.g., deletion, archiving)
watch(
  () => conversationStore.activeConversationId,
  (newId, oldId) => {
    // If active conversation was cleared (deleted/archived), clear the display
    if (oldId && !newId) {
      messages.value = [];
      entities.value = [];
      currentThinkingSteps.value = [];
      selectedEntity.value = null;
      showGraphExplorer.value = false;
    }
  },
);

// Handle click outside user menu
const userMenuRef = ref<HTMLElement | null>(null);

function handleClickOutside(event: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    showUserMenu.value = false;
  }
}

// Initialize conversation store on mount
onMounted(async () => {
  await conversationStore.initializeConversations();

  // If there's an active conversation, load it
  if (conversationStore.activeConversationId) {
    await loadConversation(conversationStore.activeConversationId);
  }

  // Add click-outside listener for user menu
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  // Remove click-outside listener
  document.removeEventListener("click", handleClickOutside);
});

// Cleanup on unmount
onUnmounted(() => {
  stopQuery();
});
</script>

<style scoped>
/* Modal transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .bg-card,
.modal-leave-active .bg-card {
  transition: transform 0.3s ease;
}

.modal-enter-from .bg-card,
.modal-leave-to .bg-card {
  transform: scale(0.95);
}

/* Dropdown transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Slide-in transition for graph explorer */
.slide-in-enter-active,
.slide-in-leave-active {
  transition: all 0.3s ease;
}

.slide-in-enter-from,
.slide-in-leave-to {
  opacity: 0;
  transform: translateX(20px);
  width: 0 !important;
  min-width: 0 !important;
}

/* Slide-sidebar transition for conversation sidebar */
.slide-sidebar-enter-active,
.slide-sidebar-leave-active {
  transition: all 0.3s ease;
}

.slide-sidebar-enter-from,
.slide-sidebar-leave-to {
  opacity: 0;
  transform: translateX(-20px);
  width: 0 !important;
  min-width: 0 !important;
}

/* Prevent text selection while resizing */
body.resizing {
  user-select: none;
  cursor: col-resize !important;
}
</style>
