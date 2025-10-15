/**
 * Toast Notification Composable
 *
 * Simple toast notifications for user feedback
 */

export interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
  duration: number;
}

const toasts = ref<Toast[]>([]);

export const useToast = () => {
  function showToast(options: {
    type: "success" | "error" | "info";
    message: string;
    duration?: number;
  }) {
    const id = crypto.randomUUID();
    const duration = options.duration || 3000;

    const toast: Toast = {
      id,
      type: options.type,
      message: options.message,
      duration,
    };

    toasts.value.push(toast);

    // Auto-remove after duration
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  function success(message: string, duration?: number) {
    showToast({ type: "success", message, duration });
  }

  function error(message: string, duration?: number) {
    showToast({ type: "error", message, duration });
  }

  function info(message: string, duration?: number) {
    showToast({ type: "info", message, duration });
  }

  return {
    toasts: readonly(toasts),
    showToast,
    removeToast,
    success,
    error,
    info,
  };
};
