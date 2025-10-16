.PHONY: help build push deploy deploy-ephemeral clean logs port-forward test

# Default values
IMAGE_REGISTRY ?= quay.io
IMAGE_ORG ?= cloudservices
IMAGE_NAME ?= kartograph-app
IMAGE_TAG ?= latest
IMAGE ?= $(IMAGE_REGISTRY)/$(IMAGE_ORG)/$(IMAGE_NAME)

# Local development image (using OpenShift internal registry)
INTERNAL_REGISTRY ?= default-route-openshift-image-registry.apps.crc-eph.r9lp.p1.openshiftapps.com
LOCAL_IMAGE ?= $(INTERNAL_REGISTRY)/$(BONFIRE_NAMESPACE)/kartograph-app
LOCAL_IMAGE_TAG ?= $(APP_VERSION)-$(GIT_COMMIT)

# Deployment values
ENV_NAME ?= ephemeral
NAMESPACE ?= $(shell oc project -q 2>/dev/null || echo "kartograph-dev")
BONFIRE_NAMESPACE ?= $(shell bonfire namespace list --mine 2>/dev/null | awk 'NR==3 {print $$1}' || echo "$(shell whoami)-kartograph")

# ClowdApp parameters
APP_PUBLIC_URL ?= https://cloud.redhat.com
GITHUB_URL ?=

# Vertex AI configuration (optional - can be set via environment or command line)
VERTEX_CREDENTIALS_FILE ?= $(GOOGLE_APPLICATION_CREDENTIALS)
VERTEX_PROJECT_ID ?=
VERTEX_REGION ?= us-central1

# GitHub OAuth configuration (optional - can be set via environment or command line)
GITHUB_CLIENT_ID ?=
GITHUB_CLIENT_SECRET ?=

# Authentication configuration (optional - can be set via environment or command line)
AUTH_PASSWORD_ENABLED ?= true
AUTH_ALLOWED_EMAIL_DOMAINS ?=

# Version info for Docker builds
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
APP_VERSION ?= $(shell node -p "require('./package.json').version" 2>/dev/null || echo "0.0.0")

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the container image
	@echo "Building image: $(IMAGE):$(IMAGE_TAG)"
	@echo "Version: $(APP_VERSION)+$(GIT_COMMIT)"
	docker build \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		--build-arg APP_VERSION=$(APP_VERSION) \
		-t $(IMAGE):$(IMAGE_TAG) .

build-local: ## Build and push to internal registry
	@echo "Building image: $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG)"
	@echo "Version: $(APP_VERSION)+$(GIT_COMMIT)"
	docker build \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		--build-arg APP_VERSION=$(APP_VERSION) \
		-t $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG) .
	@echo "Logging into internal registry..."
	@docker login -u $(shell oc whoami) -p $(shell oc whoami -t) $(INTERNAL_REGISTRY)
	@echo "Pushing to internal registry..."
	docker push $(LOCAL_IMAGE):$(LOCAL_IMAGE_TAG)

push: ## Push the container image to registry
	@echo "Pushing image: $(IMAGE):$(IMAGE_TAG)"
	docker push $(IMAGE):$(IMAGE_TAG)

build-push: build push ## Build and push the container image

deploy: ## Deploy using oc apply (requires IMAGE_TAG)
	@echo "Deploying to namespace: $(NAMESPACE)"
	@echo "Using image: $(IMAGE):$(IMAGE_TAG)"
	oc apply -f deploy/dgraph-pvcs.yaml
	@echo "Creating kartograph-secrets if it doesn't exist..."
	@oc create secret generic kartograph-secrets \
		--from-literal=auth-secret=$$(openssl rand -base64 32) \
		--dry-run=client -o yaml | oc apply -f -
	@echo "Creating Vertex AI secrets if credentials provided..."
	@if [ -n "$(VERTEX_CREDENTIALS_FILE)" ] && [ -f "$(VERTEX_CREDENTIALS_FILE)" ]; then \
		echo "Found Vertex AI credentials file: $(VERTEX_CREDENTIALS_FILE)"; \
		if [ -z "$(VERTEX_PROJECT_ID)" ]; then \
			echo "ERROR: VERTEX_PROJECT_ID is required when VERTEX_CREDENTIALS_FILE is provided"; \
			exit 1; \
		fi; \
		oc create secret generic kartograph-vertex-ai \
			--from-file=credentials.json=$(VERTEX_CREDENTIALS_FILE) \
			--from-literal=project-id=$(VERTEX_PROJECT_ID) \
			--from-literal=region=$(VERTEX_REGION) \
			--dry-run=client -o yaml | oc apply -f -; \
		echo "Vertex AI secret created/updated"; \
	else \
		echo "No Vertex AI credentials file provided (VERTEX_CREDENTIALS_FILE is empty or file not found)"; \
		echo "AI query features will not be available. Set VERTEX_CREDENTIALS_FILE to enable."; \
	fi
	@echo "Creating GitHub OAuth secrets if credentials provided..."
	@if [ -n "$(GITHUB_CLIENT_ID)" ] && [ -n "$(GITHUB_CLIENT_SECRET)" ]; then \
		echo "Found GitHub OAuth credentials"; \
		oc create secret generic kartograph-github-oauth \
			--from-literal=client-id=$(GITHUB_CLIENT_ID) \
			--from-literal=client-secret=$(GITHUB_CLIENT_SECRET) \
			--dry-run=client -o yaml | oc apply -f -; \
		echo "GitHub OAuth secret created/updated"; \
	else \
		echo "No GitHub OAuth credentials provided (GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET is empty)"; \
		echo "GitHub SSO will not be available. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to enable."; \
	fi
	@echo "Creating authentication configuration secret..."
	@oc create secret generic kartograph-auth-config \
		--from-literal=password-enabled=$(AUTH_PASSWORD_ENABLED) \
		--from-literal=allowed-domains=$(AUTH_ALLOWED_EMAIL_DOMAINS) \
		--dry-run=client -o yaml | oc apply -f -
	@echo "Auth config: PASSWORD_ENABLED=$(AUTH_PASSWORD_ENABLED), ALLOWED_DOMAINS=$(AUTH_ALLOWED_EMAIL_DOMAINS)"
	oc process -f deploy/clowdapp.yaml \
		-p ENV_NAME=$(ENV_NAME) \
		-p IMAGE=$(IMAGE) \
		-p IMAGE_TAG=$(IMAGE_TAG) \
		-p APP_PUBLIC_URL=$(APP_PUBLIC_URL) \
		-p GITHUB_URL=$(GITHUB_URL) \
		| oc apply -f -
	@echo ""
	@echo "Deployment complete! Waiting for rollout..."
	oc rollout status deployment/kartograph-app --timeout=5m || true

deploy-ephemeral: ## Deploy to ephemeral namespace using bonfire
	@echo "Deploying to ephemeral namespace: $(BONFIRE_NAMESPACE)"
	bonfire deploy kartograph \
		--namespace $(BONFIRE_NAMESPACE) \
		--source=appsre \
		--ref-env insights-stage \
		--set-image-tag $(IMAGE)=$(IMAGE_TAG) \
		--set-parameter kartograph/APP_PUBLIC_URL=$(APP_PUBLIC_URL)

deploy-ephemeral-local: build-local ## Build and deploy locally to ephemeral namespace
	@echo "Deploying to ephemeral namespace: $(BONFIRE_NAMESPACE) with local image"
	@echo "Switching to namespace..."
	oc project $(BONFIRE_NAMESPACE)
	@echo "Applying PVCs..."
	oc apply -f deploy/dgraph-pvcs.yaml
	@echo "Creating kartograph-secrets if it doesn't exist..."
	@oc create secret generic kartograph-secrets \
		--from-literal=auth-secret=$$(openssl rand -base64 32) \
		--dry-run=client -o yaml | oc apply -f -
	@echo "Creating Vertex AI secrets if credentials provided..."
	@if [ -n "$(VERTEX_CREDENTIALS_FILE)" ] && [ -f "$(VERTEX_CREDENTIALS_FILE)" ]; then \
		echo "Found Vertex AI credentials file: $(VERTEX_CREDENTIALS_FILE)"; \
		if [ -z "$(VERTEX_PROJECT_ID)" ]; then \
			echo "ERROR: VERTEX_PROJECT_ID is required when VERTEX_CREDENTIALS_FILE is provided"; \
			exit 1; \
		fi; \
		oc create secret generic kartograph-vertex-ai \
			--from-file=credentials.json=$(VERTEX_CREDENTIALS_FILE) \
			--from-literal=project-id=$(VERTEX_PROJECT_ID) \
			--from-literal=region=$(VERTEX_REGION) \
			--dry-run=client -o yaml | oc apply -f -; \
		echo "Vertex AI secret created/updated"; \
	else \
		echo "No Vertex AI credentials file provided (VERTEX_CREDENTIALS_FILE is empty or file not found)"; \
		echo "AI query features will not be available. Set VERTEX_CREDENTIALS_FILE to enable."; \
	fi
	@echo "Creating GitHub OAuth secrets if credentials provided..."
	@if [ -n "$(GITHUB_CLIENT_ID)" ] && [ -n "$(GITHUB_CLIENT_SECRET)" ]; then \
		echo "Found GitHub OAuth credentials"; \
		oc create secret generic kartograph-github-oauth \
			--from-literal=client-id=$(GITHUB_CLIENT_ID) \
			--from-literal=client-secret=$(GITHUB_CLIENT_SECRET) \
			--dry-run=client -o yaml | oc apply -f -; \
		echo "GitHub OAuth secret created/updated"; \
	else \
		echo "No GitHub OAuth credentials provided (GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET is empty)"; \
		echo "GitHub SSO will not be available. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to enable."; \
	fi
	@echo "Creating authentication configuration secret..."
	@oc create secret generic kartograph-auth-config \
		--from-literal=password-enabled=$(AUTH_PASSWORD_ENABLED) \
		--from-literal=allowed-domains=$(AUTH_ALLOWED_EMAIL_DOMAINS) \
		--dry-run=client -o yaml | oc apply -f -
	@echo "Auth config: PASSWORD_ENABLED=$(AUTH_PASSWORD_ENABLED), ALLOWED_DOMAINS=$(AUTH_ALLOWED_EMAIL_DOMAINS)"
	@echo "Deploying standalone dgraph (bypassing Clowder)..."
	@oc apply -f deploy/dgraph-standalone.yaml
	@oc apply -f deploy/dgraph-services.yaml
	@echo "Processing and applying ClowdApp template (app only)..."
	@ENV_NAME=$$(oc get clowdenvironment -o jsonpath="{.items[?(@.spec.targetNamespace==\"$(BONFIRE_NAMESPACE)\")].metadata.name}" 2>/dev/null || echo "ephemeral"); \
	echo "Using ClowdEnvironment: $$ENV_NAME"; \
	oc process --local -f deploy/clowdapp.yaml \
		-p ENV_NAME=$$ENV_NAME \
		-p IMAGE=$(LOCAL_IMAGE) \
		-p IMAGE_TAG=$(LOCAL_IMAGE_TAG) \
		-p APP_PUBLIC_URL=$(APP_PUBLIC_URL) \
		-p GITHUB_URL=$(GITHUB_URL) \
		| oc apply -f -
	@echo ""
	@echo "Deployment complete! Waiting for resources to be ready..."
	@echo "Checking deployment status..."
	@oc rollout status deployment/kartograph-app --timeout=5m || true
	@echo ""
	@echo "Waiting for route to be created..."
	@for i in 1 2 3 4 5 6; do \
		ROUTE_HOST=$$(oc get route -l app=kartograph -o jsonpath='{.items[0].spec.host}' 2>/dev/null); \
		if [ -n "$$ROUTE_HOST" ]; then \
			ROUTE_URL="https://$$ROUTE_HOST/api/kartograph"; \
			ROUTE_ORIGIN="https://$$ROUTE_HOST"; \
			echo "Detected route URL: $$ROUTE_URL"; \
			echo "Detected route origin: $$ROUTE_ORIGIN"; \
			if [ "$$ROUTE_URL" != "$(APP_PUBLIC_URL)" ]; then \
				echo "Updating ClowdApp with correct URLs..."; \
				echo "Finding environment variable indices dynamically..."; \
				ORIGIN_INDEX=$$(oc get clowdapp kartograph -o json | jq -r '.spec.deployments[0].podSpec.env | to_entries | .[] | select(.value.name == "NUXT_PUBLIC_ORIGIN") | .key'); \
				TRUSTED_INDEX=$$(oc get clowdapp kartograph -o json | jq -r '.spec.deployments[0].podSpec.env | to_entries | .[] | select(.value.name == "BETTER_AUTH_TRUSTED_ORIGINS") | .key'); \
				if [ -z "$$ORIGIN_INDEX" ] || [ -z "$$TRUSTED_INDEX" ]; then \
					echo "ERROR: Could not find env var indices in ClowdApp"; \
					echo "ORIGIN_INDEX=$$ORIGIN_INDEX, TRUSTED_INDEX=$$TRUSTED_INDEX"; \
					echo "Falling back to direct deployment env update..."; \
					oc set env deployment/kartograph-app \
						NUXT_PUBLIC_ORIGIN="$$ROUTE_ORIGIN" \
						BETTER_AUTH_TRUSTED_ORIGINS="$$ROUTE_URL" 2>/dev/null || true; \
				else \
					echo "Found NUXT_PUBLIC_ORIGIN at index $$ORIGIN_INDEX"; \
					echo "Found BETTER_AUTH_TRUSTED_ORIGINS at index $$TRUSTED_INDEX"; \
					oc patch clowdapp kartograph --type=json -p="[{ \
						\"op\": \"replace\", \
						\"path\": \"/spec/deployments/0/podSpec/env/$$ORIGIN_INDEX/value\", \
						\"value\": \"$$ROUTE_ORIGIN\" \
					}, { \
						\"op\": \"replace\", \
						\"path\": \"/spec/deployments/0/podSpec/env/$$TRUSTED_INDEX/value\", \
						\"value\": \"$$ROUTE_URL\" \
					}]"; \
				fi; \
				echo "Waiting for Clowder to reconcile..."; \
				sleep 10; \
			fi; \
			echo ""; \
			echo "Application URL: $$ROUTE_URL"; \
			exit 0; \
		fi; \
		echo "Waiting for route (attempt $$i/6)..."; \
		sleep 10; \
	done; \
	echo "Warning: Could not detect route URL after 60 seconds"

status: ## Show deployment status
	@echo "==> ClowdApp Status"
	@oc get clowdapp kartograph -o wide 2>/dev/null || echo "ClowdApp not found"
	@echo ""
	@echo "==> Deployments"
	@oc get deployments -l app=kartograph
	@echo ""
	@echo "==> Pods"
	@oc get pods -l app=kartograph
	@echo ""
	@echo "==> Services"
	@oc get services -l app=kartograph
	@echo ""
	@echo "==> Routes"
	@oc get routes -l app=kartograph

logs: ## Tail logs from app (use POD=name for specific pod)
ifdef POD
	oc logs -f $(POD)
else
	oc logs -l deployment=kartograph-app -f --tail=100
endif

logs-dgraph: ## Tail logs from dgraph-alpha
	oc logs -l component=dgraph-alpha -f --tail=100

logs-dgraph-zero: ## Tail logs from dgraph-zero
	oc logs -l component=dgraph-zero -f --tail=100

port-forward: ## Port forward app to localhost:3003
	@echo "Forwarding kartograph-app to localhost:3003"
	@POD=$$(oc get pods -l deployment=kartograph-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No app pod found"; \
		exit 1; \
	fi; \
	oc port-forward $$POD 3003:3000

port-forward-dgraph: ## Port forward dgraph-alpha to localhost (use DGRAPH_PORT=8081 to specify port)
	@POD=$$(oc get pods -l component=dgraph-alpha -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No dgraph-alpha pod found"; \
		exit 1; \
	fi; \
	LOCAL_PORT=$(DGRAPH_PORT); \
	while ss -tln | grep -q ":$$LOCAL_PORT " ; do \
		echo "Port $$LOCAL_PORT is in use, trying $$((LOCAL_PORT + 1))..."; \
		LOCAL_PORT=$$((LOCAL_PORT + 1)); \
	done; \
	echo "Forwarding dgraph-alpha to localhost:$$LOCAL_PORT"; \
	echo "Port forwarding dgraph-alpha pod: $$POD"; \
	echo "You can now load data using:"; \
	echo "  cd .. && python load_dgraph.py --input working/combined_graph.jsonld --dgraph-url http://localhost:$$LOCAL_PORT"; \
	echo ""; \
	oc port-forward $$POD $$LOCAL_PORT:8080

shell: ## Open shell in app pod
	@POD=$$(oc get pods -l deployment=kartograph-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No app pod found"; \
		exit 1; \
	fi; \
	oc rsh $$POD

clean: ## Delete the deployment
	@echo "Deleting deployment from namespace: $(NAMESPACE)"
	oc delete clowdapp kartograph --ignore-not-found=true
	oc delete deployment kartograph-dgraph-zero kartograph-dgraph-alpha --ignore-not-found=true
	oc delete svc kartograph-dgraph-zero kartograph-dgraph-alpha --ignore-not-found=true
	oc delete pvc dgraph-zero-pvc dgraph-alpha-pvc app-pvc --ignore-not-found=true
	oc delete secret kartograph-secrets --ignore-not-found=true

restart: ## Restart all deployments
	@echo "Restarting deployments..."
	oc rollout restart deployment/kartograph-app
	oc rollout restart deployment/kartograph-dgraph-alpha
	oc rollout restart deployment/kartograph-dgraph-zero

test-local: ## Run local development server
	npm run dev

lint: ## Run linter
	npm run lint

format: ## Format code
	npm run format || npx prettier --write .

# Quick deployment workflow
quick-deploy: build-push deploy ## Build, push, and deploy in one command

# Development workflow
dev-setup: ## Setup local development environment
	@echo "Installing dependencies..."
	npm install
	@echo ""
	@echo "Development setup complete!"
	@echo "Run 'make test-local' to start the dev server"

# Data loading
DGRAPH_PORT ?= 8080
GRAPH_FILE ?= working/knowledge_graph.jsonld

# Helper function to find a free port
find-free-port:
	@PORT=$(DGRAPH_PORT); \
	while ss -tln | grep -q ":$$PORT " ; do \
		echo "Port $$PORT is in use, trying next port..."; \
		PORT=$$((PORT + 1)); \
	done; \
	echo $$PORT

load-data: ## Load graph data into remote dgraph (use GRAPH_FILE=path/to/file.jsonld)
	@echo "This will port-forward dgraph-alpha and load data from $(GRAPH_FILE)"
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
		cd .. && python extraction/load_dgraph.py --input $(GRAPH_FILE) --dgraph-url http://localhost:$$HTTP_PORT; \
		LOAD_EXIT=$$?; \
		echo ""; \
		echo "Stopping port-forwards..."; \
		kill $$PF_PID $$ZERO_PID 2>/dev/null || true; \
		wait $$PF_PID $$ZERO_PID 2>/dev/null || true; \
		exit $$LOAD_EXIT; \
	fi

# Bonfire-specific targets
bonfire-deploy: ## Deploy using bonfire (alias for deploy-ephemeral)
	$(MAKE) deploy-ephemeral

bonfire-clean: ## Remove bonfire ephemeral namespace
	bonfire namespace release $(BONFIRE_NAMESPACE)

# Image inspection
image-inspect: ## Inspect the container image
	docker inspect $(IMAGE):$(IMAGE_TAG)

image-run-local: ## Run the container image locally
	docker run -it --rm \
		-p 3000:3000 \
		-e DGRAPH_URL=http://host.docker.internal:8080 \
		-e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/kartograph \
		-e BETTER_AUTH_SECRET=$$(openssl rand -base64 32) \
		$(IMAGE):$(IMAGE_TAG)
