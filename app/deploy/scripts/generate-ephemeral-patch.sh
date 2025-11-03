#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_DIR="$SCRIPT_DIR/../overlays/ephemeral"
NAMESPACE=${1:-$(oc project -q 2>/dev/null || echo "")}

if [ -z "$NAMESPACE" ]; then
  echo "ERROR: Could not detect namespace. Pass as argument or set oc context."
  exit 1
fi

echo "==> Detecting route URL for namespace: $NAMESPACE"
ROUTE_NAME="kartograph"

# Wait for route to exist
for i in {1..30}; do
  if oc get route $ROUTE_NAME -n $NAMESPACE &>/dev/null; then
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Route not found after 60 seconds"
    exit 1
  fi
  echo "Waiting for route to be created... ($i/30)"
  sleep 2
done

# Get route host
ROUTE_HOST=$(oc get route $ROUTE_NAME -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$ROUTE_HOST" ]; then
  echo "ERROR: Could not detect route host. Manual intervention required."
  exit 1
fi

PUBLIC_ORIGIN="https://${ROUTE_HOST}"
echo "==> Detected PUBLIC_ORIGIN: $PUBLIC_ORIGIN"

# Generate patch file
cat > "$OVERLAY_DIR/patch-url.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: kartograph-config
data:
  NUXT_PUBLIC_ORIGIN: "$PUBLIC_ORIGIN"
  BETTER_AUTH_TRUSTED_ORIGINS: "$PUBLIC_ORIGIN"
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: kartograph
spec:
  host: "$ROUTE_HOST"
EOF

echo "==> Generated $OVERLAY_DIR/patch-url.yaml"
