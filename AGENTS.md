# AGENTS.md - Guide for AI Coding Assistants

This file provides AI coding assistants (Claude Code, GitHub Copilot, etc.) with essential context for working effectively in the Kartograph repository.

## Repository Overview

**Kartograph** is a knowledge graph extraction and visualization platform for Kubernetes environments. It consists of two main components:

1. **Extraction Tools** (`extraction/`) - Python scripts and methodology for creating knowledge graphs from repositories
2. **Web Application** (`app/`) - Nuxt-based platform for querying and visualizing graphs with AI

## Directory Structure

```
kartograph/
├── extraction/           # Knowledge graph extraction tools
│   ├── PROCESS.md       # Complete methodology for extracting graphs
│   ├── load_dgraph.py   # Load JSON-LD into Dgraph
│   └── load_neo4j.py    # Load JSON-LD into Neo4j
│
├── app/                 # Main web application (Nuxt 4 + Vue 3)
│   ├── .specify/        # Spec-kit specifications (intent-driven development)
│   │   ├── memory/     # Project documentation and constitution
│   │   └── specs/      # Feature specifications and implementation plans
│   ├── components/      # Vue components (shadcn-vue based)
│   ├── pages/           # Nuxt pages (file-based routing)
│   ├── server/          # Nuxt server code
│   │   ├── api/        # API routes
│   │   ├── db/         # Database schema (Drizzle ORM + SQLite)
│   │   ├── lib/        # Server utilities (auth, dgraph, MCP)
│   │   └── plugins/    # Nitro plugins (migrations)
│   ├── stores/          # Pinia state management
│   ├── deploy/          # Kubernetes/OpenShift manifests
│   └── Makefile        # Deployment automation
│
├── .github/workflows/   # CI/CD (container builds)
└── README.md            # User-facing documentation
```

## Tech Stack

### Extraction (`extraction/`)

- **Language**: Python 3.8+
- **Format**: JSON-LD for graph interchange
- **Dependencies**: requests, argparse (stdlib)
- **Databases**: Dgraph (primary), Neo4j (supported)

### App (`app/`)

- **Frontend**: Nuxt 4, Vue 3, TypeScript, Tailwind CSS
- **UI Components**: shadcn-vue (Radix Vue primitives)
- **Backend**: Nuxt Server (Nitro)
- **Authentication**: Better Auth (email/password + GitHub OAuth)
- **User Database**: SQLite + Drizzle ORM
- **Graph Database**: Dgraph (DQL queries)
- **AI Integration**: Claude via Vertex AI (Anthropic SDK)
- **MCP Server**: Custom implementation for programmatic access

## Key Concepts

### 1. Knowledge Graph Extraction

The `extraction/PROCESS.md` file contains the complete methodology for AI assistants to extract knowledge graphs from repositories. Key points:

- **Input**: Any structured repository (Kubernetes YAMLs, Terraform, etc.)
- **Process**: AI analyzes structure → identifies entities → extracts relationships → validates → exports JSON-LD
- **Output**: JSON-LD file with `@graph` array of entities
- **URN Pattern**: All entities use URNs like `urn:service:foo`, `urn:namespace:prod`

### 2. App Architecture

The app has three main data stores:

1. **SQLite** (`app/server/db/`) - User auth, sessions, conversations, API tokens
2. **Dgraph** (external) - Knowledge graph data (entities and relationships)
3. **Pinia** (`app/stores/`) - Client-side state (auth, conversations)

### 3. Dgraph Integration

Located in `app/server/lib/dgraph-tools.ts`:

- Uses DQL (Dgraph Query Language), not GraphQL
- All predicates wrapped in angle brackets: `<name>`, `<_type>`
- Reverse edges use `~` prefix: `<~dependsOn>`
- Queries run via HTTP POST to `/query` endpoint

Example query:

```graphql
{
  services(func: eq(<_type>, "Service")) {
    <name>
    <description>
  }
}
```

### 4. AI Query Flow

1. User enters natural language query
2. Frontend sends to `/api/chat`
3. Server uses Claude (Vertex AI) with MCP tools
4. MCP tool `query_dgraph` executes DQL against Dgraph
5. Results streamed back to frontend
6. Conversation saved to SQLite

## Spec-Kit: Intent-Driven Development

Kartograph follows the [spec-kit](https://github.com/github/spec-kit) methodology for feature development. The `.specify/` directory in the app contains specifications that define the "what" before the "how".

### Directory Structure

- **`app/.specify/memory/`** - Project documentation and foundational guidelines
  - `constitution.md` - Project governance principles and coding standards
- **`app/.specify/specs/`** - Feature specifications organized by number
  - `001-feature-name/spec.md` - Detailed specification for a feature
  - `002-another-feature/spec.md` - Another feature specification

### Development Workflow

When implementing new features, follow this process:

1. **Specify** - Define requirements and user stories in a spec file
2. **Plan** - Develop technical implementation strategy
3. **Tasks** - Generate actionable task lists
4. **Implement** - Execute tasks to build the feature

### Creating a New Specification

```bash
# Create a new spec directory
mkdir -p app/.specify/specs/00X-feature-name

# Create the spec file
touch app/.specify/specs/00X-feature-name/spec.md
```

A good specification includes:

- **Problem Statement**: What problem does this solve?
- **User Stories**: Who benefits and how?
- **Requirements**: What must the feature do?
- **Technical Approach**: High-level architecture
- **Success Criteria**: How do we know it works?

### Example Spec Structure

```markdown
# Feature: MCP Server Implementation

## Problem Statement

Users need programmatic access to query the knowledge graph...

## User Stories

- As a developer, I want to query the graph via MCP...

## Requirements

- Implement MCP server following Model Context Protocol spec
- Support query_dgraph tool...

## Technical Approach

- Use @modelcontextprotocol/sdk
- Implement tools in app/server/lib/mcp/...

## Success Criteria

- [ ] MCP server starts successfully
- [ ] Claude Desktop can connect and query
```

### Updating Specifications

Specifications are living documents. Update them as:

- Requirements change
- Implementation reveals new insights
- User feedback comes in

Keep specs in sync with implementation to maintain a single source of truth.

## Common Tasks

### Adding a New API Endpoint

1. Create file in `app/server/api/` (file-based routing)
2. Use `defineEventHandler()` from Nuxt
3. Access auth with `await requireAuth(event)`
4. Return JSON directly or use `sendError()`

Example:

```typescript
// app/server/api/example.get.ts
export default defineEventHandler(async (event) => {
  const user = await requireAuth(event);
  return { message: "Hello", userId: user.id };
});
```

### Adding a Database Table

1. Define schema in `app/server/db/schema.ts` using Drizzle
2. Generate migration: `npx drizzle-kit generate`
3. Migration auto-runs on server start via `app/server/plugins/migrate.ts`

### Adding a Vue Component

1. Create in `app/components/` (auto-imported by Nuxt)
2. Use TypeScript with `<script setup lang="ts">`
3. Follow shadcn-vue patterns for UI components
4. Components in `app/components/ui/` are from shadcn-vue library

### Modifying Dgraph Queries

1. Edit `app/server/lib/dgraph-tools.ts`
2. Remember: all predicates need angle brackets `<predicate>`
3. Use `eq()`, `has()`, `@filter()` for filtering
4. Use `expand(_all_)` carefully (can be slow)

### Deployment Changes

1. Edit `app/deploy/clowdapp.yaml` for OpenShift resources
2. Edit `app/Makefile` for build/deploy automation
3. Secrets managed via OpenShift secrets (not committed)
4. Environment variables use `NUXT_` prefix for runtime config

## Important Conventions

### File Naming

- Vue components: PascalCase (`QueryInput.vue`)
- Pages: kebab-case (`pages/settings.vue`)
- API routes: `[name].[method].ts` (`tokens.get.ts`)
- Utilities: camelCase (`authClient.ts`)

### Code Style

- **TypeScript**: Strict mode enabled
- **Formatting**: Prettier (configured in `app/.prettierrc`)
- **Linting**: ESLint with Nuxt preset
- **Imports**: Auto-imported (composables, components, Vue APIs)

### Database

- **Migrations**: Auto-generated, never edit manually
- **Schema**: Single source of truth in `schema.ts`
- **Queries**: Use Drizzle query builder, avoid raw SQL

### Authentication

- **Session-based**: Better Auth manages sessions
- **Middleware**: `app/middleware/auth.global.ts` protects routes
- **API**: Use `requireAuth()` for protected endpoints
- **OAuth**: GitHub provider configured in `app/server/lib/auth.ts`

## Environment Variables

### Required (Vertex AI)

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
VERTEX_PROJECT_ID=your-gcp-project
VERTEX_REGION=us-central1
```

### Optional (GitHub OAuth)

```bash
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

### Runtime Overrides (Nuxt)

Use `NUXT_` prefix to override at runtime:

- `NUXT_DGRAPH_URL=http://dgraph:8080`
- `NUXT_PUBLIC_SITE_URL=https://example.com`

## Testing

Currently minimal test coverage. When adding tests:

```bash
# Unit tests
npm test

# E2E tests (not yet implemented)
# Would use Playwright or Cypress
```

## Deployment

### Local Development

```bash
cd app
npm install
npm run dev
```

### OpenShift/Kubernetes

```bash
cd app
make deploy-ephemeral-local  # Builds + deploys to current namespace
make port-forward            # Access via localhost:3003
make logs                    # View application logs
```

## Common Issues & Solutions

### "Dgraph connection failed"

- Check `NUXT_DGRAPH_URL` environment variable
- Verify Dgraph pods are running: `oc get pods -l component=dgraph-alpha`
- Port-forward for local testing: `make port-forward-dgraph`

### "Better Auth origin error"

- Ensure `BETTER_AUTH_URL` matches your deployment URL
- Check `BETTER_AUTH_TRUSTED_ORIGINS` includes your domain
- For OpenShift, the Makefile auto-detects and patches these

### "Vertex AI authentication failed"

- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON
- Check service account has "Vertex AI User" role
- Ensure `VERTEX_PROJECT_ID` is correct

### Database migration errors

- Delete `app/server/data.db` and restart (local dev only)
- Check `app/server/db/migrations/` for conflicts
- Re-generate: `npx drizzle-kit generate`

## Git Workflow

- **Branching**: Feature branches from `main`
- **Commits**: Descriptive messages, atomic changes. Use conventional commits.
- **PRs**: GitHub Actions builds container on PR
- **Releases**: Tag with `v*` to trigger versioned build

## Need Help?

1. Check `README.md` for high-level overview
2. Check `extraction/PROCESS.md` for graph extraction methodology
3. Check `app/README.md` for deployment details
4. Check relevant source code - it's well-commented

## Important Notes for AI Assistants

- **Extraction**: You (the AI assistant) are expected to generate extraction scripts following `extraction/PROCESS.md`
- **Branding**: Always use "Kartograph" (with K), not "Cartograph"
- **Database**: Dgraph is NOT GraphQL - it uses DQL with different syntax
- **Security**: Never commit secrets, credentials, or personal data
- **Paths**: Use relative paths or argparse, never hardcode absolute paths
- **Examples**: Use `example.com`, `localhost`, or generic placeholders

---

**Last Updated**: 2025-10-15
**Maintainer**: See repository contributors
