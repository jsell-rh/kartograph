# Kartograph Deployment

This directory contains deployment manifests for Kartograph using Clowder.
These manifests were originally created to deploy to the Red Hat Rapid Innovation Platform's
ephemeral environment and may not be suitable for direct use against another environment.

## Components

- **App**: Nuxt.js application for querying the knowledge graph (UI + MCP server)
- **Dgraph Zero**: Cluster coordinator for Dgraph
- **Dgraph Alpha**: Graph database instance
- **PostgreSQL**: Managed by Clowder for auth/sessions

## Prerequisites

- `bonfire` CLI installed
- `oc` CLI installed and logged in
- Access to an OpenShift cluster with Clowder operator
- Docker or Podman for building images

## Quick Start (Recommended)

The Makefile provides convenient commands for common deployment workflows.

### ⚠️ Important: Environment Variables

**Before running any `make` commands**, you must export the required environment variables in your shell. These variables need to be in your shell environment, not just in a `.env` file:

```bash
# Required: Vertex AI credentials for Claude
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcloud-credentials.json
export VERTEX_PROJECT_ID=your-gcp-project-id
export VERTEX_REGION=us-central1

# Required: Auth secret (generate a random string)
export BETTER_AUTH_SECRET=$(openssl rand -base64 32)

# (Optional) Configure GitHub OAuth
# export GITHUB_CLIENT_ID=your_client_id
# export GITHUB_CLIENT_SECRET=your_client_secret
```

**Critical**: The Makefile and deployment scripts read these variables from your shell environment at runtime. If they're not exported in your current shell session, deployment will fail.

**Recommended approach**: Create a `setenv.sh` file (don't commit it!) or add these exports to your `~/.bashrc` / `~/.zshrc`:

```bash
# Example setenv.sh
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcloud-credentials.json
export VERTEX_PROJECT_ID=my-gcp-project
export VERTEX_REGION=us-central1
export BETTER_AUTH_SECRET=your-generated-secret

# (Optional) Configure GitHub OAuth
# export GITHUB_CLIENT_ID=your_client_id
# export GITHUB_CLIENT_SECRET=your_client_secret

# Then source it before running make:
# source setenv.sh
# make deploy-ephemeral-local
```

### 1. Reserve an Ephemeral Namespace

```bash
# Reserve a namespace for 96 hours (required for ephemeral deployments)
bonfire namespace reserve --duration "96h"

# Check your reserved namespace
bonfire namespace list --mine
```

### 2. Build and Deploy to Ephemeral Environment

```bash
cd app

# Build local image, push to internal registry, and deploy
make deploy-ephemeral-local
```

This command will:

- Build the Docker image with current git commit and version
- Push to OpenShift internal registry in your namespace
- Process the local `deploy/clowdapp.yaml` template with your namespace's ClowdEnvironment
- Apply all resources (PVCs, secrets, ClowdApp) to your namespace
- Wait for deployment to be ready
- Auto-detect the route URL and update environment variables
- Restart the deployment with correct configuration

**Note**: This uses `oc apply` with your local ClowdApp template, so any changes you make to `deploy/clowdapp.yaml` will be immediately deployed.

### 3. Check Deployment Status

```bash
make status
```

### 4. View Logs

```bash
# App logs
make logs

# Dgraph Alpha logs
make logs-dgraph

# Dgraph Zero logs
make logs-dgraph-zero
```

### 5. Access the Application

```bash
# Port forward to localhost:3003
make port-forward

# Then visit http://localhost:3003
```

### 6. Clean Up

```bash
# Delete the ClowdApp deployment
make clean

# Or delete directly with oc
oc delete clowdapp kartograph

# Release the namespace reservation
make bonfire-clean
```

### 7. Complete Fresh Slate (Delete Everything)

If you need to completely reset and start fresh:

```bash
# Delete the ClowdApp (this will delete all deployments, services, etc.)
oc delete clowdapp kartograph

# Delete PVCs to clear all data
oc delete pvc dgraph-zero-pvc dgraph-alpha-pvc app-pvc

# Optional: Delete secrets
oc delete secret kartograph-secrets

# Now you can redeploy from scratch
make deploy-ephemeral-local
```

**Note**: Deleting the ClowdApp will automatically delete all related resources (deployments, pods, services created by Clowder), but manually created resources like PVCs and the custom Services need to be deleted separately.

## Makefile Targets

Run `make help` to see all available targets:

```
make help              # Show available targets
make build             # Build container image
make build-local       # Build and push to internal registry
make deploy            # Deploy using oc apply (non-ephemeral)
make deploy-ephemeral-local  # Build local + deploy to ephemeral (recommended)
make status            # Show deployment status
make logs              # Tail app logs
make logs-dgraph       # Tail dgraph-alpha logs
make port-forward      # Forward app to localhost:3003
make clean             # Delete deployment
make restart           # Restart all deployments
```

**Key differences**:

- `make deploy-ephemeral-local` - For development in ephemeral namespaces. Uses local ClowdApp template and auto-configures URLs.
- `make deploy` - For deploying to a standard (non-ephemeral) namespace with manual configuration.

## Manual Deployment

If you prefer not to use the Makefile, you can deploy manually.

### Container Registry Configuration

**⚠️ Important**: The examples below use `quay.io/cloudservices` as the container registry. You **must** update this to use a registry you have access to:

- **GitHub Container Registry**: `ghcr.io/YOUR_USERNAME/kartograph-app`
- **Docker Hub**: `docker.io/YOUR_USERNAME/kartograph-app`
- **Quay.io**: `quay.io/YOUR_ORG/kartograph-app`
- **Other registries**: `YOUR_REGISTRY/YOUR_ORG/kartograph-app`

The Makefile variables you need to update are in `app/Makefile`:

```makefile
IMAGE_REGISTRY ?= quay.io          # Change to your registry
IMAGE_ORG ?= cloudservices         # Change to your username/org
IMAGE_NAME ?= kartograph-app       # Can keep this or rename
```

### Build and Push Image

```bash
cd app

# Set your container registry (replace with your own!)
export IMAGE_REGISTRY=ghcr.io
export IMAGE_ORG=YOUR_USERNAME

# Build the image
docker build \
  --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
  --build-arg APP_VERSION=$(node -p "require('./package.json').version") \
  -t ${IMAGE_REGISTRY}/${IMAGE_ORG}/kartograph-app:latest .

# Push to registry (ensure you're logged in first)
docker push ${IMAGE_REGISTRY}/${IMAGE_ORG}/kartograph-app:latest
```

**Authentication**: Ensure you're logged into your container registry before pushing:

```bash
# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Docker Hub
docker login docker.io

# Quay.io
docker login quay.io
```

### Deploy with oc apply

```bash
# Set your container registry variables
export IMAGE_REGISTRY=ghcr.io
export IMAGE_ORG=YOUR_USERNAME
export IMAGE_TAG=latest

# Create namespace
oc new-project kartograph-dev

# Apply PVCs
oc apply -f deploy/dgraph-pvcs.yaml

# Create required secrets
oc create secret generic kartograph-secrets \
  --from-literal=auth-secret=$(openssl rand -base64 32)

# Process and apply the template
# IMPORTANT: Update the IMAGE parameter to use your registry!
oc process -f deploy/clowdapp.yaml \
  -p ENV_NAME=kartograph-dev \
  -p IMAGE=${IMAGE_REGISTRY}/${IMAGE_ORG}/kartograph-app \
  -p IMAGE_TAG=${IMAGE_TAG} \
  -p APP_PUBLIC_URL=https://kartograph.apps.example.com \
  | oc apply -f -
```

## Environment Variables

The app requires these environment variables:

- `DGRAPH_URL`: URL to Dgraph Alpha (default: `http://kartograph-dgraph-alpha:8080`)
- `DATABASE_URL`: SQLite database path (default: `/data/kartograph.db`)
- `BETTER_AUTH_SECRET`: Secret key for auth (from secret)
- `BETTER_AUTH_URL`: Public URL for the app (auto-configured by Makefile)
- `NUXT_PUBLIC_SITE_URL`: Public URL for the app
- `NUXT_APP_BASE_URL`: Base path for Nuxt app (default: `/api/kartograph`)

## Namespace Management

### Reserving a Namespace

Ephemeral namespaces must be reserved before deployment:

```bash
# Reserve for 96 hours
bonfire namespace reserve --duration "96h"

# Check your reservations
bonfire namespace list --mine

# Extend reservation
bonfire namespace extend <namespace-name> --duration "48h"

# Release reservation (cleans up resources)
bonfire namespace release <namespace-name>
```

### Deleting a Deployment

```bash
# Delete just the ClowdApp (keeps namespace)
oc delete clowdapp kartograph -n <namespace-name>

# Delete with Makefile
make clean

# Full cleanup including namespace release
make bonfire-clean
```

## Troubleshooting

### Check Deployment Status

```bash
# Using Makefile
make status

# Or manually
oc get clowdapp kartograph
oc get deployments -l app=kartograph
oc get pods -l app=kartograph
```

### View Logs

```bash
# Using Makefile
make logs          # App
make logs-dgraph   # Dgraph Alpha
make logs-dgraph-zero  # Dgraph Zero

# Or manually
oc logs -l deployment=kartograph-app -f
oc logs -l deployment=kartograph-dgraph-alpha -f
oc logs -l deployment=kartograph-dgraph-zero -f
```

### Common Issues

**Dgraph pods in CrashLoopBackOff**

- Check service names match pod arguments
- Verify ports are correctly configured (5080/6080 for zero, 7080/8080/9080 for alpha)

```bash
oc get svc -l app=kartograph
oc logs -l deployment=kartograph-dgraph-alpha --tail=50
```

**Auth endpoints returning 404**

- Verify BETTER_AUTH_URL includes the full path
- Should be: `https://<route-url>/api/kartograph`

```bash
oc get deployment kartograph-app -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="BETTER_AUTH_URL")].value}'
```

**Can't access application**

- Check route was created
- Verify crcauth whitelist is configured

```bash
oc get route -l app=kartograph
oc get clowdapp kartograph -o yaml | grep -A 5 whitelistPaths
```

**Database errors**

- Verify PVC is bound
- Check SQLite file permissions

```bash
oc get pvc app-pvc
oc exec -it deployment/kartograph-app -- ls -la /data
```
