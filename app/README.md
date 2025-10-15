# Kartograph App

Web application for querying and visualizing knowledge graphs using natural language, built with Nuxt 4 and integrated with Dgraph.

## Features

- **AI-Powered Queries**: Natural language queries using Claude via Vertex AI
- **Knowledge Graph Visualization**: Interactive graph exploration
- **Conversation History**: Persistent chat sessions with message history
- **MCP Server**: Programmatic access for Claude Code and other MCP clients
- **Authentication**: Better Auth integration with email/password and GitHub OAuth
- **Kubernetes-Native**: ClowdApp-compatible deployment manifests for OpenShift

## Local Development

### Prerequisites

- Node.js 18+ and npm
- Docker (for local Dgraph instance)
- Google Cloud credentials (for Vertex AI access)

### Setup

1. Install dependencies:

```bash
npm install
```

2. Create `.env` file with required configuration:

```bash
cp .env.example .env
```

3. Configure environment variables in `.env`:

```bash
# Dgraph connection
DGRAPH_URL=http://localhost:8080

# Database (SQLite for local dev)
DATABASE_URL=/data/kartograph.db

# Better Auth
BETTER_AUTH_SECRET=your-secret-key-change-in-production
BETTER_AUTH_URL=http://localhost:3000

# GitHub OAuth (optional - enables GitHub sign-in)
GITHUB_CLIENT_ID=your-github-oauth-client-id
GITHUB_CLIENT_SECRET=your-github-oauth-client-secret

# Vertex AI configuration (required for AI queries)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcloud-credentials.json
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_REGION=us-central1
CLAUDE_CODE_USE_VERTEX=1
```

4. Start development server:

```bash
npm run dev
```

Visit <http://localhost:3000>

## Vertex AI Setup

The app uses Claude via Google Cloud's Vertex AI. You'll need:

1. **GCP Project** with Vertex AI API enabled
2. **Service Account** with Vertex AI User role
3. **Credentials JSON** downloaded from GCP

### Getting Credentials

1. Go to [GCP Console](https://console.cloud.google.com)
2. Navigate to IAM & Admin → Service Accounts
3. Create a new service account or select existing one
4. Grant "Vertex AI User" role
5. Create a JSON key and download it
6. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of this JSON file

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account JSON key file
- `VERTEX_PROJECT_ID`: Your GCP project ID
- `VERTEX_REGION`: GCP region (e.g., us-central1, us-east1)
- `CLAUDE_CODE_USE_VERTEX`: Set to `1` to enable Vertex AI

## GitHub OAuth Setup

The app supports GitHub OAuth for single sign-on authentication. This is optional but provides a better user experience.

### Creating a GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** → **New OAuth App**
3. Fill in the application details:
   - **Application name**: Kartograph (or your preferred name)
   - **Homepage URL**: Your application URL (e.g., `http://localhost:3000` for local dev)
   - **Authorization callback URL**: `{YOUR_APP_URL}/api/auth/callback/github`
     - Local: `http://localhost:3000/api/auth/callback/github`
     - Kubernetes: `https://your-route-url.apps.example.com/api/kartograph/api/auth/callback/github`
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it immediately (you won't see it again)

### Local Development

Add to your `.env` file:

```bash
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
```

Restart your development server for changes to take effect.

### Kubernetes Deployment

Set environment variables before deploying:

```bash
export GITHUB_CLIENT_ID=your_github_client_id_here
export GITHUB_CLIENT_SECRET=your_github_client_secret_here

# Deploy (Makefile will create secret automatically)
make deploy-ephemeral-local
```

Or create the secret manually:

```bash
kubectl create secret generic kartograph-github-oauth \
  --from-literal=client-id=your_github_client_id_here \
  --from-literal=client-secret=your_github_client_secret_here
```

### Callback URL Configuration

The callback URL depends on your deployment environment:

| Environment                 | Callback URL Format                                            |
| --------------------------- | -------------------------------------------------------------- |
| Local Development           | `http://localhost:3000/api/auth/callback/github`               |
| Kubernetes (with base path) | `https://{route-host}/api/kartograph/api/auth/callback/github` |
| Kubernetes (root path)      | `https://{route-host}/api/auth/callback/github`                |

**Important**: The callback URL in your GitHub OAuth App must exactly match what Better Auth expects. For Kubernetes deployments with a base path (like `/api/kartograph`), the callback URL includes that base path.

### Verifying GitHub OAuth

After configuration, you should see a "Continue with GitHub" button on the login page. When clicked:

1. User is redirected to GitHub for authorization
2. After approval, GitHub redirects back to your callback URL
3. User is automatically signed in and redirected to the home page

If GitHub OAuth is not configured (missing client ID/secret), the button will still appear but authentication will fail gracefully.

## Kubernetes/OpenShift Deployment

### Prerequisites

- Kubernetes cluster or OpenShift cluster
- kubectl or oc CLI installed and configured
- Docker or Podman for building images
- Optional: Bonfire CLI (for Red Hat internal ephemeral environments)

### Quick Deployment

Deploy to Kubernetes namespace with local image:

```bash
make deploy-ephemeral-local
```

This will:

1. Build container image with your local code
2. Push to OpenShift internal registry (or configure for your registry)
3. Deploy standalone Dgraph instances
4. Deploy app via ClowdApp template
5. Auto-detect route URL and configure authentication

### Deployment Variants

#### Using pre-built images

```bash
make deploy IMAGE_TAG=v1.0.0
```

#### Deploy via Bonfire (Red Hat internal)

```bash
make deploy-ephemeral IMAGE_TAG=latest
```

### Vertex AI Secrets

Before deploying, you must create a secret with your GCP credentials:

```bash
# Create secret from your local credentials file
kubectl create secret generic kartograph-vertex-ai \
  --from-file=credentials.json=/path/to/your/gcloud-credentials.json \
  --from-literal=project-id=your-gcp-project-id \
  --from-literal=region=us-central1
```

Or let the Makefile create it for you:

```bash
# Set environment variables
export VERTEX_CREDENTIALS_FILE=/path/to/gcloud-credentials.json
export VERTEX_PROJECT_ID=your-gcp-project-id
export VERTEX_REGION=us-central1

# Deploy (Makefile will create secret automatically)
make deploy-ephemeral-local
```

### Configuration Parameters

The deployment can be customized via Makefile variables:

```bash
# Image configuration
IMAGE_REGISTRY=quay.io
IMAGE_ORG=your-org
IMAGE_NAME=kartograph-app
IMAGE_TAG=latest

# Vertex AI (required for AI features)
VERTEX_CREDENTIALS_FILE=/path/to/credentials.json
VERTEX_PROJECT_ID=your-project-id
VERTEX_REGION=us-central1

# GitHub OAuth (optional for SSO)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Resource limits
APP_CPU_LIMIT=500m
APP_MEMORY_LIMIT=512Mi
DGRAPH_ALPHA_MEMORY_LIMIT=2Gi
```

### Deployment Architecture

The deployment consists of:

1. **Dgraph Zero** - Cluster coordinator (standalone Deployment)
2. **Dgraph Alpha** - Graph database (standalone Deployment)
3. **App** - Nuxt application with UI and MCP server (ClowdApp deployment)

Dgraph components are deployed as standalone Kubernetes resources to avoid conflicts with service mesh configurations.

### Accessing the Application

After deployment:

```bash
# Get the route URL
kubectl get routes -l app=kartograph  # OpenShift
kubectl get ingress -l app=kartograph # Standard Kubernetes

# View logs
make logs

# Port forward for local access
make port-forward
```

## Available Commands

### Development

- `make dev-setup` - Install dependencies
- `make test-local` - Run development server
- `make lint` - Run linter
- `make format` - Format code

### Deployment

- `make build` - Build container image
- `make push` - Push image to registry
- `make deploy` - Deploy using kubectl/oc apply
- `make deploy-ephemeral-local` - Build and deploy locally

### Management

- `make status` - Show deployment status
- `make logs` - Tail app logs
- `make logs-dgraph` - Tail dgraph-alpha logs
- `make port-forward` - Forward app to localhost:3003
- `make shell` - Open shell in app pod
- `make restart` - Restart all deployments
- `make clean` - Delete deployment

## MCP Server

The app includes an MCP (Model Context Protocol) server that allows Claude Code and other MCP clients to query your knowledge graph programmatically.

### Enabling MCP Access

1. Create an API token in the web UI (Settings → API Tokens)
2. Configure your MCP client with the token and server URL

See the MCP server documentation in `server/lib/mcp/` for more details.

## Architecture

### Technology Stack

- **Frontend**: Nuxt 4, Vue 3, TypeScript, Tailwind CSS, shadcn-vue
- **Backend**: Nuxt server API routes (Nitro)
- **User Database**: SQLite + Drizzle ORM
- **Graph Database**: Dgraph (DQL queries)
- **Authentication**: Better Auth (email/password + GitHub OAuth)
- **AI Integration**: Claude via Vertex AI (Anthropic SDK)
- **Deployment**: Kubernetes/OpenShift with ClowdApp support

### Directory Structure

```
app/
├── components/       # Vue components (shadcn-vue based)
├── composables/      # Vue composables (auto-imported)
├── deploy/          # Kubernetes/OpenShift deployment manifests
├── lib/             # Shared utilities
├── middleware/      # Nuxt middleware (authentication)
├── pages/           # Page routes (file-based routing)
├── server/          # Nuxt server code
│   ├── api/        # API endpoints (file-based routes)
│   ├── db/         # Database schema and migrations (Drizzle)
│   ├── lib/        # Server utilities (auth, dgraph, MCP)
│   └── plugins/    # Nitro plugins (database migrations)
├── stores/          # Pinia state management
└── Makefile        # Deployment automation
```

## Troubleshooting

### Vertex AI Authentication Errors

If you see authentication errors:

1. Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON file
2. Check service account has "Vertex AI User" role
3. Ensure Vertex AI API is enabled in GCP project
4. Verify project ID and region are correct

### Dgraph Connection Errors

If app can't connect to Dgraph:

```bash
# Check dgraph pods
kubectl get pods -l component=dgraph-alpha

# Check dgraph logs
make logs-dgraph

# Verify services have correct ports
kubectl get svc kartograph-dgraph-alpha -o yaml
```

Expected ports:

- dgraph-alpha: 7080 (grpc), 8080 (http), 9080 (grpc-internal)
- dgraph-zero: 5080 (grpc), 6080 (http)

### Better Auth "Invalid Origin" Errors

The deployment automatically configures trusted origins based on the detected route URL.
If you still see errors:

1. Check the route URL matches `BETTER_AUTH_TRUSTED_ORIGINS`:

```bash
kubectl get route -l app=kartograph  # OpenShift
kubectl get deployment kartograph-app -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="BETTER_AUTH_TRUSTED_ORIGINS")].value}'
```

2. Trigger route URL detection:

```bash
make deploy-ephemeral-local
```

## Contributing

See the main [AGENTS.md](../AGENTS.md) file for guidance on working in this codebase.

## License

MIT License - see [LICENSE](../LICENSE)
