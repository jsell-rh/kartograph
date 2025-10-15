/**
 * Centralized logging configuration using Pino
 *
 * Features:
 * - Beautiful colorized output in development
 * - Structured JSON logging in production
 * - Context-aware child loggers
 * - Full message logging with automatic truncation
 */

import pino from "pino";
import pretty from "pino-pretty";

// Detect if running in development mode
const isDevelopment = process.env.NODE_ENV !== "production";

// Level label mapping
const levelLabels: Record<number, string> = {
  10: "TRACE",
  20: "DEBUG",
  30: "INFO",
  40: "WARN",
  50: "ERROR",
  60: "FATAL",
};

// Create pretty stream for development (avoids worker thread issues in Nitro)
const prettyStream = isDevelopment
  ? pretty({
      colorize: true,
      translateTime: "HH:MM:ss.l",
      ignore: "pid,hostname,level",
      singleLine: false,
      messageFormat: (log, messageKey) => {
        const level = levelLabels[log.level as number] || "INFO";
        const context = log.context ? `[${log.context}]` : "";
        const message = log[messageKey];

        // Preserve newlines by indenting continuation lines
        if (typeof message === "string" && message.includes("\n")) {
          const lines = message.split("\n");
          const indent = " ".repeat(
            level.length + (context ? context.length + 1 : 0) + 1,
          );
          const formattedMessage = lines
            .map((line, i) => (i === 0 ? line : indent + line))
            .join("\n");
          return `${level} ${context} ${formattedMessage}`;
        }

        return `${level} ${context} ${message}`;
      },
    })
  : undefined;

// Create base logger
export const logger = pino(
  {
    level: process.env.LOG_LEVEL || (isDevelopment ? "debug" : "info"),
    // Base configuration
    formatters: {
      level: (label) => {
        return { level: label };
      },
    },
  },
  prettyStream,
);

/**
 * Generate correlation ID for request tracing
 */
export function generateCorrelationId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create a child logger with context and optional correlation ID
 */
export function createLogger(context: string, correlationId?: string) {
  return logger.child({
    context,
    ...(correlationId && { correlationId }),
  });
}

/**
 * Create a request-scoped logger with correlation ID and timing
 */
export function createRequestLogger(context: string) {
  const correlationId = generateCorrelationId();
  const startTime = Date.now();

  const requestLogger = logger.child({
    context,
    correlationId,
    requestStartTime: startTime,
  });

  // Add timing helper
  const addTiming = () => ({
    elapsedMs: Date.now() - startTime,
  });

  return {
    logger: requestLogger,
    correlationId,
    addTiming,
    // Helper methods that include timing
    debug: (obj: any, msg?: string) =>
      requestLogger.debug({ ...obj, ...addTiming() }, msg),
    info: (obj: any, msg?: string) =>
      requestLogger.info({ ...obj, ...addTiming() }, msg),
    warn: (obj: any, msg?: string) =>
      requestLogger.warn({ ...obj, ...addTiming() }, msg),
    error: (obj: any, msg?: string) =>
      requestLogger.error({ ...obj, ...addTiming() }, msg),
  };
}

/**
 * Helper to safely truncate large objects for logging
 */
export function truncateForLog(obj: any, maxLength = 500): string {
  const str = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  if (str.length <= maxLength) return str;
  return (
    str.substring(0, maxLength) +
    `... (${str.length - maxLength} chars truncated)`
  );
}

/**
 * Helper to log full messages with automatic preview/full toggle
 */
export function logMessage(
  log: pino.Logger,
  level: "debug" | "info" | "warn" | "error",
  message: string,
  data: any,
) {
  const preview = truncateForLog(data, 200);
  const full = typeof data === "string" ? data : JSON.stringify(data, null, 2);

  log[level]({
    message,
    preview,
    ...(full.length > 200 && { full }),
  });
}
