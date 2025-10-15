# Kartograph

Use AI to extract, visualize, and query knowledge graphs.

## Overview

Kartograph provides two main components that work together:

### 1. Extraction → Knowledge Graphs

Transform any structured repository (Kubernetes manifests, Terraform, API specs, Docs, etc.) into queryable knowledge graphs. An AI assistant (like Claude Code) analyzes your repository, identifies entities and relationships, and exports to JSON-LD format compatible with any graph database.

**[→ See Extraction Documentation](./extraction/)**

Key features:

- Repository-agnostic methodology (works with K8s, Terraform, OpenAPI, etc.)
- Automatic relationship resolution and validation
- Export to Dgraph, Neo4j, or any JSON-LD compatible database

### 2. App → Query & Visualize

Web application that lets you explore knowledge graphs using natural language queries powered by Claude. Built with Nuxt 4, Vue 3, and designed for Kubernetes/OpenShift deployment.

**[→ See App Documentation](./app/)**

Key features:

- AI-powered natural language queries via Claude (Vertex AI)
- Interactive graph visualization
- Secure authentication (email/password + GitHub OAuth)
- Conversation history and session management
- MCP server for programmatic access
- Kubernetes-native with ClowdApp support

## Quick Start

### Extract a Knowledge Graph

#### 1. Use Claude Code to extract entities from your repository

Ask Claude to follow the methodology in extraction/PROCESS.md.
Be sure to point it to the repo you wish to extract from in the same
prompt.

Example Prompt:

```
Apply the process detailed in ./extraction/PROCESS.md to the
repo located at /home/my-user/my-repo/
```

#### 2. Load the resulting JSON-LD into your graph database

_This example uses dgraph. There is also a script for loading into a Neo4j database._

```bash
cd extraction
python load_dgraph.py --input ../working/knowledge_graph.jsonld --dgraph-url http://localhost:8080
```

### Deploy the App

```bash
# Local development
cd app
npm install
npm run dev

# OpenShift/Kubernetes
cd app
make deploy-ephemeral-local

# See app/README.md for full deployment options
```

## Use Cases

- **Service Discovery**: "Show me all services owned by the platform team"
- **Dependency Analysis**: "What services depend on the authentication service?"
- **Incident Response**: "What's the blast radius if this database fails?"
- **Compliance Audits**: "Which namespaces don't have resource limits configured?"
- **Capacity Planning**: "How many services are deployed across production clusters?"

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Your Repository (K8s, Terraform, Config Files)      │
└────────────────┬─────────────────────────────────────┘
                 │
                 │ AI Assistant + extraction/PROCESS.md
                 ▼
         ┌────────────────┐
         │   JSON-LD      │
         │ Knowledge Graph│
         └───────┬────────┘
                 │
                 │ extraction/load_*.py
                 ▼
         ┌───────────────┐
         │ Graph Database│
         │ (Dgraph/Neo4j)│
         └───────┬───────┘
                 │
                 │ GraphQL/DQL queries
                 ▼
         ┌───────────────┐
         │  Kartograph   │
         │  Web App      │ ← Users query via natural language
         └───────────────┘
```

## Tech Stack

**Extraction:**

- Python 3.8+ for loaders
- JSON-LD for graph interchange format
- Compatible with Dgraph, Neo4j, and RDF databases

**App:**

- [Nuxt 4](https://nuxt.com/) + Vue 3 + TypeScript
- [Dgraph](https://dgraph.io/) for graph database
- [Better Auth](https://www.better-auth.com/) for authentication
- [Claude](https://claude.ai/) via Vertex AI for natural language queries
- [shadcn-vue](https://www.shadcn-vue.com/) for UI components
- SQLite for user data and sessions

## Development

### Pre-commit Hooks

This repository uses [pre-commit](https://pre-commit.com/) to ensure code quality and security:

```bash
# One-time setup
./setup-pre-commit.sh

# Or manual setup
pip install pre-commit
cd app && npm install && cd ..
pre-commit install

# Run manually
pre-commit run --all-files
```

**What's checked:**

- **Format**: Prettier (TypeScript/Vue), Black (Python), trailing whitespace
- **Lint**: ESLint (TypeScript/Vue), markdownlint, yamllint
- **Type Safety**: TypeScript type checking
- **Security**: Gitleaks (credential scanning), detect-secrets
- **General**: YAML/JSON validity, large file detection, merge conflicts

Hooks run automatically on `git commit`. To skip (not recommended): `git commit --no-verify`

## Contributing

Contributions welcome! Areas for expansion:

- New graph database loaders
- Additional extraction patterns for different repository types
- UI enhancements and visualizations
- Documentation improvements

Please ensure pre-commit hooks pass before submitting PRs.

## License

MIT License - see [LICENSE](./LICENSE)
