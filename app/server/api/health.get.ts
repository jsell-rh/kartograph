/**
 * Health check endpoint for liveness/readiness probes
 *
 * This endpoint does not require authentication and provides basic
 * health status for Kubernetes probes.
 */

export default defineEventHandler(async (event) => {
  // Return 200 OK with basic health info
  return {
    status: "ok",
    timestamp: new Date().toISOString(),
  };
});
