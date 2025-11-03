.PHONY: help build-local push-local deploy-ephemeral deploy-stage test-local lint format dev-setup load-data find-free-port

# Local development image (using OpenShift internal registry)
INTERNAL_REGISTRY ?= default-route-openshift-image-registry.apps.crc-eph.r9lp.p1.openshiftapps.com
LOCAL_IMAGE ?= $(INTERNAL_REGISTRY)/$(shell oc project -q 2>/dev/null || echo "default")/kartograph-app
LOCAL_IMAGE_TAG ?= $(APP_VERSION)-$(GIT_COMMIT)

# Version info for Docker builds
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
APP_VERSION ?= $(shell node -p "require('./package.json').version" 2>/dev/null || echo "0.0.0")

# Data loading configuration
DGRAPH_PORT ?= 8080
GRAPH_FILE ?= working/knowledge_graph.jsonld
DROP_ALL ?= false

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build-local: ## Build local container image
	@echo "==> Building image: $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG)"
	@echo "Version: $(APP_VERSION)+$(GIT_COMMIT)"
	docker build \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		--build-arg APP_VERSION=$(APP_VERSION) \
		-t $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG) \
		-f Dockerfile .

push-local: build-local ## Push image to OpenShift internal registry
	@echo "==> Logging into internal registry..."
	@docker login -u $(shell oc whoami) -p $(shell oc whoami -t) $(INTERNAL_REGISTRY)
	@echo "==> Pushing image to OpenShift registry"
	docker push $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG)

deploy-ephemeral: push-local ## Deploy to ephemeral environment
	@echo "==> Deploying to ephemeral environment"
	@if [ -z "$$BETTER_AUTH_SECRET" ]; then \
		echo "ERROR: BETTER_AUTH_SECRET must be set"; \
		echo "If first deployment: export BETTER_AUTH_SECRET=\$$(openssl rand -base64 32)"; \
		echo "Otherwise: Use the same value from previous deployments"; \
		exit 1; \
	fi
	@NAMESPACE=$$(oc project -q); \
	echo "==> Checking for existing ClowdApp deployment..."; \
	if oc get clowdapp kartograph -n $$NAMESPACE &>/dev/null; then \
		echo "==> Found old ClowdApp deployment, removing..."; \
		oc delete clowdapp kartograph -n $$NAMESPACE --wait=false || true; \
		echo "==> Waiting for old deployment to terminate..."; \
		sleep 5; \
	fi; \
	if oc get deployment kartograph-app -n $$NAMESPACE &>/dev/null; then \
		echo "==> Found old deployment with incompatible selector, removing..."; \
		oc delete deployment kartograph-app -n $$NAMESPACE --wait=false || true; \
		sleep 5; \
	fi; \
	cp deploy/overlays/ephemeral/kustomization.yaml.template deploy/overlays/ephemeral/kustomization.yaml && \
	cd deploy/overlays/ephemeral && \
	kustomize edit set image ghcr.io/jsell-rh/kartograph=$(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG) && \
	kustomize edit set namespace $$NAMESPACE && \
	cd ../../.. && \
	./deploy/scripts/create-ephemeral-secrets.sh $$NAMESPACE && \
	echo "==> Creating placeholder patch for initial deployment..."; \
	if [ ! -f deploy/overlays/ephemeral/patch-url.yaml ]; then \
		echo "apiVersion: v1" > deploy/overlays/ephemeral/patch-url.yaml; \
		echo "kind: ConfigMap" >> deploy/overlays/ephemeral/patch-url.yaml; \
		echo "metadata:" >> deploy/overlays/ephemeral/patch-url.yaml; \
		echo "  name: kartograph-config" >> deploy/overlays/ephemeral/patch-url.yaml; \
		echo "data:" >> deploy/overlays/ephemeral/patch-url.yaml; \
		echo "  NUXT_PUBLIC_ORIGIN: \"https://PLACEHOLDER\"" >> deploy/overlays/ephemeral/patch-url.yaml; \
		echo "  BETTER_AUTH_TRUSTED_ORIGINS: \"https://PLACEHOLDER\"" >> deploy/overlays/ephemeral/patch-url.yaml; \
	fi && \
	echo "==> Deploying to ephemeral (includes route creation)..."; \
	kubectl apply -k deploy/overlays/ephemeral --namespace=$$NAMESPACE && \
	echo "==> Detecting route URL and patching configuration..."; \
	./deploy/scripts/generate-ephemeral-patch.sh $$NAMESPACE && \
	kubectl apply -k deploy/overlays/ephemeral --namespace=$$NAMESPACE
	@echo "==> Deployment complete! Route URL detected and patched."

deploy-stage: ## Deploy to stage (for testing - ArgoCD handles production)
	@echo "==> Deploying to stage (for testing only - ArgoCD handles production)"
	kubectl apply -k deploy/overlays/stage

deploy-ephemeral-local: deploy-ephemeral ## Alias for deploy-ephemeral (backward compatibility)

test-local: ## Run local development server
	npm run dev

lint: ## Run linter
	npm run lint

format: ## Format code
	npm run format || npx prettier --write .

# Development setup
dev-setup: ## Setup local development environment
	@echo "Installing dependencies..."
	npm install
	@echo ""
	@echo "Development setup complete!"
	@echo "Run 'make test-local' to start the dev server"

# Helper function to find a free port
find-free-port:
	@PORT=$(DGRAPH_PORT); \
	while ss -tln | grep -q ":$$PORT " ; do \
		echo "Port $$PORT is in use, trying next port..."; \
		PORT=$$((PORT + 1)); \
	done; \
	echo $$PORT

load-data: ## Load graph data into remote dgraph (use GRAPH_FILE=path/to/file.jsonld DROP_ALL=true)
	@echo "This will port-forward dgraph-alpha and load data from $(GRAPH_FILE)"
	@if [ "$(DROP_ALL)" = "true" ]; then \
		echo "⚠️  WARNING: DROP_ALL=true - This will DELETE all existing data in Dgraph!"; \
	fi
	@echo "Make sure the graph data file exists before continuing."
	@echo ""
	@if [ ! -f $(GRAPH_FILE) ]; then \
		echo "ERROR: $(GRAPH_FILE) not found"; \
		echo ""; \
		echo "Available graph files:"; \
		find .. -name "*.jsonld" -type f 2>/dev/null |  head -10; \
		echo ""; \
		echo "Use: make load-data GRAPH_FILE=path/to/file.jsonld"; \
		exit 1; \
	fi
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		POD=$$(oc get pods -l component=dgraph-alpha -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
		ZERO_POD=$$(oc get pods -l component=dgraph-zero -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
		if [ -z "$$POD" ]; then \
			echo "ERROR: No dgraph-alpha pod found"; \
			exit 1; \
		fi; \
		if [ -z "$$ZERO_POD" ]; then \
			echo "ERROR: No dgraph-zero pod found"; \
			exit 1; \
		fi; \
		HTTP_PORT=8081; \
		GRPC_PORT=9080; \
		ZERO_PORT=5080; \
		while ss -tln | grep -qE ":($$HTTP_PORT|$$GRPC_PORT|$$ZERO_PORT) " ; do \
			echo "Port(s) in use: HTTP=$$HTTP_PORT, gRPC=$$GRPC_PORT, Zero=$$ZERO_PORT"; \
			echo "Trying next port set..."; \
			HTTP_PORT=$$((HTTP_PORT + 1)); \
			GRPC_PORT=$$((GRPC_PORT + 1)); \
			ZERO_PORT=$$((ZERO_PORT + 1)); \
		done; \
		echo "Port-forwarding dgraph-alpha: HTTP=$$HTTP_PORT, gRPC=$$GRPC_PORT"; \
		echo "Port-forwarding dgraph-zero: gRPC=$$ZERO_PORT"; \
		PF_LOG=$$(mktemp); \
		(oc port-forward $$POD $$HTTP_PORT:8080 $$GRPC_PORT:9080 >$$PF_LOG 2>&1) & \
		PF_PID=$$!; \
		(oc port-forward $$ZERO_POD $$ZERO_PORT:5080 >>$$PF_LOG 2>&1) & \
		ZERO_PID=$$!; \
		echo "Port-forward PIDs: alpha=$$PF_PID zero=$$ZERO_PID"; \
		sleep 4; \
		if ! kill -0 $$PF_PID 2>/dev/null; then \
			echo "ERROR: Alpha port-forward failed"; \
			cat $$PF_LOG; \
			rm -f $$PF_LOG; \
			kill $$ZERO_PID 2>/dev/null || true; \
			exit 1; \
		fi; \
		rm -f $$PF_LOG; \
		echo ""; \
		echo "Loading data with dgraph live..."; \
		DROP_FLAG=""; \
		if [ "$(DROP_ALL)" = "true" ]; then \
			DROP_FLAG="--drop-all"; \
		fi; \
		cd .. && python extraction/load_dgraph.py --input $(GRAPH_FILE) --dgraph-url http://localhost:$$HTTP_PORT --grpc-port $$GRPC_PORT --zero-port $$ZERO_PORT $$DROP_FLAG; \
		LOAD_EXIT=$$?; \
		if [ $$LOAD_EXIT -ne 0 ]; then \
			echo ""; \
			echo "❌ Data load failed!"; \
			echo ""; \
			echo "💡 Common issues:"; \
			echo "  - Schema conflict: If you see 'Schema change not allowed', the new data has"; \
			echo "    a different schema than existing data. Solutions:"; \
			echo "      1. Drop existing data: make load-data GRAPH_FILE=$(GRAPH_FILE) DROP_ALL=true"; \
			echo "      2. Or manually alter the schema to match"; \
			echo "  - Connection timeout: Dgraph may be slow to respond, try again"; \
			echo "  - Port conflicts: Check that port-forwards are still running"; \
		fi; \
		echo ""; \
		echo "Stopping port-forwards..."; \
		kill $$PF_PID $$ZERO_PID 2>/dev/null || true; \
		wait $$PF_PID $$ZERO_PID 2>/dev/null || true; \
		exit $$LOAD_EXIT; \
	fi
