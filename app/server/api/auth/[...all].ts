/**
 * Better Auth API handler
 *
 * Handles all auth routes: /api/auth/*
 */

import { auth } from "../../lib/auth";
import { toWebRequest } from "h3";
import { createLogger } from "../../lib/logger";

const log = createLogger("auth-api");

export default defineEventHandler(async (event) => {
  const path = event.path;
  const method = event.method;

  log.debug({ path, method }, "Auth request");

  // Convert H3 event to Web Request for Better Auth
  const request = toWebRequest(event);

  return auth.handler(request);
});
