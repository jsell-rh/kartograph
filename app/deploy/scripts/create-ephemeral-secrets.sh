#!/bin/bash
set -e

NAMESPACE=${1:-$(oc project -q 2>/dev/null || echo "")}

if [ -z "$NAMESPACE" ]; then
  echo "ERROR: Could not detect namespace"
  exit 1
fi

echo "==> Creating secrets in namespace: $NAMESPACE"

# kartograph-secrets (REQUIRED - must be from env)
if [ -z "$BETTER_AUTH_SECRET" ]; then
  echo "ERROR: BETTER_AUTH_SECRET environment variable is required"
  echo ""
  echo "This secret is used for JWT signing and must persist across deployments."
  echo "Generate one with: export BETTER_AUTH_SECRET=\$(openssl rand -base64 32)"
  echo ""
  echo "IMPORTANT: Save this value! Changing it will invalidate all existing sessions."
  exit 1
fi

echo "Creating kartograph-secrets..."
oc create secret generic kartograph-secrets \
  --namespace="$NAMESPACE" \
  --from-literal=auth-secret="$BETTER_AUTH_SECRET" \
  --dry-run=client -o yaml | oc apply -f -

# kartograph-vertex-ai (optional)
if [ -n "$VERTEX_CREDENTIALS_FILE" ] && [ -f "$VERTEX_CREDENTIALS_FILE" ]; then
  echo "Creating kartograph-vertex-ai..."
  oc create secret generic kartograph-vertex-ai \
    --namespace="$NAMESPACE" \
    --from-file=credentials.json="$VERTEX_CREDENTIALS_FILE" \
    --from-literal=project-id="${VERTEX_PROJECT_ID:-}" \
    --from-literal=region="${VERTEX_REGION:-us-east5}" \
    --dry-run=client -o yaml | oc apply -f -
else
  echo "Skipping kartograph-vertex-ai (VERTEX_CREDENTIALS_FILE not set)"
fi

# kartograph-github-oauth (optional)
if [ -n "$GITHUB_CLIENT_ID" ]; then
  echo "Creating kartograph-github-oauth..."
  oc create secret generic kartograph-github-oauth \
    --namespace="$NAMESPACE" \
    --from-literal=client-id="$GITHUB_CLIENT_ID" \
    --from-literal=client-secret="$GITHUB_CLIENT_SECRET" \
    --dry-run=client -o yaml | oc apply -f -
else
  echo "Skipping kartograph-github-oauth (GITHUB_CLIENT_ID not set)"
fi

echo "==> All secrets created successfully"
