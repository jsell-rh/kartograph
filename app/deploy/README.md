# Kartograph Deployment

Kubernetes deployment manifests using Kustomize.

## Structure

- `base/` - Common resources for all environments
- `overlays/ephemeral/` - Development/testing overlay
- `overlays/stage/` - Staging environment (ArgoCD-managed)
- `scripts/` - Deployment automation scripts

## Prerequisites

### Environment Variables (Ephemeral)

**Required:**

```bash
export BETTER_AUTH_SECRET="your-secret-here"  # MUST persist across deployments! # pragma: allowlist secret
```

**Optional:**

```bash
export VERTEX_CREDENTIALS_FILE="/path/to/credentials.json"
export VERTEX_PROJECT_ID="your-gcp-project"
export VERTEX_REGION="us-east5"
export GITHUB_CLIENT_ID="your-oauth-client-id"  # pragma: allowlist secret
export GITHUB_CLIENT_SECRET="your-oauth-client-secret"  # pragma: allowlist secret  # noqa: E501
export AUTH_PASSWORD_ENABLED="true"  # pragma: allowlist secret
export AUTH_ALLOWED_EMAIL_DOMAINS="example.com,another.com"
export ADMIN_EMAILS="admin@example.com"
```

## Deployment Workflows

### Ephemeral Environment

One-command deployment to your current OpenShift namespace:

```bash
cd app
make deploy-ephemeral
```

This will:

1. Build image from local code
2. Push to OpenShift internal registry
3. Create secrets from environment variables
4. Deploy all resources via kustomize
5. Auto-detect route URL and patch configuration
6. Re-apply with correct URLs

### Stage Environment

ArgoCD manages stage automatically. For manual testing:

```bash
kubectl apply -k deploy/overlays/stage
```

## Secret Management

### Ephemeral

Secrets created from environment variables via `scripts/create-ephemeral-secrets.sh`

**IMPORTANT:** The `BETTER_AUTH_SECRET` is used for JWT signing. If you change it, all existing user sessions will be invalidated. Always use the same value across deployments.

```bash
# First deployment
export BETTER_AUTH_SECRET=$(openssl rand -base64 32)
# Save this value somewhere safe!

# Subsequent deployments
export BETTER_AUTH_SECRET="<same-value-from-first-deployment>"
```

### Stage

Secrets are managed using the **Secrets Store CSI Driver** with HashiCorp Vault provider.

**How it works:**

1. `SecretProviderClass` resources define which secrets to retrieve from Vault
2. CSI volumes mount secrets from Vault at pod startup
3. Secrets are automatically synced to Kubernetes Secret objects for use as environment variables

**Vault paths:**

- `hcm-ai/data/kartograph/stage/better-auth` → `BETTER_AUTH_SECRET`
- `hcm-ai/data/kartograph/stage/github-oidc` → `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
- `hcm-ai/data/kartograph/stage/vertex-ai` → `credentials.json`, `VERTEX_PROJECT_ID`, `VERTEX_REGION`

**Service account:** The pod's service account must be bound to the Vault role `kartograph-stage` with appropriate policies.

See: `overlays/stage/secret-provider-class.yaml`

## Image Tagging

- **Ephemeral**: `{version}-{git-commit}` (e.g., `0.2.5-a92a5b4`)
- **Stage**: Semver tags (e.g., `v0.2.5`) - updated by GitHub Actions

## Environment Variables

All runtime configuration uses `NUXT_*` prefix:

- `NUXT_APP_BASE_URL` - Path prefix (`/api/kartograph/`)
- `NUXT_DGRAPH_URL` - Dgraph connection
- `NUXT_PUBLIC_ORIGIN` - Full origin URL
- `NUXT_BETTER_AUTH_SECRET` - JWT signing key
- `NUXT_VERTEX_PROJECT_ID` - GCP project
- `NUXT_API_TOKEN_RATE_LIMIT` - MCP token rate limit
- `NUXT_AUDIT_LOG_RETENTION_DAYS` - Audit log retention

**Exception:** `GOOGLE_APPLICATION_CREDENTIALS` (unprefixed, for Google SDK)

## Components

### Application (kartograph-app)

- **Image**: `ghcr.io/jsell-rh/kartograph`
- **Port**: 8000
- **Volumes**:
  - `app-pvc` (1Gi) - SQLite database
  - `vertex-ai-credentials` (secret) - GCP credentials
- **Resources**: 100m-500m CPU, 256Mi-512Mi RAM

### Dgraph Zero

- **Image**: `dgraph/dgraph:v23.1.1`
- **Ports**: 5080 (gRPC), 6080 (HTTP)
- **Storage**: emptyDir (ephemeral)
- **Resources**: 100m-500m CPU, 256Mi-512Mi RAM

### Dgraph Alpha

- **Image**: `dgraph/dgraph:v23.1.1`
- **Ports**: 7080 (gRPC), 8080 (HTTP), 9080 (internal)
- **Storage**: `dgraph-alpha-pvc` (50Gi)
- **Resources**: 200m-1000m CPU, 1Gi-2Gi RAM

## Secrets Structure

### kartograph-secrets (required)

```yaml
data:
  auth-secret: <base64-encoded-secret>
```

### kartograph-vertex-ai (optional)

```yaml
data:
  credentials.json: <base64-encoded-gcp-credentials>
  project-id: <base64-encoded-project-id>
  region: <base64-encoded-region>
```

### kartograph-github-oauth (optional)

```yaml
data:
  client-id: <base64-encoded-client-id>
  client-secret: <base64-encoded-client-secret>
```

### kartograph-auth-config (optional)

```yaml
data:
  password-enabled: <base64-encoded-boolean>
  allowed-domains: <base64-encoded-comma-separated-domains>
  admin-emails: <base64-encoded-comma-separated-emails>
```

## Troubleshooting

### Route not detected

If the automatic route detection fails:

```bash
# Manually check the route
oc get route kartograph

# Re-run the patch script
./deploy/scripts/generate-ephemeral-patch.sh
kubectl apply -k deploy/overlays/ephemeral
```

### Secrets not created

Ensure all required environment variables are set:

```bash
# Check required variables
echo $BETTER_AUTH_SECRET

# Check optional variables
echo $VERTEX_CREDENTIALS_FILE
echo $VERTEX_PROJECT_ID
```

### Deployment fails

Check kustomize build output:

```bash
kubectl kustomize deploy/overlays/ephemeral
```

### Pod errors

Check logs:

```bash
# App logs
kubectl logs -l component=app -f

# Dgraph logs
kubectl logs -l component=dgraph-alpha -f
kubectl logs -l component=dgraph-zero -f
```

## Migration from ClowdApp

This deployment replaces the previous ClowdApp-based setup. Key changes:

- **No ClowdApp**: Pure Kubernetes Deployment resources
- **Kustomize**: Overlay-based configuration management
- **Dynamic URLs**: Automatic route detection for ephemeral
- **ArgoCD ready**: Stage overlay designed for GitOps

Legacy manifests have been removed:

- `clowdapp.yaml`
- `dgraph-standalone.yaml`
- `dgraph-services.yaml`
- `dgraph-pvcs.yaml`
