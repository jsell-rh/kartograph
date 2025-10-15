/**
 * Conversation store for managing chat history
 * Provides conversation list management and persistence
 */

import { defineStore } from "pinia";

export interface ThinkingStep {
  type: "thinking" | "tool_call" | "retry";
  content: string;
  metadata?: {
    toolName?: string;
    description?: string;
    timing?: number;
    error?: string;
  };
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinkingSteps?: ThinkingStep[];
  entities?: Array<{
    urn: string;
    type: string;
    id: string;
    displayName: string;
  }>;
  elapsedSeconds?: number;
  createdAt: Date;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessageAt?: Date;
  messageCount: number;
  isArchived: boolean;
  createdAt: Date;
  updatedAt: Date;
  messages?: Message[];
}

interface ConversationState {
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  isInitialLoad: boolean;
  lastFetch: number | null;
}

export const useConversationStore = defineStore("conversation", {
  state: (): ConversationState => ({
    conversations: [],
    activeConversationId: null,
    isLoading: false,
    isInitialLoad: true,
    lastFetch: null,
  }),

  getters: {
    activeConversation: (state): Conversation | null => {
      if (!state.activeConversationId) return null;
      return (
        state.conversations.find((c) => c.id === state.activeConversationId) ||
        null
      );
    },

    nonArchivedConversations: (state): Conversation[] => {
      return state.conversations.filter((c) => !c.isArchived);
    },

    archivedConversations: (state): Conversation[] => {
      return state.conversations.filter((c) => c.isArchived);
    },

    // Combined loading state for UI
    showLoading: (state): boolean => {
      return state.isLoading || state.isInitialLoad;
    },
  },

  actions: {
    /**
     * Initialize conversation state from localStorage
     */
    async initializeConversations() {
      if (process.server) return;

      // Load active conversation ID from localStorage
      const storedActiveId = localStorage.getItem(
        "kartograph_active_conversation",
      );
      if (storedActiveId) {
        this.activeConversationId = storedActiveId;
      }

      // Fetch conversations from server
      await this.fetchConversations();
    },

    /**
     * Fetch all conversations from the API
     */
    async fetchConversations() {
      if (process.server) return;

      this.isLoading = true;

      try {
        const data = await $fetch("/api/conversations");
        this.conversations = data.conversations.map((conv: any) => ({
          ...conv,
          createdAt: new Date(conv.createdAt),
          updatedAt: new Date(conv.updatedAt),
          lastMessageAt: conv.lastMessageAt
            ? new Date(conv.lastMessageAt)
            : undefined,
        }));

        this.lastFetch = Date.now();
      } catch (error) {
        console.error("Failed to fetch conversations:", error);
      } finally {
        this.isLoading = false;
        this.isInitialLoad = false;
      }
    },

    /**
     * Create a new conversation
     */
    async createConversation(
      title: string = "New Conversation",
    ): Promise<Conversation | null> {
      if (process.server) return null;

      try {
        const conversation = await $fetch<any>("/api/conversations", {
          method: "POST",
          body: { title },
        });

        const formattedConv: Conversation = {
          id: conversation.id,
          title: conversation.title || title,
          messageCount: conversation.messageCount || 0,
          isArchived: conversation.isArchived || false,
          createdAt: new Date(conversation.createdAt),
          updatedAt: new Date(conversation.updatedAt),
          lastMessageAt: conversation.lastMessageAt
            ? new Date(conversation.lastMessageAt)
            : undefined,
        };

        this.conversations.unshift(formattedConv);
        this.setActiveConversation(formattedConv.id);

        return formattedConv;
      } catch (error) {
        console.error("Failed to create conversation:", error);
        return null;
      }
    },

    /**
     * Fetch a specific conversation with its messages
     */
    async fetchConversation(id: string): Promise<Conversation | null> {
      if (process.server) return null;

      try {
        const data: any = await $fetch(`/api/conversations/${id}`);
        const conversation: Conversation = {
          id: data.id || id, // Fallback to the requested id
          title: data.title || "Untitled",
          messageCount: data.messageCount || 0,
          isArchived: data.isArchived || false,
          createdAt: new Date(data.createdAt || new Date()),
          updatedAt: new Date(data.updatedAt || new Date()),
          lastMessageAt: data.lastMessageAt
            ? new Date(data.lastMessageAt)
            : undefined,
          messages: data.messages?.map((msg: any) => ({
            ...msg,
            createdAt: new Date(msg.createdAt),
          })),
        };

        // Update in conversations list
        const index = this.conversations.findIndex((c) => c.id === id);
        if (index >= 0) {
          this.conversations[index] = conversation;
        }

        return conversation;
      } catch (error) {
        console.error("Failed to fetch conversation:", error);
        return null;
      }
    },

    /**
     * Update a conversation (rename or archive)
     */
    async updateConversation(
      id: string,
      updates: { title?: string; isArchived?: boolean },
    ): Promise<boolean> {
      if (process.server) return false;

      try {
        const updated = await $fetch(`/api/conversations/${id}`, {
          method: "PUT",
          body: updates,
        });

        const index = this.conversations.findIndex((c) => c.id === id);

        if (index >= 0 && updated) {
          const existing = this.conversations[index]!;
          this.conversations[index] = {
            id: existing.id,
            title: updates.title ?? existing.title,
            messageCount: existing.messageCount,
            isArchived: updates.isArchived ?? existing.isArchived,
            createdAt: existing.createdAt,
            updatedAt: new Date((updated as any).updatedAt || new Date()),
            lastMessageAt: existing.lastMessageAt,
            messages: existing.messages,
          };
        }

        return true;
      } catch (error) {
        console.error("Failed to update conversation:", error);
        return false;
      }
    },

    /**
     * Delete a conversation
     */
    async deleteConversation(id: string): Promise<boolean> {
      if (process.server) return false;

      try {
        await $fetch(`/api/conversations/${id}`, {
          method: "DELETE",
        });

        // Remove from store
        this.conversations = this.conversations.filter((c) => c.id !== id);

        // If this was the active conversation, clear it
        if (this.activeConversationId === id) {
          this.activeConversationId = null;
          localStorage.removeItem("kartograph_active_conversation");
        }

        return true;
      } catch (error) {
        console.error("Failed to delete conversation:", error);
        return false;
      }
    },

    /**
     * Set the active conversation
     */
    setActiveConversation(id: string | null) {
      this.activeConversationId = id;

      if (process.client) {
        if (id) {
          localStorage.setItem("kartograph_active_conversation", id);
        } else {
          localStorage.removeItem("kartograph_active_conversation");
        }
      }
    },

    /**
     * Add a message to the active conversation (optimistic update)
     */
    addMessageToActive(message: Omit<Message, "id" | "createdAt">) {
      const active = this.activeConversation;
      if (!active) return;

      const fullMessage: Message = {
        ...message,
        id: crypto.randomUUID(),
        createdAt: new Date(),
      };

      if (!active.messages) {
        active.messages = [];
      }

      active.messages.push(fullMessage);
      active.messageCount = active.messages.length;
      active.lastMessageAt = fullMessage.createdAt;
      active.updatedAt = fullMessage.createdAt;
    },

    /**
     * Clear all conversation state
     */
    clearConversations() {
      this.conversations = [];
      this.activeConversationId = null;
      this.lastFetch = null;

      if (process.client) {
        localStorage.removeItem("kartograph_active_conversation");
      }
    },
  },
});
