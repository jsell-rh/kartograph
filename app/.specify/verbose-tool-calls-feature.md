# Verbose Tool Call Display Feature

**Issue:** N/A (Enhancement)
**Status:** Specification
**Priority:** Medium
**Estimated Effort:** 2-3 hours

## Overview

Add a collapsible "verbose mode" to tool call displays in the thinking viewer, allowing power users to inspect the input parameters and output results of each tool execution. This provides transparency into the AI's reasoning process and helps with debugging and understanding query behavior.

## User Stories

### As a power user

- I want to see the exact input parameters sent to each tool
- I want to see the raw output returned by each tool
- I want to quickly copy input/output for debugging or sharing
- I want the verbose details to be hidden by default to avoid clutter
- I want syntax-highlighted JSON for better readability

### As a developer

- I want to debug failed queries by seeing exact tool inputs/outputs
- I want to understand how the AI is constructing DGraph queries
- I want to share tool execution details with team members

### As a casual user

- I don't want to be overwhelmed by technical details
- I want the interface to remain clean and simple by default

## Current State

**ToolCallDisplay.vue** shows:

- Tool name (with icon)
- Description
- Timing (e.g., "1.23s")
- Error message (if failed)

**Missing:**

- Input parameters
- Output results
- Copy functionality
- Syntax highlighting

## Proposed Design

### Visual Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ 🔧 dgraph_query                              1.23s      │ ← Header (always visible)
│                                                         │
│ Querying for all services owned by SRE team           │ ← Description
│                                                         │
│ ▸ Input Parameters                                     │ ← Collapsed by default
│                                                         │
│ ▾ Output (2.4 KB)                              [Copy]  │ ← Expanded, with copy button
│ ┌───────────────────────────────────────────────────┐  │
│ │ {                                                 │  │
│ │   "data": {                                       │  │ ← Syntax highlighted JSON
│ │     "queryService": [                             │  │
│ │       {                                           │  │
│ │         "name": "api-gateway",                    │  │
│ │         "owner": "sre-team"                       │  │
│ │       }                                           │  │
│ │     ]                                             │  │
│ │   }                                               │  │
│ │ }                                                 │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Interaction States

#### Default State (Collapsed)

- Both "Input Parameters" and "Output" sections collapsed
- Chevron icons point right (▸)
- Minimal vertical space usage

#### Input Expanded

- Chevron rotates 90° down (▾)
- JSON content slides in with smooth animation
- Syntax-highlighted with proper indentation
- Copy button appears on hover

#### Output Expanded

- Same behavior as input
- Shows file size in header (e.g., "2.4 KB")
- Truncates very large outputs (>5000 chars) with indicator
- Scrollable if content exceeds max-height

### Color & Styling

**Theme Integration:**

- Follows existing glass-morphism design language
- Uses `bg-muted/30` for code blocks (consistent with existing code blocks)
- Primary color for interactive elements
- Syntax highlighting uses theme-aware colors

**Typography:**

- Monospace font for JSON (`font-mono`)
- 12px font size (`text-xs`) for code
- 14px (`text-sm`) for section headers

**Spacing:**

- Indentation: 24px (`pl-6`) to align with description
- Internal padding: 12px (`p-3`) for code blocks
- Gap between sections: 8px (`space-y-2`)

**Animations:**

- Chevron rotation: 200ms ease
- Content expansion: 300ms ease with slide-down
- Hover effects: 150ms ease

## Technical Implementation

### Phase 1: Backend Data Emission (15 min)

#### File: `app/server/orchestrator/QueryAgent.ts`

**Changes to `executeToolCalls()` method:**

```typescript
// Line ~457-461: Add input to tool_call event
this.emit("tool_call", {
  id: toolCall.id,
  name: toolCall.name,
  description,
  input: toolCall.input, // ✨ ADD
});

// Line ~481-484: Add result to tool_complete event
this.emit("tool_complete", {
  toolId: toolCall.id,
  elapsedMs: toolElapsedMs,
  result: typeof result === "string" ? result : JSON.stringify(result, null, 2), // ✨ ADD
});

// Line ~507-511: Add result to tool_error event for failed attempts
this.emit("tool_complete", {
  toolId: toolCall.id,
  elapsedMs: toolElapsedMs,
  error: true,
  result: undefined, // ✨ ADD (null for errors)
});
```

### Phase 2: Frontend Data Handling (15 min)

#### File: `app/pages/index.vue`

**Update ThinkingStep interface:**

```typescript
interface ThinkingStep {
  type: "thinking" | "tool_call" | "retry";
  content: string;
  metadata?: {
    toolName?: string;
    description?: string;
    timing?: number;
    error?: string;
    input?: any;      // ✨ ADD
    result?: string;  // ✨ ADD
  };
}
```

**Update event handlers:**

```typescript
// Line ~539-549: Capture input
case "tool_call":
  currentThinkingSteps.value.push({
    type: "tool_call",
    content: data.description || "Executing query...",
    metadata: {
      toolName: data.name,
      description: data.description,
      input: data.input, // ✨ ADD
    },
  });
  break;

// Line ~551-564: Capture result
case "tool_complete":
  if (currentThinkingSteps.value.length > 0) {
    const lastIndex = currentThinkingSteps.value.length - 1;
    const lastStep = currentThinkingSteps.value[lastIndex];
    if (lastStep.type === "tool_call") {
      lastStep.metadata = {
        ...lastStep.metadata,
        timing: data.elapsedMs,
        result: data.result, // ✨ ADD
      };
    }
  }
  break;
```

### Phase 3: ToolCallDisplay Enhancement (1.5-2 hours)

#### File: `app/components/ToolCallDisplay.vue`

**New Props:**

```typescript
interface Props {
  toolName: string;
  description: string;
  error?: string;
  timing?: string;
  input?: any;      // ✨ NEW
  result?: string;  // ✨ NEW
}
```

**New Template Structure:**

```vue
<template>
  <div class="tool-call-display space-y-2">
    <!-- Existing header (tool name + timing) -->
    <div class="flex items-center gap-2 text-muted-foreground">
      <!-- ... existing content ... -->
    </div>

    <!-- Existing description -->
    <div class="text-sm text-muted-foreground/80 pl-6">
      {{ description }}
    </div>

    <!-- ✨ NEW: Input Parameters Section -->
    <div v-if="input" class="pl-6">
      <button
        @click="toggleInput"
        class="group flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-1"
      >
        <svg
          class="w-3 h-3 transition-transform duration-200"
          :class="{ 'rotate-90': showInput }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span>Input Parameters</span>
      </button>

      <Transition name="expand-code">
        <div v-if="showInput" class="mt-2 relative group/code">
          <!-- Copy button -->
          <button
            @click="copyToClipboard(formattedInput, 'input')"
            class="absolute top-2 right-2 p-1.5 rounded bg-background/80 hover:bg-background border border-border/50 opacity-0 group-hover/code:opacity-100 transition-opacity"
            :title="copiedInput ? 'Copied!' : 'Copy input'"
          >
            <svg
              v-if="copiedInput"
              class="w-3.5 h-3.5 text-green-500"
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
            <svg
              v-else
              class="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          </button>

          <!-- Syntax-highlighted code -->
          <div
            class="rounded-lg bg-muted/30 backdrop-blur-sm border border-border/40 p-3 font-mono text-xs overflow-x-auto max-h-64 overflow-y-auto"
          >
            <pre v-html="highlightedInput"></pre>
          </div>
        </div>
      </Transition>
    </div>

    <!-- ✨ NEW: Output Section -->
    <div v-if="result" class="pl-6">
      <button
        @click="toggleOutput"
        class="group flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-1"
      >
        <svg
          class="w-3 h-3 transition-transform duration-200"
          :class="{ 'rotate-90': showOutput }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span>Output</span>
        <span class="text-[10px] text-primary/70 bg-primary/10 px-1.5 py-0.5 rounded-full font-normal">
          {{ formatSize(result) }}
        </span>
      </button>

      <Transition name="expand-code">
        <div v-if="showOutput" class="mt-2 relative group/code">
          <!-- Copy button -->
          <button
            @click="copyToClipboard(result, 'output')"
            class="absolute top-2 right-2 p-1.5 rounded bg-background/80 hover:bg-background border border-border/50 opacity-0 group-hover/code:opacity-100 transition-opacity z-10"
            :title="copiedOutput ? 'Copied!' : 'Copy output'"
          >
            <svg
              v-if="copiedOutput"
              class="w-3.5 h-3.5 text-green-500"
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
            <svg
              v-else
              class="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          </button>

          <!-- Syntax-highlighted code with truncation -->
          <div
            class="rounded-lg bg-muted/30 backdrop-blur-sm border border-border/40 p-3 font-mono text-xs overflow-x-auto max-h-80 overflow-y-auto"
          >
            <pre v-html="highlightedOutput"></pre>
            <div
              v-if="isTruncated"
              class="mt-3 pt-3 border-t border-border/30 text-center text-muted-foreground italic"
            >
              ... output truncated (showing first {{ maxOutputLength.toLocaleString() }} characters)
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Existing error display -->
    <div v-if="error" class="text-sm text-destructive pl-6 flex items-center gap-2">
      <!-- ... existing error content ... -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { codeToHtml } from 'shiki';

interface Props {
  toolName: string;
  description: string;
  error?: string;
  timing?: string;
  input?: any;
  result?: string;
}

const props = defineProps<Props>();

// State
const showInput = ref(false);
const showOutput = ref(false);
const copiedInput = ref(false);
const copiedOutput = ref(false);
const maxOutputLength = 5000;

// Computed
const formattedInput = computed(() => {
  if (!props.input) return '';
  try {
    return JSON.stringify(props.input, null, 2);
  } catch {
    return String(props.input);
  }
});

const isTruncated = computed(() => {
  return props.result && props.result.length > maxOutputLength;
});

const truncatedResult = computed(() => {
  if (!props.result) return '';
  if (props.result.length <= maxOutputLength) return props.result;
  return props.result.substring(0, maxOutputLength);
});

const highlightedInput = ref('');
const highlightedOutput = ref('');

// Syntax highlighting using shiki
async function highlightCode(code: string, language: string = 'json'): Promise<string> {
  try {
    return await codeToHtml(code, {
      lang: language,
      theme: 'github-dark-dimmed', // Use dark theme (we can make this theme-aware)
    });
  } catch (e) {
    // Fallback to plain text if highlighting fails
    return `<code>${escapeHtml(code)}</code>`;
  }
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Watch for input changes and highlight
watch(() => props.input, async (newInput) => {
  if (newInput) {
    highlightedInput.value = await highlightCode(formattedInput.value);
  }
}, { immediate: true });

// Watch for result changes and highlight
watch(() => props.result, async (newResult) => {
  if (newResult) {
    // Try to detect if it's JSON and highlight accordingly
    const isJson = newResult.trim().startsWith('{') || newResult.trim().startsWith('[');
    highlightedOutput.value = await highlightCode(
      truncatedResult.value,
      isJson ? 'json' : 'text'
    );
  }
}, { immediate: true });

// Methods
function toggleInput() {
  showInput.value = !showInput.value;
}

function toggleOutput() {
  showOutput.value = !showOutput.value;
}

async function copyToClipboard(text: string, type: 'input' | 'output') {
  try {
    await navigator.clipboard.writeText(text);
    if (type === 'input') {
      copiedInput.value = true;
      setTimeout(() => (copiedInput.value = false), 2000);
    } else {
      copiedOutput.value = true;
      setTimeout(() => (copiedOutput.value = false), 2000);
    }
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

function formatSize(text: string): string {
  const len = text.length;
  if (len < 1024) return `${len} chars`;
  if (len < 1024 * 1024) return `${(len / 1024).toFixed(1)} KB`;
  return `${(len / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<style scoped>
/* Expand/collapse animation for code blocks */
.expand-code-enter-active,
.expand-code-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-code-enter-from,
.expand-code-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}

.expand-code-enter-to,
.expand-code-leave-from {
  opacity: 1;
  max-height: 500px;
  margin-top: 0.5rem;
}

/* Syntax highlighting overrides for theme consistency */
:deep(pre) {
  margin: 0;
  padding: 0;
  background: transparent !important;
}

:deep(code) {
  background: transparent !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  line-height: 1.5;
}

/* Custom scrollbar for code blocks */
:deep(.overflow-x-auto)::-webkit-scrollbar {
  height: 8px;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-track {
  background: transparent;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 4px;
}

:deep(.overflow-x-auto)::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}
</style>
```

### Phase 4: Integration with ThinkingViewer (10 min)

#### File: `app/components/ThinkingViewer.vue`

**Update ToolCallDisplay usage (line ~123-133):**

```vue
<ToolCallDisplay
  v-if="step.type === 'tool_call'"
  :tool-name="step.metadata?.toolName || 'Tool'"
  :description="step.content"
  :error="step.metadata?.error"
  :timing="
    step.metadata?.timing
      ? `${(step.metadata.timing / 1000).toFixed(2)}s`
      : undefined
  "
  :input="step.metadata?.input"   <!-- ✨ ADD -->
  :result="step.metadata?.result" <!-- ✨ ADD -->
/>
```

## Dependencies

### New Package: shiki

```bash
npm install shiki
```

**Why shiki?**

- Zero-runtime overhead (pre-renders HTML)
- Theme-aware (supports dark/light modes)
- Better quality than Prism.js
- No global CSS pollution
- 100+ language support
- Used by VS Code

**Alternative:** Could use `highlight.js` or `prism.js`, but shiki provides better TypeScript support and theme integration.

## Design Specifications

### Accessibility

- **Keyboard Navigation:**
  - Tab to focus collapse/expand buttons
  - Enter/Space to toggle
  - Arrow keys to navigate between sections

- **Screen Readers:**
  - Aria labels on all interactive elements
  - Announce state changes (expanded/collapsed)
  - Semantic HTML structure

- **Focus Indicators:**
  - Clear focus rings on interactive elements
  - High contrast for visibility

### Responsive Behavior

- **Mobile (<640px):**
  - Reduce horizontal padding
  - Smaller font sizes (11px for code)
  - Max height 200px for code blocks

- **Tablet (640px-1024px):**
  - Standard styling
  - Max height 256px

- **Desktop (>1024px):**
  - Full styling
  - Max height 320px
  - Wider code blocks

### Performance Considerations

- **Lazy Highlighting:**
  - Only highlight when section is expanded
  - Cache highlighted HTML
  - Debounce re-highlighting

- **Large Outputs:**
  - Truncate at 5000 chars
  - Virtual scrolling for very long results (future enhancement)
  - Show truncation indicator

- **Memory:**
  - Clean up highlighted HTML when component unmounts
  - Don't store full output in multiple places

## Success Criteria

### Functional Requirements

- ✅ Input parameters display correctly for all tool types
- ✅ Output results display correctly (JSON and plain text)
- ✅ Sections collapsed by default
- ✅ Smooth expand/collapse animations
- ✅ Copy buttons work reliably
- ✅ Syntax highlighting renders correctly
- ✅ Large outputs truncated appropriately
- ✅ No performance degradation with multiple tool calls

### UX Requirements

- ✅ Beautiful, polished design matching existing UI
- ✅ Intuitive interaction (clear affordances)
- ✅ Fast and responsive (no lag on expand/collapse)
- ✅ Accessible (keyboard + screen reader friendly)
- ✅ Mobile-friendly

### Visual Requirements

- ✅ Consistent with glass-morphism design language
- ✅ Proper theme integration (dark/light mode)
- ✅ Clear visual hierarchy
- ✅ Subtle hover effects
- ✅ Professional syntax highlighting

## Testing Plan

### Manual Testing

1. **Basic Functionality:**
   - Expand/collapse input section
   - Expand/collapse output section
   - Copy input to clipboard
   - Copy output to clipboard

2. **Edge Cases:**
   - Tool with no input (should not show section)
   - Tool with no output (should not show section)
   - Very large JSON objects (>1MB)
   - Malformed JSON
   - Non-JSON text output

3. **Visual Testing:**
   - Test in dark mode
   - Test in light mode (if implemented)
   - Test on mobile viewport
   - Test with multiple tool calls expanded simultaneously

4. **Accessibility:**
   - Tab through all interactive elements
   - Test with screen reader
   - Test keyboard shortcuts

### Integration Testing

- Query with multiple tool calls
- Failed tool calls (with errors)
- Tool calls with different input types
- Reload conversation and verify tool details persist

## Future Enhancements (Out of Scope)

- **Search within results** - Find text in large outputs
- **Export tool calls** - Download as JSON file
- **Compare tool calls** - Diff two similar executions
- **Permalink to tool call** - Share specific tool execution
- **Performance metrics** - Token usage, cache hits, etc.
- **Retry tool call** - Re-execute with modified input

## Implementation Checklist

### Backend

- [ ] Update QueryAgent to emit input in tool_call event
- [ ] Update QueryAgent to emit result in tool_complete event
- [ ] Test SSE events include new fields

### Frontend - Data Layer

- [ ] Update ThinkingStep interface to include input/result
- [ ] Update tool_call event handler to capture input
- [ ] Update tool_complete event handler to capture result
- [ ] Verify data flow from backend to component

### Frontend - UI Component

- [ ] Install shiki package
- [ ] Create collapsible input section
- [ ] Create collapsible output section
- [ ] Implement copy to clipboard for input
- [ ] Implement copy to clipboard for output
- [ ] Add syntax highlighting for JSON
- [ ] Add file size display
- [ ] Add truncation logic for large outputs
- [ ] Add expand/collapse animations
- [ ] Style copy buttons with hover effects
- [ ] Add responsive styles for mobile

### Frontend - Integration

- [ ] Update ThinkingViewer to pass input/result props
- [ ] Update ResponseDisplay if needed
- [ ] Test with live queries

### Testing & Polish

- [ ] Manual testing of all functionality
- [ ] Test edge cases (large outputs, errors, etc.)
- [ ] Test accessibility (keyboard, screen reader)
- [ ] Test responsive design on mobile
- [ ] Verify theme consistency
- [ ] Performance testing with many tool calls

### Documentation

- [ ] Update component documentation
- [ ] Add usage examples
- [ ] Document keyboard shortcuts

## Notes

- Keep backward compatibility - old tool calls without input/result should still display
- Consider adding a user preference to auto-expand verbose mode
- May want to persist expanded/collapsed state in localStorage
- Consider adding tooltips explaining what input/output represent
