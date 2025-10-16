<template>
  <div class="h-full flex flex-col bg-card border-r border-border pt-[14px]">
    <!-- Header -->
    <div class="px-4 pb-4 border-b border-border bg-muted/30">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-foreground">Conversations</h2>
          <p class="text-xs text-muted-foreground mt-1">
            {{ conversationStore.conversations.length }} total
          </p>
        </div>
        <!-- Collapse sidebar button -->
        <button
          @click="$emit('toggle-sidebar')"
          class="p-2 hover:bg-muted rounded-lg transition-colors"
          title="Hide conversation history"
        >
          <svg
            class="w-4 h-4 text-muted-foreground hover:text-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Conversation list -->
    <div class="flex-1 overflow-y-auto">
      <!-- Loading state -->
      <div v-if="conversationStore.showLoading" class="p-4 space-y-3">
        <div
          v-for="i in 5"
          :key="i"
          class="bg-muted/30 rounded-lg p-3 animate-pulse"
        >
          <div class="h-4 bg-muted/50 rounded w-3/4 mb-2"></div>
          <div class="h-3 bg-muted/40 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="conversationStore.nonArchivedConversations.length === 0"
        class="p-8 text-center"
      >
        <svg
          class="w-16 h-16 mx-auto text-muted-foreground/30"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
        <p class="text-sm text-muted-foreground mt-4">No conversations yet</p>
        <p class="text-xs text-muted-foreground mt-1">
          Start asking questions to begin
        </p>
      </div>

      <!-- Conversation items -->
      <div v-else class="p-2 space-y-1">
        <div
          v-for="conv in conversationStore.nonArchivedConversations"
          :key="conv.id"
          class="group"
        >
          <button
            @click="selectConversation(conv.id)"
            class="w-full text-left p-3 rounded-lg transition-all relative"
            :class="[
              conv.id === conversationStore.activeConversationId
                ? 'bg-primary/10 border border-primary/30'
                : 'hover:bg-muted/50 border border-transparent',
            ]"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <h3
                  class="text-sm font-medium text-foreground truncate"
                  :title="conv.title"
                >
                  {{ conv.title }}
                </h3>
                <div class="flex items-center gap-2 mt-1">
                  <p class="text-xs text-muted-foreground whitespace-nowrap">
                    {{ conv.messageCount }}
                    {{ conv.messageCount === 1 ? "message" : "messages" }}
                  </p>
                  <span class="text-xs text-muted-foreground">•</span>
                  <p class="text-xs text-muted-foreground whitespace-nowrap">
                    {{ formatDate(conv.lastMessageAt || conv.createdAt) }}
                  </p>
                </div>
              </div>

              <!-- Action buttons -->
              <div
                class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                @click.stop
              >
                <!-- Rename Dialog -->
                <Dialog v-model:open="renameDialogOpen">
                  <button
                    @click="openRenameDialog(conv)"
                    class="p-1 hover:bg-background rounded transition-colors"
                    title="Rename"
                  >
                    <svg
                      class="w-4 h-4 text-muted-foreground hover:text-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Rename Conversation</DialogTitle>
                      <DialogDescription>
                        Enter a new name for this conversation
                      </DialogDescription>
                    </DialogHeader>
                    <div class="py-4">
                      <input
                        v-model="renameTitle"
                        type="text"
                        class="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="Conversation title"
                        @keydown.enter="confirmRename"
                      />
                    </div>
                    <DialogFooter>
                      <button
                        @click="cancelRename"
                        class="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        @click="confirmRename"
                        class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                      >
                        Rename
                      </button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <!-- Archive button -->
                <button
                  @click="archiveConversation(conv)"
                  class="p-1 hover:bg-background rounded transition-colors"
                  title="Archive"
                >
                  <svg
                    class="w-4 h-4 text-muted-foreground hover:text-foreground"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                    />
                  </svg>
                </button>

                <!-- Delete Dialog -->
                <Dialog>
                  <DialogTrigger as-child>
                    <button
                      class="p-1 hover:bg-destructive/10 rounded transition-colors"
                      title="Delete"
                      @click="conversationToDelete = conv"
                    >
                      <svg
                        class="w-4 h-4 text-muted-foreground hover:text-destructive"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Delete Conversation</DialogTitle>
                      <DialogDescription>
                        Are you sure you want to delete "{{ conv.title }}"? This
                        action cannot be undone.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter class="mt-4">
                      <DialogClose as-child>
                        <button
                          class="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted transition-colors"
                        >
                          Cancel
                        </button>
                      </DialogClose>
                      <DialogClose as-child>
                        <button
                          @click="confirmDelete(conv)"
                          class="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                        >
                          Delete
                        </button>
                      </DialogClose>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Archived conversations section -->
      <div
        v-if="conversationStore.archivedConversations.length > 0"
        class="mt-4 border-t border-border"
      >
        <button
          @click="showArchived = !showArchived"
          class="w-full p-3 text-left flex items-center justify-between hover:bg-muted/30 transition-colors"
        >
          <span class="text-sm font-medium text-muted-foreground">
            Archived ({{ conversationStore.archivedConversations.length }})
          </span>
          <svg
            class="w-4 h-4 text-muted-foreground transition-transform"
            :class="{ 'rotate-180': showArchived }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        <div v-if="showArchived" class="p-2 space-y-1">
          <button
            v-for="conv in conversationStore.archivedConversations"
            :key="conv.id"
            @click="selectConversation(conv.id)"
            class="w-full text-left p-3 rounded-lg hover:bg-muted/30 transition-all group relative opacity-60"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <h3
                  class="text-sm font-medium text-foreground truncate"
                  :title="conv.title"
                >
                  {{ conv.title }}
                </h3>
                <p class="text-xs text-muted-foreground mt-1">
                  {{ conv.messageCount }} messages
                </p>
              </div>
              <button
                @click.stop="unarchiveConversation(conv)"
                class="opacity-0 group-hover:opacity-100 p-1 hover:bg-background rounded transition-all"
                title="Unarchive"
              >
                <svg
                  class="w-4 h-4 text-muted-foreground hover:text-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                  />
                </svg>
              </button>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useConversationStore, type Conversation } from "~/stores/conversation";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";

const conversationStore = useConversationStore();
const showArchived = ref(false);
const renameTitle = ref("");
const conversationToDelete = ref<Conversation | null>(null);
const renameDialogOpen = ref(false);
const currentRenamingConv = ref<Conversation | null>(null);

const emit = defineEmits<{
  selectConversation: [id: string];
  toggleSidebar: [];
  conversationDeleted: [conversationId: string, wasActive: boolean];
}>();

function selectConversation(id: string) {
  emit("selectConversation", id);
}

function formatDate(date: Date | undefined): string {
  if (!date) return "Just now";

  const now = new Date();
  const diffMs = now.getTime() - new Date(date).getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return new Date(date).toLocaleDateString();
}

function openRenameDialog(conv: Conversation) {
  currentRenamingConv.value = conv;
  renameTitle.value = conv.title;
  renameDialogOpen.value = true;
}

async function confirmRename() {
  if (
    currentRenamingConv.value &&
    renameTitle.value &&
    renameTitle.value !== currentRenamingConv.value.title
  ) {
    await conversationStore.updateConversation(currentRenamingConv.value.id, {
      title: renameTitle.value,
    });
  }
  renameDialogOpen.value = false;
  renameTitle.value = "";
  currentRenamingConv.value = null;
}

function cancelRename() {
  renameDialogOpen.value = false;
  renameTitle.value = "";
  currentRenamingConv.value = null;
}

async function archiveConversation(conv: Conversation) {
  await conversationStore.updateConversation(conv.id, { isArchived: true });

  // If this was the active conversation, clear it
  if (conversationStore.activeConversationId === conv.id) {
    conversationStore.setActiveConversation(null);
  }
}

async function unarchiveConversation(conv: Conversation) {
  await conversationStore.updateConversation(conv.id, { isArchived: false });
}

async function confirmDelete(conv: Conversation) {
  const wasActive = conversationStore.activeConversationId === conv.id;
  await conversationStore.deleteConversation(conv.id);
  conversationToDelete.value = null;

  // Notify parent that a conversation was deleted
  emit("conversationDeleted", conv.id, wasActive);
}
</script>
