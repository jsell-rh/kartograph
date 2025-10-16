/**
 * Onboarding tour composable using Driver.js
 *
 * Provides app tour for first-time users and version change notifications
 */

import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import "~/assets/css/driver-custom.css";

export function useOnboarding() {
  const ONBOARDING_KEY = "kartograph_onboarding_completed";
  const LAST_VERSION_KEY = "kartograph_last_version";

  /**
   * Check if user has completed onboarding
   */
  function hasCompletedOnboarding(): boolean {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(ONBOARDING_KEY) === "true";
  }

  /**
   * Mark onboarding as completed
   */
  function completeOnboarding() {
    if (typeof window === "undefined") return;
    localStorage.setItem(ONBOARDING_KEY, "true");
  }

  /**
   * Check if app version has changed since last visit
   */
  function hasVersionChanged(currentVersion: string): boolean {
    if (typeof window === "undefined") return false;
    const lastVersion = localStorage.getItem(LAST_VERSION_KEY);
    return lastVersion !== null && lastVersion !== currentVersion;
  }

  /**
   * Update last seen version
   */
  function updateLastVersion(version: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem(LAST_VERSION_KEY, version);
  }

  /**
   * Start the app tour
   */
  function startTour(onComplete?: () => void, options?: {
    showGraphExplorer?: (show: boolean, entity?: any) => void;
    githubUrl?: string;
  }) {
    const driverObj = driver({
      showProgress: true,
      animate: true,
      allowClose: true,
      overlayOpacity: 0.75,
      steps: [
        {
          popover: {
            title: "Welcome to Kartograph! 🗺️",
            description:
              "Ask questions about Red Hat's applications and infrastructure. " +
              "Powered by Claude Sonnet 4.5 and a knowledge graph built from app-interface.",
            side: "top",
            align: "center",
            onPopoverRender: () => {
              // Ensure graph is closed on this step
              if (options?.showGraphExplorer) {
                options.showGraphExplorer(false);
              }
            },
          },
        },
        {
          element: ".query-input-container",
          popover: {
            title: "Query the Knowledge Graph with Natural Language",
            description:
              "Kartograph Excels at Questions Related to:<br/>" +
              "• SRE Incident Response<br/>" +
              "• User Onboarding?<br/>" +
              "• Technical Discovery<br/>",
            side: "top",
            align: "center",
            onPopoverRender: () => {
              // Ensure graph is closed on this step
              if (options?.showGraphExplorer) {
                options.showGraphExplorer(false);
              }
            },
          },
        },
        {
          popover: {
            title: "Interactive Graph Explorer",
            description:
              "Kartograph includes clickable entities in its responses. Click an entity to open the graph explorer on the right. " +
              "<br/><br/>Select an entity (node) to view additional metadata! " +
              "<br/><br/><em class='text-xs opacity-70'>We've opened a sample graph for you on the right →</em>",
            side: "left",
            align: "start",
            onPopoverRender: () => {
              // Show sample graph explorer when this step is active
              if (options?.showGraphExplorer) {
                const sampleEntity = {
                  urn: "urn:demo:service:payment-api",
                  type: "service",
                  id: "payment-api",
                  displayName: "Payment API (Demo)",
                };
                options.showGraphExplorer(true, sampleEntity);
              }

              // Make graph explorer interactive by modifying overlay
              setTimeout(() => {
                const overlay = document.querySelector('.driver-overlay') as HTMLElement;
                if (overlay) {
                  overlay.style.pointerEvents = 'none';
                }

                // Re-enable pointer events on popover
                const popover = document.querySelector('.driver-popover') as HTMLElement;
                if (popover) {
                  popover.style.pointerEvents = 'auto';
                }

                // Temporarily elevate graph explorer above overlay during this step only
                const graphExplorer = document.querySelector('.graph-explorer') as HTMLElement;
                if (graphExplorer) {
                  // Driver overlay is typically z-index: 10000
                  // User menu is z-50 which in Tailwind is 50
                  // So we need to be above overlay (10000) but that will cover menu
                  // Solution: Set to 10001 only during this step, restore later
                  graphExplorer.style.zIndex = '10001';

                  // Prevent clicks on graph explorer from propagating to overlay/tour
                  graphExplorer.addEventListener('click', (e) => {
                    e.stopPropagation();
                  }, { capture: true });
                }
              }, 100);
            },
          },
        },
        {
          element: ".conversation-sidebar",
          popover: {
            title: "Conversation History",
            description:
              "All your conversations are automatically saved here. " +
              "Switch between conversations or start a new one anytime!",
            side: "right",
            align: "start",
            onPopoverRender: () => {
              // Hide graph explorer when moving to next step
              if (options?.showGraphExplorer) {
                options.showGraphExplorer(false);
              }

              // Restore overlay pointer events and graph z-index for other steps
              setTimeout(() => {
                const overlay = document.querySelector('.driver-overlay') as HTMLElement;
                if (overlay) {
                  overlay.style.pointerEvents = '';
                }

                // Restore graph explorer z-index
                const graphExplorer = document.querySelector('.graph-explorer') as HTMLElement;
                if (graphExplorer) {
                  graphExplorer.style.zIndex = '';
                }
              }, 100);
            },
          },
        },
        {
          element: ".user-menu-button",
          popover: {
            title: "Settings & API Tokens",
            description:
              "Create API tokens here for Claude Code MCP integration. " +
              "Use Kartograph as a tool within Claude Code or any MCP-compatible AI assistant!",
            side: "bottom",
            align: "end",
            onPopoverRender: () => {
              // Ensure graph is closed on this step
              if (options?.showGraphExplorer) {
                options.showGraphExplorer(false);
              }
            },
          },
        },
        {
          popover: {
            title: "Ready to Explore! 🚀",
            description: options?.githubUrl
              ? `You're all set! Have feedback or found a bug? <a href="${options.githubUrl}/issues/new" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">Submit an issue on GitHub</a>.`
              : "You're all set! Start asking questions and explore the knowledge graph.",
            side: "top",
            align: "center",
            onPopoverRender: () => {
              // Ensure graph is closed on this step
              if (options?.showGraphExplorer) {
                options.showGraphExplorer(false);
              }
            },
          },
        },
      ],
      nextBtnText: "Next →",
      prevBtnText: "← Back",
      doneBtnText: "Let's Go! 🚀",
      onDestroyed: () => {
        // Restore graph explorer z-index
        const graphExplorer = document.querySelector('.graph-explorer') as HTMLElement;
        if (graphExplorer) {
          graphExplorer.style.zIndex = '';
        }

        // Close graph explorer if still open
        if (options?.showGraphExplorer) {
          options.showGraphExplorer(false);
        }

        completeOnboarding();
        if (onComplete) {
          onComplete();
        }
      },
    });

    driverObj.drive();
  }

  /**
   * Reset onboarding (for testing or re-showing tour)
   */
  function resetOnboarding() {
    if (typeof window === "undefined") return;
    localStorage.removeItem(ONBOARDING_KEY);
  }

  return {
    hasCompletedOnboarding,
    completeOnboarding,
    hasVersionChanged,
    updateLastVersion,
    startTour,
    resetOnboarding,
  };
}
