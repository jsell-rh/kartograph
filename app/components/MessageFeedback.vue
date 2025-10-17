<template>
  <div class="message-feedback">
    <!-- Feedback confirmation (shown after submission) -->
    <Transition name="fade">
      <div
        v-if="showConfirmation"
        class="feedback-confirmation"
        :class="confirmationClass"
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
            d="M5 13l4 4L19 7"
          />
        </svg>
        <span>{{ confirmationMessage }}</span>
      </div>
    </Transition>

    <!-- Feedback prompt (always visible) -->
    <div class="feedback-prompt">
      <span class="feedback-label">Was this helpful?</span>
      <div class="feedback-buttons">
        <button
          @click="handleFeedback('helpful')"
          class="feedback-button"
          :class="{
            active: currentRating === 'helpful',
            disabled: isSubmitting,
          }"
          :disabled="isSubmitting"
        >
          <span class="feedback-icon">👍</span>
          <span class="feedback-text">Yes</span>
        </button>
        <button
          @click="handleFeedback('unhelpful')"
          class="feedback-button"
          :class="{
            active: currentRating === 'unhelpful',
            disabled: isSubmitting,
          }"
          :disabled="isSubmitting"
        >
          <span class="feedback-icon">👎</span>
          <span class="feedback-text">No</span>
        </button>
      </div>
    </div>

    <!-- Expanded feedback form (shown after thumbs down) -->
    <Transition name="expand">
      <div v-if="showFeedbackForm" class="feedback-form">
        <div class="feedback-form-header">
          <span class="feedback-icon">👎</span>
          <span class="feedback-form-title">Sorry this wasn't helpful</span>
        </div>

        <label class="feedback-form-label">
          Help us improve (optional):
        </label>

        <textarea
          ref="feedbackTextarea"
          v-model="feedbackText"
          class="feedback-textarea"
          placeholder="What went wrong? What would have been more helpful?"
          rows="3"
          maxlength="1000"
          :disabled="isSubmitting"
        />
        <div class="character-count">
          {{ feedbackText.length }}/1000
        </div>

        <!-- Privacy notice -->
        <div class="feedback-privacy-notice">
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
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span class="text-xs text-muted-foreground">
            Your message and the assistant's response will be shared with our
            team to improve the service.
          </span>
        </div>

        <div class="feedback-form-actions">
          <Button
            variant="outline"
            @click="skipFeedback"
            :disabled="isSubmitting"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            <span>Skip</span>
          </Button>
          <Button
            variant="default"
            @click="submitFeedback"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting" class="spinner"></span>
            <template v-else>
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
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
              <span>Submit Feedback</span>
            </template>
          </Button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { Button } from "~/components/ui/button";

interface Props {
  messageId: string;
}

const props = defineProps<Props>();

const currentRating = ref<"helpful" | "unhelpful" | null>(null);
const showFeedbackForm = ref(false);
const feedbackText = ref("");
const isSubmitting = ref(false);
const showConfirmation = ref(false);
const confirmationMessage = ref("");
const confirmationClass = ref("");
const feedbackTextarea = ref<HTMLTextAreaElement | null>(null);

async function handleFeedback(rating: "helpful" | "unhelpful") {
  currentRating.value = rating;

  if (rating === "helpful") {
    // Submit immediately for thumbs up
    await submitFeedbackToServer(rating);
  } else {
    // Show feedback form for thumbs down
    showFeedbackForm.value = true;

    // Auto-focus textarea
    await nextTick();
    feedbackTextarea.value?.focus();
  }
}

function skipFeedback() {
  // Submit thumbs down without text
  submitFeedbackToServer("unhelpful");
}

async function submitFeedback() {
  await submitFeedbackToServer("unhelpful", feedbackText.value);
}

async function submitFeedbackToServer(
  rating: "helpful" | "unhelpful",
  text?: string,
) {
  isSubmitting.value = true;

  try {
    await $fetch("/api/feedback", {
      method: "POST",
      body: {
        messageId: props.messageId,
        rating,
        feedbackText: text || null,
      },
    });

    // Show confirmation
    confirmationMessage.value =
      rating === "helpful"
        ? "Thanks for your feedback!"
        : "Thank you! We'll use your feedback to improve our responses.";
    confirmationClass.value = "success";
    showConfirmation.value = true;

    // Hide feedback form
    showFeedbackForm.value = false;

    // Hide confirmation after 3 seconds
    setTimeout(() => {
      showConfirmation.value = false;
    }, 3000);
  } catch (error) {
    console.error("Failed to submit feedback:", error);

    confirmationMessage.value =
      "Failed to submit feedback. Please try again.";
    confirmationClass.value = "error";
    showConfirmation.value = true;

    setTimeout(() => {
      showConfirmation.value = false;
    }, 3000);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.message-feedback {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.feedback-confirmation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.feedback-confirmation.success {
  background-color: rgb(220 252 231 / 0.5);
  color: rgb(22 163 74);
  border: 1px solid rgb(134 239 172 / 0.5);
}

.feedback-confirmation.error {
  background-color: rgb(254 226 226 / 0.5);
  color: rgb(220 38 38);
  border: 1px solid rgb(252 165 165 / 0.5);
}

.feedback-prompt {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.feedback-label {
  font-size: 0.875rem;
  color: var(--muted-foreground);
  font-weight: 500;
}

.feedback-buttons {
  display: flex;
  gap: 0.5rem;
}

.feedback-button {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  background-color: var(--background);
  color: var(--muted-foreground);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.feedback-button:hover:not(.disabled) {
  background-color: var(--muted);
  border-color: var(--primary);
  color: var(--foreground);
}

.feedback-button.active {
  background-color: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.feedback-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-icon {
  font-size: 1rem;
  line-height: 1;
}

.feedback-text {
  font-weight: 500;
}

.feedback-form {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: var(--muted);
  border: 1px solid var(--border);
}

.feedback-form-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.feedback-form-title {
  font-weight: 500;
  color: var(--foreground);
}

.feedback-form-label {
  display: block;
  font-size: 0.875rem;
  color: var(--muted-foreground);
  margin-bottom: 0.5rem;
}

.feedback-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid var(--border);
  border-radius: 0.5rem;
  background-color: var(--card);
  color: var(--foreground);
  font-size: 0.875rem;
  resize: vertical;
  min-height: 4rem;
  font-family: inherit;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
  transition: all 0.2s ease;
}

.feedback-textarea::placeholder {
  color: var(--muted-foreground);
  opacity: 0.6;
}

.feedback-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1), 0 1px 3px 0 rgb(0 0 0 / 0.1);
}

.feedback-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.character-count {
  display: flex;
  justify-content: flex-end;
  font-size: 0.75rem;
  color: var(--muted-foreground);
  margin-top: 0.25rem;
  opacity: 0.7;
}

.feedback-privacy-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 0.75rem;
  background-color: var(--muted);
  border-radius: 0.375rem;
  border: 1px solid var(--border);
}

.feedback-privacy-notice svg {
  flex-shrink: 0;
  color: var(--muted-foreground);
  opacity: 0.7;
}

.feedback-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid currentColor;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
