<template>
  <div
    class="graph-explorer h-full flex flex-col bg-card/80 backdrop-blur-sm border-l border-border/40 relative"
  >
    <!-- Header with glass-morphism -->
    <div
      class="border-b border-border/40 bg-card/60 backdrop-blur-md p-4 flex-shrink-0"
    >
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <h2 class="text-lg font-semibold text-foreground">Graph Explorer</h2>
          <span v-if="selectedEntity" class="text-sm text-muted-foreground">
            • {{ selectedEntity.displayName }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="resetGraph"
            class="px-3 py-1.5 hover:bg-muted rounded-lg transition-colors flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            title="Clear all nodes and edges"
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span class="font-medium">Clear Graph</span>
          </button>
          <button
            @click="emit('closeExplorer')"
            class="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Hide graph explorer"
          >
            <svg
              class="w-5 h-5 text-muted-foreground hover:text-foreground"
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
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="flex items-center gap-4 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5">
          <div class="w-2 h-2 rounded-full bg-primary"></div>
          <span>{{ nodeCount }} nodes</span>
        </div>
        <div class="flex items-center gap-1.5">
          <svg
            class="w-3 h-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
          <span>{{ edgeCount }} edges</span>
        </div>
      </div>

      <!-- Instructions -->
      <div v-if="nodeCount === 0" class="mt-3 space-y-1">
        <div class="text-xs text-muted-foreground/70 italic">
          Click an entity in the conversation to add it to the graph
        </div>
      </div>
      <div v-else class="mt-3 space-y-1.5">
        <div class="text-xs text-muted-foreground/70 flex items-center gap-2">
          <svg
            class="w-3 h-3 flex-shrink-0"
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
          <span>Click node for details • Double-click to expand/collapse</span>
        </div>
        <div
          class="text-xs text-muted-foreground/60 flex items-center gap-1.5 pl-5"
        >
          <svg
            class="w-3 h-3 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 6v6m0 0v6m0-6h6m-6 0H6"
            />
          </svg>
          <span>Click more entities to add to graph</span>
        </div>
      </div>

      <!-- View Controls -->
      <div
        class="flex items-center justify-between mt-3 pt-3 border-t border-border/40"
      >
        <div class="flex items-center gap-2">
          <button
            @click="fitToView"
            class="px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 transition-all"
          >
            Fit View
          </button>
          <button
            @click="centerOnSelected"
            :disabled="!hasSelectedNode"
            class="px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Center
          </button>
        </div>

        <!-- Zoom controls -->
        <div class="flex items-center gap-1 bg-muted rounded p-1">
          <button
            @click="zoomIn"
            class="p-1.5 hover:bg-background rounded transition-colors"
            title="Zoom in"
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
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
          </button>
          <button
            @click="zoomOut"
            class="p-1.5 hover:bg-background rounded transition-colors"
            title="Zoom out"
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
                d="M20 12H4"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Cytoscape container and overlays -->
    <div class="flex-1 relative bg-background/50 min-h-0">
      <!-- Cytoscape canvas -->
      <div ref="cytoscapeContainer" class="absolute inset-0"></div>

      <!-- Empty state overlay - shown when no nodes -->
      <div
        v-if="nodeCount === 0"
        class="absolute inset-0 flex items-center justify-center z-10 pointer-events-none"
      >
        <div class="text-center max-w-md px-8">
          <div
            class="mx-auto w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center mb-6"
          >
            <svg
              class="w-12 h-12 text-primary/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
              />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-foreground mb-2">
            Graph Explorer Ready
          </h3>
          <p class="text-sm text-muted-foreground mb-4">
            Click on any entity in a conversation response to visualize its
            relationships
          </p>
          <div
            class="inline-flex items-center gap-2 px-4 py-2 bg-muted/50 rounded-lg text-xs text-muted-foreground"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span
              >Entities appear as clickable tags in assistant responses</span
            >
          </div>
        </div>
      </div>

      <!-- Loading overlay -->
      <div
        v-if="loading"
        class="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-10 pointer-events-none"
      >
        <div class="flex items-center gap-3 text-muted-foreground">
          <div
            class="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"
          ></div>
          <span class="text-sm">Loading relationships...</span>
        </div>
      </div>

      <!-- Color Legend - Top Right -->
      <div class="absolute top-4 right-4 z-10 pointer-events-auto">
        <transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition-all duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="showLegend"
            class="bg-card/80 backdrop-blur-md border border-border/40 rounded-lg shadow-xl p-3 max-w-xs"
          >
            <div
              class="text-xs font-semibold text-foreground mb-2 flex items-center gap-2"
            >
              <svg
                class="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                />
              </svg>
              Node Types
            </div>
            <div class="grid grid-cols-2 gap-x-3 gap-y-1.5">
              <div
                v-for="item in legendItems"
                :key="item.type"
                class="flex items-center gap-1.5"
              >
                <div
                  class="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  :style="{ backgroundColor: item.color }"
                ></div>
                <span class="text-xs text-muted-foreground truncate">{{
                  item.type
                }}</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- Toggle Button -->
        <button
          @click="showLegend = !showLegend"
          class="mt-2 w-full px-3 py-2 bg-card/80 backdrop-blur-md border border-border/40 rounded-lg shadow-xl hover:bg-muted/50 transition-all text-xs font-medium text-foreground flex items-center justify-center gap-2"
          :title="showLegend ? 'Hide legend' : 'Show legend'"
        >
          <svg
            class="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
            />
          </svg>
          {{ showLegend ? "Hide" : "Legend" }}
        </button>
      </div>
    </div>

    <!-- Node Details Panel - Bottom Slide Up (Outside Cytoscape Container) -->
    <transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-full opacity-0"
    >
      <div
        v-if="selectedNodeDetails"
        :style="{ height: `${detailsPanelHeight}px` }"
        class="absolute bottom-0 left-0 right-0 bg-card/90 backdrop-blur-md border-t border-border/40 shadow-2xl z-50 flex flex-col pointer-events-auto"
        @mousedown.stop
        @click.stop
        @dblclick.stop
        @contextmenu.stop
      >
        <!-- Resize Handle -->
        <div
          class="h-2 w-full bg-border/40 hover:bg-primary cursor-row-resize transition-colors relative group flex items-center justify-center"
          @mousedown="startPanelResize"
        >
          <div
            class="w-12 h-1 bg-primary/50 rounded-full group-hover:bg-primary group-hover:h-1.5 transition-all"
          ></div>
        </div>
        <!-- Panel Header with glass-morphism -->
        <div
          class="flex-shrink-0 border-b border-border/40 bg-card/60 backdrop-blur-md p-4"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <div
                  class="w-3 h-3 rounded-full flex-shrink-0"
                  :style="{ backgroundColor: selectedNodeDetails.color }"
                ></div>
                <h3 class="text-lg font-semibold text-foreground truncate">
                  {{ selectedNodeDetails.displayName }}
                </h3>
              </div>
              <div
                class="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <span
                  class="px-2 py-0.5 bg-primary/10 text-primary rounded-full font-medium"
                >
                  {{ selectedNodeDetails.type }}
                </span>
              </div>
            </div>
            <button
              @click="closeNodeDetails"
              class="flex-shrink-0 ml-2 p-1.5 hover:bg-muted rounded-lg transition-colors"
              title="Close"
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <div class="text-xs font-mono text-muted-foreground/70 truncate">
            {{ selectedNodeDetails.urn }}
          </div>
        </div>

        <!-- Panel Content -->
        <div ref="panelContent" class="flex-1 overflow-y-auto p-4 space-y-6">
          <!-- Scalar Properties -->
          <div
            v-if="
              selectedNodeDetails.scalars &&
              selectedNodeDetails.scalars.length > 0
            "
          >
            <h4
              class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"
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
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              Properties
            </h4>
            <div class="space-y-3">
              <div
                v-for="prop in sortedScalars"
                :key="prop.name"
                class="bg-muted/30 rounded-lg p-3 border border-border/50"
              >
                <div class="text-xs font-medium text-muted-foreground mb-1">
                  {{ prop.displayName }}
                </div>
                <!-- URL values as clickable links -->
                <a
                  v-if="isUrl(prop.value)"
                  :href="prop.value"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-primary hover:underline break-all flex items-center gap-1.5"
                >
                  {{ prop.value }}
                  <svg
                    class="w-3 h-3 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
                <!-- Boolean values with icon -->
                <div
                  v-else-if="typeof prop.value === 'boolean'"
                  class="text-sm flex items-center gap-2"
                >
                  <span
                    v-if="prop.value"
                    class="text-green-500 flex items-center gap-1"
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
                    True
                  </span>
                  <span
                    v-else
                    class="text-muted-foreground flex items-center gap-1"
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
                    False
                  </span>
                </div>
                <!-- Multi-line text values -->
                <pre
                  v-else-if="String(prop.value).includes('\n')"
                  class="text-sm text-foreground whitespace-pre-wrap break-words font-sans"
                  >{{ prop.value }}</pre
                >
                <!-- Regular values -->
                <div v-else class="text-sm text-foreground break-words">
                  {{ prop.value }}
                </div>
              </div>
            </div>
          </div>

          <!-- Relationships -->
          <div
            v-if="
              selectedNodeDetails.relationships &&
              selectedNodeDetails.relationships.length > 0
            "
          >
            <h4
              class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"
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
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                />
              </svg>
              Relationships
            </h4>
            <div class="space-y-3">
              <div
                v-for="rel in selectedNodeDetails.relationships"
                :key="`${rel.direction}-${rel.predicate}`"
                class="bg-muted/30 rounded-lg p-3 border border-border/50"
              >
                <div class="flex items-center gap-2 mb-2">
                  <!-- Direction indicator -->
                  <div
                    :class="[
                      'flex items-center justify-center w-5 h-5 rounded flex-shrink-0',
                      rel.direction === 'outgoing'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-green-500/20 text-green-400',
                    ]"
                    :title="
                      rel.direction === 'outgoing'
                        ? 'Outgoing relationship'
                        : 'Incoming relationship'
                    "
                  >
                    <!-- Outgoing arrow -->
                    <svg
                      v-if="rel.direction === 'outgoing'"
                      class="w-3 h-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2.5"
                        d="M17 8l4 4m0 0l-4 4m4-4H3"
                      />
                    </svg>
                    <!-- Incoming arrow -->
                    <svg
                      v-else
                      class="w-3 h-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2.5"
                        d="M7 16l-4-4m0 0l4-4m-4 4h18"
                      />
                    </svg>
                  </div>
                  <div class="text-xs font-medium text-primary">
                    {{ rel.displayName }}
                  </div>
                  <span class="text-xs text-muted-foreground/60">
                    ({{ rel.direction }})
                  </span>
                </div>
                <div class="space-y-1.5">
                  <button
                    v-for="(target, idx) in rel.targets"
                    :key="idx"
                    @click="handleRelationshipTargetClick(target)"
                    class="flex items-center gap-2 text-sm w-full hover:bg-muted/50 rounded px-2 py-1.5 transition-colors cursor-pointer group"
                  >
                    <div
                      class="w-2 h-2 rounded-full flex-shrink-0"
                      :style="{ backgroundColor: getColorForType(target.type) }"
                    ></div>
                    <span
                      class="text-foreground truncate group-hover:text-primary"
                      >{{ target.name }}</span
                    >
                    <span
                      class="text-xs text-muted-foreground/70 flex-shrink-0 group-hover:text-primary/70"
                      >({{ target.type }})</span
                    >
                    <svg
                      class="w-3 h-3 ml-auto opacity-0 group-hover:opacity-100 transition-opacity"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div
            v-if="
              (!selectedNodeDetails.scalars ||
                selectedNodeDetails.scalars.length === 0) &&
              (!selectedNodeDetails.relationships ||
                selectedNodeDetails.relationships.length === 0)
            "
            class="text-center py-8 text-muted-foreground/70"
          >
            <svg
              class="w-12 h-12 mx-auto mb-3 opacity-50"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
              />
            </svg>
            <p class="text-sm">No metadata available</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";

// Register layout
cytoscape.use(coseBilkent);

interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

interface Props {
  selectedEntity?: Entity | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  closeExplorer: [];
}>();

const cytoscapeContainer = ref<HTMLElement | null>(null);
let cy: cytoscape.Core | null = null;

const nodeCount = ref(0);
const edgeCount = ref(0);
const loading = ref(false);
const detailsPanelHeight = ref(350); // Default height in pixels
const isResizingPanel = ref(false);

interface NodeDetails {
  urn: string;
  type: string;
  displayName: string;
  color: string;
  scalars: Array<{
    name: string;
    displayName: string;
    value: any;
  }>;
  relationships: Array<{
    predicate: string;
    displayName: string;
    direction: "outgoing" | "incoming";
    targets: Array<{
      name: string;
      type: string;
    }>;
  }>;
}

const selectedNodeDetails = ref<NodeDetails | null>(null);
const showLegend = ref(false);
const hasSelectedNode = ref(false);

/**
 * Sorted scalar properties with description first, then alphabetically
 */
const sortedScalars = computed(() => {
  if (!selectedNodeDetails.value?.scalars) return [];

  const scalars = [...selectedNodeDetails.value.scalars];

  // Find description property (case-insensitive)
  const descriptionIndex = scalars.findIndex(s =>
    s.name.toLowerCase().includes('description')
  );

  let description = null;
  if (descriptionIndex >= 0) {
    description = scalars.splice(descriptionIndex, 1)[0];
  }

  // Sort remaining properties alphabetically by display name
  const sortedOthers = scalars.sort((a, b) =>
    a.displayName.localeCompare(b.displayName)
  );

  // Return with description first if it exists
  return description ? [description, ...sortedOthers] : sortedOthers;
});

/**
 * Legend items computed from color map
 */
const legendItems = computed(() => {
  const colorMap: Record<string, string> = {
    Application: "#60a5fa",
    Service: "#34d399",
    Endpoint: "#fbbf24",
    Route: "#a78bfa",
    Namespace: "#f472b6",
    User: "#818cf8",
    Role: "#2dd4bf",
    Cluster: "#fb923c",
    ExternalResource: "#22d3ee",
    Alert: "#f87171",
    SLO: "#a3e635",
    JiraProject: "#c084fc",
  };

  return Object.entries(colorMap).map(([type, color]) => ({ type, color }));
});

/**
 * Initialize Cytoscape instance
 */
onMounted(async () => {
  if (!cytoscapeContainer.value) return;

  cy = cytoscape({
    container: cytoscapeContainer.value,

    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          label: "data(label)",
          width: "data(size)",
          height: "data(size)",
          "font-size": "12px",
          "font-weight": "500",
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "wrap",
          "text-max-width": "80px",
          color: "#ffffff",
          "text-outline-color": "data(color)",
          "text-outline-width": 2,
          "border-width": 2,
          "border-color": "#ffffff",
          "border-opacity": 0.8,
          "shadow-blur": 12,
          "shadow-color": "#000000",
          "shadow-opacity": 0.2,
          "shadow-offset-x": 0,
          "shadow-offset-y": 3,
        },
      },
      {
        selector: "node:selected",
        style: {
          "border-width": 5,
          "border-color": "#3b82f6",
          "shadow-blur": 16,
          "shadow-opacity": 0.3,
        },
      },
      {
        selector: "node.expanded",
        style: {
          "border-style": "double",
          "border-width": 6,
        },
      },
      {
        selector: "node:active",
        style: {
          "overlay-color": "#3b82f6",
          "overlay-padding": 8,
          "overlay-opacity": 0.1,
        },
      },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "#cbd5e1",
          "target-arrow-color": "#cbd5e1",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(label)",
          "font-size": "10px",
          "font-weight": "500",
          "text-rotation": "autorotate",
          "text-margin-y": -12,
          color: "#64748b",
          "text-background-color": "#ffffff",
          "text-background-opacity": 0.95,
          "text-background-padding": "4px",
          "text-background-shape": "roundrectangle",
          opacity: 0.6,
        },
      },
      {
        selector: "edge:selected",
        style: {
          "line-color": "#3b82f6",
          "target-arrow-color": "#3b82f6",
          width: 4,
          opacity: 1,
        },
      },
    ],

    layout: {
      name: "cose-bilkent",
      animate: true,
      animationDuration: 600,
      fit: true,
      padding: 60,
      nodeDimensionsIncludeLabels: true,
      nodeRepulsion: 15000, // Increased for more spacing between nodes
      idealEdgeLength: 100, // Increased for longer edges to spread nodes
      edgeElasticity: 0.35, // Reduced to allow more spreading
      nestingFactor: 0.1, // Increased for better hierarchy
      gravity: 0.15, // Further reduced to minimize central clustering
      numIter: 5000, // More iterations for better convergence
      tile: true,
      tilingPaddingVertical: 25, // Increased padding for more space
      tilingPaddingHorizontal: 25,
      gravityRange: 4.5, // Increased range for better distribution
      gravityCompound: 1.0, // Reduced compound gravity
      gravityRangeCompound: 2.0, // Increased compound range
      randomize: false,
      quality: "proof", // Higher quality layout algorithm
    },

    minZoom: 0.1,
    maxZoom: 4, // Increased from 3 for more zoom flexibility
    wheelSensitivity: 2,
  });

  // Double-click to expand/collapse
  cy.on("dbltap", "node", handleNodeDoubleClick);

  // Single click to show details
  cy.on("tap", "node", handleNodeClick);

  // Click on background to close details panel
  cy.on("tap", (evt) => {
    if (evt.target === cy) {
      closeNodeDetails();
    }
  });

  // Update stats on graph changes
  cy.on("add remove", updateStats);

  // Update hasSelectedNode when selection changes
  cy.on("select unselect", () => {
    hasSelectedNode.value = cy.$("node:selected").length > 0;
  });

  updateStats();

  // If there's a selected entity when cytoscape initializes, add it now
  if (props.selectedEntity) {
    const existingNode = cy.getElementById(props.selectedEntity.urn);
    if (existingNode.length === 0) {
      await addEntityToGraph(props.selectedEntity);
    }
  }
});

/**
 * Clean up predicate name for display
 */
function cleanPredicateName(predicate: string): string {
  // Remove urn:predicate: prefix and angle brackets
  let cleaned = predicate.replace(/^<?urn:predicate:/, "").replace(/>?$/, "");

  // Convert camelCase to space-separated words
  cleaned = cleaned.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();

  // Capitalize first letter
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

/**
 * Handle node click - fetch and show details
 */
async function handleNodeClick(evt: any) {
  const node = evt.target;
  const nodeId = node.id();
  const nodeData = node.data();

  try {
    // Fetch full entity details from API
    const encodedUrn = encodeURIComponent(nodeId);
    const data = await $fetch(`/api/entity/${encodedUrn}/relationships`);

    // Find the source node (should be the first node in the response)
    const sourceNode = data.nodes.find((n: any) => n.data.id === nodeId);
    if (!sourceNode) {
      console.error("Source node not found in response");
      return;
    }

    // Build details object
    const details: NodeDetails = {
      urn: nodeId,
      type: nodeData.type,
      displayName: nodeData.displayName,
      color: nodeData.color,
      scalars: [],
      relationships: [],
    };

    // Extract scalar metadata from source node
    if (sourceNode.data.metadata) {
      details.scalars = Object.entries(sourceNode.data.metadata).map(
        ([predicate, value]) => ({
          name: predicate,
          displayName: cleanPredicateName(predicate),
          value: value,
        }),
      );
    }

    // Group edges by predicate and direction to build relationships
    const outgoingMap = new Map<
      string,
      Array<{ name: string; type: string }>
    >();
    const incomingMap = new Map<
      string,
      Array<{ name: string; type: string }>
    >();

    for (const edge of data.edges) {
      const predicate = edge.data.type;

      // Outgoing edges (this node is the source)
      if (edge.data.source === nodeId) {
        const targetNode = data.nodes.find(
          (n: any) => n.data.id === edge.data.target,
        );

        if (targetNode) {
          if (!outgoingMap.has(predicate)) {
            outgoingMap.set(predicate, []);
          }
          outgoingMap.get(predicate)!.push({
            name: targetNode.data.label,
            type: targetNode.data.type,
          });
        }
      }

      // Incoming edges (this node is the target)
      if (edge.data.target === nodeId) {
        const sourceNode = data.nodes.find(
          (n: any) => n.data.id === edge.data.source,
        );

        if (sourceNode) {
          if (!incomingMap.has(predicate)) {
            incomingMap.set(predicate, []);
          }
          incomingMap.get(predicate)!.push({
            name: sourceNode.data.label,
            type: sourceNode.data.type,
          });
        }
      }
    }

    // Convert maps to array, combining outgoing and incoming
    details.relationships = [
      ...Array.from(outgoingMap.entries()).map(([predicate, targets]) => ({
        predicate,
        displayName: cleanPredicateName(predicate),
        direction: "outgoing" as const,
        targets,
      })),
      ...Array.from(incomingMap.entries()).map(([predicate, targets]) => ({
        predicate,
        displayName: cleanPredicateName(predicate),
        direction: "incoming" as const,
        targets,
      })),
    ];

    selectedNodeDetails.value = details;
  } catch (error) {
    console.error("Error fetching node details:", error);
  }
}

/**
 * Close node details panel
 */
function closeNodeDetails() {
  selectedNodeDetails.value = null;
}

/**
 * Start resizing the details panel
 */
function startPanelResize(e: MouseEvent) {
  e.preventDefault();
  e.stopPropagation();
  isResizingPanel.value = true;
  document.body.classList.add("resizing-panel");

  const startY = e.clientY;
  const startHeight = detailsPanelHeight.value;

  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!isResizingPanel.value) return;

    // Calculate new height (moving up = larger panel)
    const deltaY = startY - moveEvent.clientY;
    const newHeight = startHeight + deltaY;

    // Constrain between 200px and 80% of viewport height
    const maxHeight = window.innerHeight * 0.8;
    detailsPanelHeight.value = Math.max(200, Math.min(maxHeight, newHeight));
  };

  const onMouseUp = () => {
    isResizingPanel.value = false;
    document.body.classList.remove("resizing-panel");
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

/**
 * Handle clicking on a relationship target to add it to the graph
 */
async function handleRelationshipTargetClick(target: {
  name: string;
  type: string;
}) {
  // Construct entity URN from name and type
  const entity: Entity = {
    urn: `<urn:${target.type}:${target.name}>`,
    type: target.type,
    id: target.name,
    displayName: target.name.replace(/-/g, " ").replace(/_/g, " "),
  };

  // Check if node already exists
  if (cy) {
    const existingNode = cy.getElementById(entity.urn);
    if (existingNode.length > 0) {
      // Node exists, just select and focus it
      cy.elements().unselect();
      existingNode.select();
      cy.animate(
        {
          center: { eles: existingNode },
          zoom: 1.5,
        },
        {
          duration: 500,
        },
      );
      return;
    }
  }

  // Add entity to graph
  await addEntityToGraph(entity, true);
}

/**
 * Watch for selected entity changes from parent
 * Clear graph and show single central node with its relationships
 */
watch(
  () => props.selectedEntity,
  async (entity) => {
    if (!entity || !cy) return;

    // Clear the entire graph first
    cy.elements().remove();
    closeNodeDetails();

    // Add new central node and fetch its relationships
    await addEntityToGraph(entity);
  },
  { immediate: true },
);

/**
 * Add entity to graph and optionally fetch relationships
 */
async function addEntityToGraph(entity: Entity, autoExpand = true) {
  if (!cy) return;

  // Add the node
  const nodeData = {
    id: entity.urn,
    label: entity.displayName || entity.id,
    type: entity.type,
    urn: entity.urn,
    displayName: entity.displayName,
    color: getColorForType(entity.type),
    size: getSizeForType(entity.type),
    expanded: false,
  };

  cy.add({
    group: "nodes",
    data: nodeData,
  });

  // Select and center on the new node
  const node = cy.getElementById(entity.urn);
  cy.elements().unselect();
  node.select();

  // Run cose-bilkent layout for better edge lengths
  cy.layout({
    name: "cose-bilkent",
    animate: true,
    animationDuration: 600,
    fit: true,
    padding: 60,
    nodeDimensionsIncludeLabels: true,
    nodeRepulsion: 15000,
    idealEdgeLength: 100,
    edgeElasticity: 0.35,
    nestingFactor: 0.1,
    gravity: 0.15,
    numIter: 5000,
    tile: true,
    tilingPaddingVertical: 25,
    tilingPaddingHorizontal: 25,
    gravityRange: 4.5,
    gravityCompound: 1.0,
    gravityRangeCompound: 2.0,
    randomize: false,
    quality: "proof",
  }).run();

  // Auto-expand if requested
  if (autoExpand) {
    await expandNode(entity.urn);
  }
}

/**
 * Handle double-click on node (expand/collapse)
 */
async function handleNodeDoubleClick(evt: any) {
  const node = evt.target;
  const nodeId = node.id();
  const isExpanded = node.data("expanded");

  if (isExpanded) {
    collapseNode(nodeId);
  } else {
    await expandNode(nodeId);
  }
}

/**
 * Expand node by fetching and adding its relationships
 */
async function expandNode(nodeId: string) {
  if (!cy) return;

  const node = cy.getElementById(nodeId);
  if (node.length === 0) return;

  loading.value = true;

  try {
    // Fetch relationships from API
    const encodedUrn = encodeURIComponent(nodeId);
    const data = await $fetch(`/api/entity/${encodedUrn}/relationships`);

    // Add nodes and edges
    const newElements = [...data.nodes, ...data.edges];

    // Filter out elements that already exist
    const elementsToAdd = newElements.filter((el: any) => {
      return cy!.getElementById(el.data.id).length === 0;
    });

    if (elementsToAdd.length > 0) {
      cy.add(elementsToAdd);

      // Run cose-bilkent layout for better edge lengths
      const layout = cy.layout({
        name: "cose-bilkent",
        animate: true,
        animationDuration: 600,
        fit: false,
        padding: 60,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: 15000,
        idealEdgeLength: 100,
        edgeElasticity: 0.35,
        nestingFactor: 0.1,
        gravity: 0.15,
        numIter: 5000,
        tile: true,
        tilingPaddingVertical: 25,
        tilingPaddingHorizontal: 25,
        gravityRange: 4.5,
        gravityCompound: 1.0,
        gravityRangeCompound: 2.0,
        randomize: false,
        quality: "proof",
      });

      // Wait for layout to complete, then center on the expanded node
      layout.promiseOn("layoutstop").then(() => {
        cy.animate(
          {
            center: { eles: node },
            zoom: cy.zoom(), // Keep current zoom level
          },
          {
            duration: 400,
          },
        );
      });

      layout.run();
    }

    // Mark node as expanded
    node.data("expanded", true);
    node.addClass("expanded");
  } catch (error) {
    console.error("Error expanding node:", error);
  } finally {
    loading.value = false;
  }
}

/**
 * Collapse node by removing its direct neighbors that don't have other connections
 */
function collapseNode(nodeId: string) {
  if (!cy) return;

  const node = cy.getElementById(nodeId);
  if (node.length === 0) return;

  // Get direct neighbors
  const neighbors = node.neighborhood();

  // Remove neighbors that only connect to this node
  neighbors.nodes().forEach((neighbor: any) => {
    const neighborEdges = neighbor.connectedEdges();
    const edgesToNode = neighborEdges.filter((edge: any) => {
      return edge.source().id() === nodeId || edge.target().id() === nodeId;
    });

    // If all edges connect to the collapsed node, remove the neighbor
    if (neighborEdges.length === edgesToNode.length) {
      neighbor.remove();
    }
  });

  // Remove edges connected to removed nodes
  const edgesToRemove = node.connectedEdges().filter((edge: any) => {
    const source = edge.source();
    const target = edge.target();
    return (
      source.removed() ||
      target.removed() ||
      (source.id() === nodeId && !target.hasClass("expanded")) ||
      (target.id() === nodeId && !source.hasClass("expanded"))
    );
  });
  edgesToRemove.remove();

  // Mark node as collapsed
  node.data("expanded", false);
  node.removeClass("expanded");

  // Re-layout with cose-bilkent for better edge lengths
  cy.layout({
    name: "cose-bilkent",
    animate: true,
    animationDuration: 600,
    fit: false,
    padding: 60,
    nodeDimensionsIncludeLabels: true,
    nodeRepulsion: 15000,
    idealEdgeLength: 100,
    edgeElasticity: 0.35,
    nestingFactor: 0.1,
    gravity: 0.15,
    numIter: 5000,
    tile: true,
    tilingPaddingVertical: 25,
    tilingPaddingHorizontal: 25,
    gravityRange: 4.5,
    gravityCompound: 1.0,
    gravityRangeCompound: 2.0,
    randomize: false,
    quality: "proof",
  }).run();
}

/**
 * Reset graph (remove all elements)
 */
function resetGraph() {
  if (!cy) return;
  cy.elements().remove();
  closeNodeDetails();
  updateStats();
}

/**
 * Fit graph to view
 */
function fitToView() {
  if (!cy) return;
  cy.fit(undefined, 50);
}

/**
 * Center on selected/highlighted node
 */
function centerOnSelected() {
  if (!cy) return;

  // Get currently selected nodes in the graph
  const selectedNodes = cy.$("node:selected");

  if (selectedNodes.length > 0) {
    // Center on the first selected node
    cy.animate(
      {
        center: { eles: selectedNodes[0] },
        zoom: 1.5,
      },
      {
        duration: 500,
      },
    );
  } else if (props.selectedEntity) {
    // Fallback to props.selectedEntity if nothing is selected
    const node = cy.getElementById(props.selectedEntity.urn);
    if (node.length > 0) {
      cy.animate(
        {
          center: { eles: node },
          zoom: 1.5,
        },
        {
          duration: 500,
        },
      );
    }
  }
}

/**
 * Zoom in
 */
function zoomIn() {
  if (!cy) return;
  cy.zoom({
    level: cy.zoom() * 1.2,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  });
}

/**
 * Zoom out
 */
function zoomOut() {
  if (!cy) return;
  cy.zoom({
    level: cy.zoom() * 0.8,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  });
}

/**
 * Update node/edge counts
 */
function updateStats() {
  if (!cy) return;
  nodeCount.value = cy.nodes().length;
  edgeCount.value = cy.edges().length;
}

/**
 * Check if a value is a URL
 */
function isUrl(value: any): boolean {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Get color for entity type
 */
function getColorForType(type: string): string {
  const colorMap: Record<string, string> = {
    Application: "#60a5fa",
    Service: "#34d399",
    Endpoint: "#fbbf24",
    Route: "#a78bfa",
    Namespace: "#f472b6",
    User: "#818cf8",
    Role: "#2dd4bf",
    Cluster: "#fb923c",
    ExternalResource: "#22d3ee",
    Alert: "#f87171",
    SLO: "#a3e635",
    JiraProject: "#c084fc",
  };
  return colorMap[type] || "#94a3b8";
}

/**
 * Get size for entity type
 */
function getSizeForType(type: string): number {
  const sizeMap: Record<string, number> = {
    Application: 50,
    Service: 50,
    Endpoint: 40,
    Route: 40,
    Namespace: 35,
    User: 30,
    Role: 30,
  };
  return sizeMap[type] || 35;
}

/**
 * Cleanup on unmount
 */
onUnmounted(() => {
  if (cy) {
    cy.destroy();
  }
});
</script>

<style scoped>
.graph-explorer {
  min-width: 400px;
}

/* Prevent text selection while resizing panel */
body.resizing-panel {
  user-select: none;
  cursor: row-resize !important;
}

body.resizing-panel * {
  cursor: row-resize !important;
}
</style>
