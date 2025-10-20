# Feature: Operational Changelog System

## Problem Statement

Kartograph currently auto-generates changelogs from git commits, which effectively captures code changes like features, bug fixes, and improvements. However, important operational events that don't result in code commits—such as data updates to Dgraph, schema changes, system maintenance, or knowledge graph reloads—are invisible to users.

Users need visibility into all changes that affect their experience, not just code deployments. For example:

- Loading 2,500 new service mappings into the knowledge graph
- Reindexing Dgraph for performance improvements
- Schema updates to support new entity types
- System maintenance windows

These operational changes are currently undocumented, creating a gap between what users experience and what they can see in the changelog.

## User Stories

### As a Kartograph User

- I want to see all updates that affect the system, including data changes and operational events
- I want to distinguish between code releases and operational updates at a glance
- I want to filter the changelog to show only the types of changes I care about
- I want to know when the knowledge graph data was last updated and what was added

### As a Kartograph Administrator

- I want to easily record operational changes without requiring a code commit
- I want to post changelog entries via the admin UI or programmatically via API
- I want to categorize operational updates (data, maintenance, configuration)
- I want to include metadata like affected record counts and data sources
- I want the system to automatically log significant operational events

### As a DevOps Engineer

- I want to automatically post changelog entries after running data load scripts
- I want to programmatically create entries via API after maintenance tasks
- I want to include structured metadata for tracking and reporting

## Requirements

### Functional Requirements

#### 1. Data Model

- **Store operational changelog entries** in SQLite with:
  - Unique ID (UUID)
  - Type: `code`, `data`, `maintenance`, `config`, `system`
  - Title (required, max 255 chars)
  - Description (optional, markdown supported)
  - Timestamp (auto-generated)
  - Author (user ID or "system")
  - Metadata (JSON object for flexible additional data)
  - Pinned flag (for important updates)
  - Visibility: `public` (all users) or `admin` (admin-only)

#### 2. API Endpoints

- `GET /api/changelog` - Fetch unified changelog (git + operational)
  - Query params: `type`, `limit`, `offset`, `since`
  - Returns merged, sorted timeline
- `POST /api/admin/changelog` - Create operational entry (admin only)
- `PATCH /api/admin/changelog/:id` - Update entry (admin only)
- `DELETE /api/admin/changelog/:id` - Delete entry (admin only)

#### 3. Admin Interface

- **Changelog Management Tab** in admin dashboard
  - Create new operational entries
  - Edit/delete existing entries
  - Preview before posting
  - View all operational entries in table format
  - Filter and search capabilities

#### 4. Public Changelog Display (Hybrid Approach)

**A. Enhanced WhatsNewDialog Modal** (existing component)

- Shows recent updates since user's last login
- Includes both:
  - Code changes from current release (from git)
  - Recent operational entries (last 7-14 days)
- Displays in categorized sections (features, improvements, bugs, operational)
- Footer includes "View Full Changelog →" link to dedicated page
- Automatically appears on version change or first login

**B. Dedicated /changelog Page** (new)

- Full browsable history with unified timeline
- Shows all code releases and operational updates
- Visual distinction via badges/icons
- Filtering: Show all, Code only, Data only, Maintenance only, etc.
- Grouping by month/week
- Pagination for large datasets
- Expandable details for longer descriptions
- Deep-linkable for sharing specific updates
- Accessible from Settings menu and modal footer

#### 5. Programmatic Entry Creation

- Script-friendly API endpoint with API token authentication
- Example: After `load_dgraph.py` runs, post an entry
- Include helpers/examples in documentation

### Non-Functional Requirements

#### UI/UX Requirements

- **Consistent with existing design system**:
  - Use existing color palette and design tokens
  - Follow shadcn-vue component patterns
  - Match admin dashboard styling (tabs, cards, tables)
  - Use gradient backgrounds for different entry types
  - Maintain glass-morphism effects where appropriate

- **Beautiful but not over-the-top**:
  - Clean, modern aesthetic
  - Subtle animations and transitions
  - Appropriate use of color to convey meaning
  - Not cluttered or overwhelming
  - Accessible and readable

#### Performance

- Changelog API should respond in <200ms
- Support pagination for large datasets
- Efficient SQL queries with proper indexing

#### Security

- Admin-only access for creation/modification
- Input validation and sanitization
- API token authentication for programmatic access
- Audit logging for all changelog modifications

## Technical Approach

### 1. Database Schema

Add new table `changelog_entries` in `app/server/db/schema.ts`:

```typescript
export const changelogEntries = sqliteTable("changelog_entries", {
  id: text("id").primaryKey().$defaultFn(() => crypto.randomUUID()),
  type: text("type", {
    enum: ["code", "data", "maintenance", "config", "system"]
  }).notNull(),
  title: text("title", { length: 255 }).notNull(),
  description: text("description"), // Markdown supported
  timestamp: integer("timestamp", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  authorId: text("author_id").references(() => users.id, { onDelete: "set null" }),
  authorName: text("author_name"), // Fallback for system/API entries
  metadata: text("metadata", { mode: "json" }).$type<{
    affectedRecords?: number;
    dataSource?: string;
    severity?: "info" | "minor" | "major";
    tags?: string[];
    relatedVersion?: string;
  }>(),
  pinned: integer("pinned", { mode: "boolean" }).notNull().default(false),
  visibility: text("visibility", {
    enum: ["public", "admin"]
  }).notNull().default("public"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

export type ChangelogEntry = typeof changelogEntries.$inferSelect;
export type NewChangelogEntry = typeof changelogEntries.$inferInsert;
```

**Index Strategy**:

- Primary index on `id`
- Index on `timestamp` (DESC) for chronological queries
- Index on `type` for filtering
- Composite index on `visibility` + `timestamp` for public queries

### 2. API Implementation

#### GET /api/changelog.get.ts

```typescript
export default defineEventHandler(async (event) => {
  const query = getQuery(event);
  const { type, limit = 50, offset = 0, since } = query;

  // Fetch operational entries from SQLite
  const operationalEntries = await getOperationalEntries({
    type,
    limit,
    offset,
    since,
    visibility: "public", // Filter based on user role
  });

  // Fetch git releases from GitHub API (cached)
  // For modal: only current version
  // For page: configurable limit
  const gitReleases = await getGitReleases(limit);

  // Merge and sort by timestamp
  const unified = mergeAndSortEntries(operationalEntries, gitReleases);

  return {
    entries: unified,
    total: operationalEntries.total + gitReleases.total,
    hasMore: /* pagination logic */
  };
});
```

#### POST /api/admin/changelog.post.ts

```typescript
export default defineEventHandler(async (event) => {
  const user = await requireAuth(event);
  requireAdmin(user);

  const body = await readBody(event);
  const { type, title, description, metadata, pinned, visibility } = body;

  // Validation
  if (!title || title.length > 255) {
    throw createError({ statusCode: 400, message: "Invalid title" });
  }

  // Create entry
  const entry = await db.insert(changelogEntries).values({
    type,
    title,
    description,
    authorId: user.id,
    authorName: user.name,
    metadata,
    pinned,
    visibility,
  }).returning();

  return entry[0];
});
```

### 3. Admin UI Components

#### AdminChangelogPanel.vue

Location: `app/components/admin/ChangelogPanel.vue`

**Structure**:

- Header with "Create Entry" button
- Filter/search controls
- Table of existing entries
- Inline edit/delete actions
- Create/Edit modal

**Styling** (consistent with existing admin components):

```vue
<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-lg font-semibold text-foreground">Operational Changelog</h2>
      <p class="text-sm text-muted-foreground">
        Manage operational updates and system events
      </p>
    </div>
    <button @click="showCreateModal = true"
      class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
      Create Entry
    </button>
  </div>

  <!-- Stats Cards (optional) -->
  <div class="grid grid-cols-4 gap-4">
    <StatCard title="Total Entries" :value="stats.total" />
    <StatCard title="Data Updates" :value="stats.dataUpdates" />
    <StatCard title="This Month" :value="stats.thisMonth" />
    <StatCard title="Pinned" :value="stats.pinned" />
  </div>

  <!-- Filters -->
  <div class="flex gap-3">
    <Select v-model="filter.type">
      <option value="">All Types</option>
      <option value="data">Data Updates</option>
      <option value="maintenance">Maintenance</option>
      <option value="config">Configuration</option>
      <option value="system">System</option>
    </Select>
    <Input v-model="filter.search" placeholder="Search entries..." />
  </div>

  <!-- Entries Table -->
  <div class="bg-card rounded-lg border border-border overflow-hidden">
    <table class="w-full">
      <thead class="bg-muted/50 border-b border-border">
        <tr>
          <th class="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Type</th>
          <th class="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Title</th>
          <th class="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Author</th>
          <th class="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Date</th>
          <th class="px-4 py-3 text-right text-sm font-medium text-muted-foreground">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in entries" :key="entry.id"
          class="border-b border-border hover:bg-muted/30 transition-colors">
          <td class="px-4 py-3">
            <EntryTypeBadge :type="entry.type" />
          </td>
          <td class="px-4 py-3">
            <div class="flex items-center gap-2">
              <span class="text-sm text-foreground">{{ entry.title }}</span>
              <PinIcon v-if="entry.pinned" class="w-3 h-3 text-primary" />
            </div>
          </td>
          <td class="px-4 py-3 text-sm text-muted-foreground">{{ entry.authorName }}</td>
          <td class="px-4 py-3 text-sm text-muted-foreground">{{ formatDate(entry.timestamp) }}</td>
          <td class="px-4 py-3 text-right">
            <button @click="editEntry(entry)">Edit</button>
            <button @click="deleteEntry(entry)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

#### ChangelogCreateModal.vue

Modal component with form:

- Type selector (dropdown)
- Title input (required)
- Description textarea (markdown)
- Metadata fields (optional, based on type)
- Pinned checkbox
- Visibility selector
- Preview tab

### 4. Public Changelog Components

#### A. Enhanced WhatsNewDialog.vue (Existing Component)

Update existing `components/WhatsNewDialog.vue` to include operational entries:

```vue
<template>
  <Dialog :open="isOpen" @update:open="handleClose">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle class="text-2xl flex items-center gap-2">
          <span class="text-3xl">✨</span>
          What's New in Kartograph
          <span class="text-sm font-normal text-muted-foreground ml-2">v{{ version }}</span>
        </DialogTitle>
        <DialogDescription>
          Here's what's new since your last visit
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
        <!-- Code Changes (existing sections) -->
        <div v-if="features.length > 0"><!-- Features --></div>
        <div v-if="improvements.length > 0"><!-- Improvements --></div>
        <div v-if="bugFixes.length > 0"><!-- Bug Fixes --></div>

        <!-- NEW: Operational Updates -->
        <div v-if="operationalUpdates.length > 0"
          class="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-lg p-4 border border-blue-500/20">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
              <DatabaseIcon class="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 class="text-sm font-semibold text-foreground">Recent Updates</h3>
          </div>
          <ul class="space-y-2.5">
            <li v-for="update in operationalUpdates" :key="update.id"
              class="text-sm text-foreground/90 flex items-start gap-3 pl-2">
              <EntryTypeBadge :type="update.type" size="sm" />
              <span>{{ update.title }}</span>
            </li>
          </ul>
        </div>
      </div>

      <DialogFooter class="flex items-center justify-between">
        <NuxtLink to="/changelog" @click="handleClose"
          class="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
          View Full Changelog
          <ArrowRightIcon class="w-3 h-3" />
        </NuxtLink>
        <button @click="handleClose"
          class="px-4 py-2 text-sm bg-primary hover:bg-primary/90 text-primary-foreground rounded-md">
          Got it!
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
// ... existing code ...

// NEW: Fetch recent operational updates
const operationalUpdates = ref<any[]>([]);

onMounted(async () => {
  // Fetch operational entries from last 14 days
  const response = await $fetch('/api/changelog', {
    query: {
      since: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      limit: 5,
      type: '', // all types
    }
  });
  operationalUpdates.value = response.entries.filter(e => e.type !== 'code');
});
</script>
```

#### B. New Dedicated Changelog Page

**pages/changelog.vue**

**Layout**:

```vue
<template>
  <div class="h-full bg-background flex flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b border-border/40 bg-card/50 backdrop-blur-sm px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-foreground">Changelog</h1>
          <p class="text-sm text-muted-foreground">
            See what's new in Kartograph
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Filter buttons -->
          <button
            v-for="filter in filters"
            :key="filter.id"
            @click="activeFilter = filter.id"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="activeFilter === filter.id
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'"
          >
            {{ filter.label }}
          </button>
        </div>
      </div>
    </header>

    <!-- Timeline -->
    <div class="flex-1 overflow-auto px-6 py-6">
      <div class="max-w-4xl mx-auto space-y-6">
        <!-- Grouped by month -->
        <div v-for="group in groupedEntries" :key="group.month">
          <h2 class="text-lg font-semibold text-foreground mb-4 sticky top-0 bg-background/80 backdrop-blur-sm py-2">
            {{ group.month }}
          </h2>

          <div class="space-y-4">
            <ChangelogEntryCard
              v-for="entry in group.entries"
              :key="entry.id"
              :entry="entry"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

#### ChangelogEntryCard.vue

Different styling based on entry type:

```vue
<template>
  <div class="rounded-lg border transition-all hover:shadow-md" :class="cardClasses">
    <div class="p-4">
      <!-- Header -->
      <div class="flex items-start justify-between mb-3">
        <div class="flex items-center gap-3">
          <EntryTypeBadge :type="entry.type" />
          <span class="text-xs text-muted-foreground">{{ formatDate(entry.timestamp) }}</span>
        </div>
        <PinIcon v-if="entry.pinned" class="w-4 h-4 text-primary" />
      </div>

      <!-- Title -->
      <h3 class="text-base font-semibold text-foreground mb-2">
        {{ entry.title }}
      </h3>

      <!-- Description -->
      <div v-if="entry.description" class="text-sm text-foreground/90 prose prose-sm dark:prose-invert">
        <MarkdownRenderer :content="entry.description" />
      </div>

      <!-- Metadata -->
      <div v-if="entry.metadata" class="mt-3 flex flex-wrap gap-2">
        <MetadataBadge
          v-if="entry.metadata.affectedRecords"
          :label="`${entry.metadata.affectedRecords.toLocaleString()} records`"
        />
        <MetadataBadge
          v-if="entry.metadata.dataSource"
          :label="entry.metadata.dataSource"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
const cardClasses = computed(() => {
  const base = 'border-l-4';
  switch (props.entry.type) {
    case 'code':
      return `${base} border-l-purple-500 bg-purple-500/5 border-purple-500/20`;
    case 'data':
      return `${base} border-l-blue-500 bg-blue-500/5 border-blue-500/20`;
    case 'maintenance':
      return `${base} border-l-orange-500 bg-orange-500/5 border-orange-500/20`;
    case 'config':
      return `${base} border-l-green-500 bg-green-500/5 border-green-500/20`;
    case 'system':
      return `${base} border-l-gray-500 bg-gray-500/5 border-gray-500/20`;
  }
});
</script>
```

### 5. GitHub Release Integration

**Fetch and cache git releases**:

`app/server/lib/github-releases.ts`:

```typescript
export async function fetchGitReleases(limit = 10) {
  // Cache releases for 5 minutes
  const cached = await getCachedReleases();
  if (cached) return cached;

  const owner = 'jsell-rh';
  const repo = 'kartograph';

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/releases?per_page=${limit}`
  );

  const releases = await response.json();

  // Transform to unified format
  const transformed = releases.map(release => ({
    id: `github-${release.id}`,
    type: 'code',
    title: release.name || release.tag_name,
    description: release.body, // Already markdown
    timestamp: new Date(release.published_at),
    authorName: release.author.login,
    metadata: {
      version: release.tag_name,
      githubUrl: release.html_url,
    },
    source: 'github',
  }));

  await cacheReleases(transformed);
  return transformed;
}
```

### 6. Programmatic API Access

**Example: Post entry from Python script**

```python
# extraction/post_changelog.py
import requests
import json

def post_changelog_entry(
    api_url: str,
    api_token: str,
    title: str,
    entry_type: str = "data",
    description: str = None,
    metadata: dict = None
):
    """
    Post an operational changelog entry to Kartograph.

    Args:
        api_url: Base URL of Kartograph API (e.g., https://kartograph.example.com/api)
        api_token: API token with admin privileges
        title: Entry title
        entry_type: One of: data, maintenance, config, system
        description: Optional markdown description
        metadata: Optional metadata dict (affectedRecords, dataSource, etc.)
    """
    endpoint = f"{api_url}/admin/changelog"

    payload = {
        "type": entry_type,
        "title": title,
        "description": description,
        "metadata": metadata or {},
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(endpoint, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()

# Usage in load_dgraph.py
if __name__ == "__main__":
    # ... load data ...
    records_loaded = 2500

    # Post changelog entry
    post_changelog_entry(
        api_url=os.getenv("KARTOGRAPH_API_URL"),
        api_token=os.getenv("KARTOGRAPH_API_TOKEN"),
        title=f"Loaded {records_loaded:,} service mappings from production",
        entry_type="data",
        description="Updated knowledge graph with service entities from prod-cluster-01 scan.",
        metadata={
            "affectedRecords": records_loaded,
            "dataSource": "prod-cluster-01",
            "severity": "info",
        }
    )
```

Update `extraction/load_dgraph.py` to optionally post changelog entry.

### 7. Type Badges and Icons

**EntryTypeBadge.vue** component:

```vue
<template>
  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
    :class="badgeClasses">
    <component :is="icon" class="w-3.5 h-3.5" />
    {{ label }}
  </span>
</template>

<script setup>
const props = defineProps<{ type: string }>();

const config = {
  code: {
    label: 'Release',
    icon: 'RocketIcon',
    classes: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20',
  },
  data: {
    label: 'Data Update',
    icon: 'DatabaseIcon',
    classes: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
  },
  maintenance: {
    label: 'Maintenance',
    icon: 'WrenchIcon',
    classes: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20',
  },
  config: {
    label: 'Configuration',
    icon: 'SettingsIcon',
    classes: 'bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20',
  },
  system: {
    label: 'System',
    icon: 'ServerIcon',
    classes: 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20',
  },
};

const { label, icon, classes } = config[props.type] || config.system;
const badgeClasses = classes;
</script>
```

## UI/UX Design Details

### Color Scheme

- **Code/Releases**: Purple (`purple-500`)
- **Data Updates**: Blue (`blue-500`)
- **Maintenance**: Orange (`orange-500`)
- **Configuration**: Green (`green-500`)
- **System**: Gray (`gray-500`)

### Visual Hierarchy

1. **Pinned entries** appear at top with pin icon
2. **Recent entries** (last 7 days) have subtle highlight
3. **Expandable descriptions** with "Read more" for long content
4. **Metadata badges** use muted colors to not distract

### Responsive Design

- Mobile: Single column, simplified filters
- Tablet: Two-column metadata layout
- Desktop: Full layout with sidebar filters

### Accessibility

- Proper heading hierarchy (h1 > h2 > h3)
- ARIA labels for icons and buttons
- Keyboard navigation support
- Screen reader friendly
- Color + icon redundancy (not just color)

### Interactions

- Smooth transitions (200ms)
- Hover states on all interactive elements
- Loading states with skeleton screens
- Empty states with helpful messaging
- Error states with retry actions

## Success Criteria

### Functional Success

- [ ] Operational changelog entries can be created via admin UI
- [ ] Operational entries can be created via API with token auth
- [ ] Public changelog page displays unified timeline
- [ ] Filtering works correctly (all types + individual)
- [ ] Pagination handles large datasets (100+ entries)
- [ ] GitHub releases are fetched and cached correctly
- [ ] Entry creation/edit includes input validation
- [ ] Markdown rendering works in descriptions
- [ ] Metadata displays correctly based on entry type

### Technical Success

- [ ] Database migrations run successfully
- [ ] API endpoints return in <200ms
- [ ] SQL queries use proper indexes
- [ ] No N+1 query problems
- [ ] API rate limiting prevents abuse
- [ ] Audit logging captures all modifications

### UI/UX Success

- [ ] Design is consistent with existing admin panels
- [ ] Color coding is clear and meaningful
- [ ] Mobile layout is usable and responsive
- [ ] No accessibility violations (WCAG 2.1 AA)
- [ ] Loading states prevent perceived lag
- [ ] Error messages are helpful and actionable

### Integration Success

- [ ] load_dgraph.py can post entries programmatically
- [ ] GitHub releases appear in unified timeline
- [ ] Entry types are visually distinct
- [ ] Admin tab integrates seamlessly
- [ ] WhatsNewDialog can optionally show operational updates

### Documentation Success

- [ ] API documented with examples
- [ ] Python helper script documented
- [ ] Admin UI has tooltips/help text
- [ ] README updated with changelog feature
- [ ] Migration guide for existing deployments

## Future Enhancements (Out of Scope)

- Email notifications for new entries
- RSS feed for changelog
- Changelog entry templates
- Bulk import from CSV
- Version comparison view
- Changelog analytics dashboard
- Scheduled/draft entries
- User subscriptions to specific types
- Webhook notifications for external systems
- Integration with Slack/Discord

## Implementation Phases

### Phase 1: Foundation (Day 1-2)

1. Create database schema and migration
2. Implement core API endpoints (CRUD)
3. Create changelog service for unified data fetching
4. Implement GitHub releases integration with caching

### Phase 2: Admin Interface (Day 3)

5. Create AdminChangelogPanel component
6. Add changelog tab to admin dashboard
7. Implement create/edit/delete functionality
8. Add entry type badges component

### Phase 3: Public Changelog Page (Day 4-5)

9. Create /changelog page route
10. Implement ChangelogEntryCard component
11. Add filtering and pagination
12. Add markdown rendering for descriptions
13. Implement grouping by time period

### Phase 4: Enhanced Modal (Day 6)

14. Update WhatsNewDialog to fetch operational entries
15. Add "Recent Updates" section to modal
16. Add "View Full Changelog" link to footer
17. Test modal with mixed content

### Phase 5: Programmatic Access & Docs (Day 7)

18. Add API token authentication for POST endpoint
19. Create Python helper script for load_dgraph.py
20. Write documentation and examples
21. Integration testing

## Notes

- This spec is a living document and will be updated as implementation progresses
- UI mockups can be refined during implementation
- Performance benchmarks should be measured in production-like environment
- Security review required before deploying programmatic API access
