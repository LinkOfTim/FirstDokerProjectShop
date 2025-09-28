SHELL := /bin/bash
.PHONY: k8s k8s-down k8s-port compose-up compose-down recreate images k8s-build k8s-load k8s-apply k8s-wait k8s-logs k8s-scale ingress-enable
PORT ?= 8000
DEPLOY ?= gateway
REPLICAS ?= 2

IMAGES := \
  auth-service:local \
  catalog-service:local \
  order-service:local \
  cart-service:local \
  gateway:local

# One-command Kubernetes demo (minikube): builds images into minikube and applies k8s/
k8s:
	set -euo pipefail; \
	if ! command -v minikube >/dev/null 2>&1; then echo "minikube is required"; exit 1; fi; \
	minikube status >/dev/null 2>&1 || minikube start; \
	eval $$(minikube -p minikube docker-env); \
	docker build -t auth-service:local services/auth_service; \
	docker build -t catalog-service:local services/catalog_service; \
	docker build -t order-service:local services/order_service; \
	docker build -t cart-service:local services/cart_service; \
	docker build -t gateway:local services/gateway; \
	kubectl apply -k k8s; \
	echo "Applied manifests. Use 'make k8s-port' or enable Ingress: 'minikube addons enable ingress && kubectl apply -f k8s/ingress.yaml'";

# Build all service images with host Docker (useful for Docker Compose)
images:
	set -euo pipefail; \
	docker build -t auth-service:local services/auth_service; \
	docker build -t catalog-service:local services/catalog_service; \
	docker build -t order-service:local services/order_service; \
	docker build -t cart-service:local services/cart_service; \
	docker build -t gateway:local services/gateway

# Build images directly into Minikube's Docker daemon
k8s-build:
	set -euo pipefail; \
	if ! command -v minikube >/dev/null 2>&1; then echo "minikube is required"; exit 1; fi; \
	minikube status >/dev/null 2>&1 || minikube start; \
	eval $$(minikube -p minikube docker-env); \
	$(MAKE) images

# Load already-built local images into Minikube
k8s-load:
	set -euo pipefail; \
	if ! command -v minikube >/dev/null 2>&1; then echo "minikube is required"; exit 1; fi; \
	minikube status >/dev/null 2>&1 || minikube start; \
	for img in $(IMAGES); do \
	  echo "Loading $$img into minikube..."; \
	  minikube image load $$img; \
	done

# Apply manifests (kustomize)
k8s-apply:
	kubectl apply -k k8s

# Wait until all deployments are Available
k8s-wait:
	set -euo pipefail; \
	for d in auth catalog order cart gateway; do \
	  echo "Waiting for $$d rollout..."; \
	  kubectl rollout status deployment/$$d --timeout=180s; \
	done

# Delete all resources created by kustomize
k8s-down:
	kubectl delete -k k8s || true

# Port-forward gateway service to localhost:8000
k8s-port:
	kubectl port-forward svc/gateway $(PORT):8000

# Convenience: docker compose up/down
compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

# Rebuild local images, apply k8s manifests and restart deployments
recreate:
	set -euo pipefail; \
	if ! command -v minikube >/dev/null 2>&1; then echo "minikube is required"; exit 1; fi; \
	minikube status >/dev/null 2>&1 || minikube start; \
	eval $$(minikube -p minikube docker-env); \
	docker build -t auth-service:local services/auth_service; \
	docker build -t catalog-service:local services/catalog_service; \
	docker build -t order-service:local services/order_service; \
	docker build -t cart-service:local services/cart_service; \
	docker build -t gateway:local services/gateway; \
	kubectl apply -k k8s; \
	kubectl rollout restart deployment auth catalog order cart gateway; \
	for d in auth catalog order cart gateway; do \
	  echo "Waiting for $$d rollout..."; \
	  kubectl rollout status deployment/$$d --timeout=120s; \
	done; \
	echo "All services recreated."

# Tail logs from a deployment (DEPLOY?=gateway)
k8s-logs:
	kubectl logs -f deploy/$(DEPLOY)

# Scale a deployment (DEPLOY, REPLICAS)
k8s-scale:
	kubectl scale deploy/$(DEPLOY) --replicas=$(REPLICAS)

# Enable Ingress addon and apply ingress manifest
ingress-enable:
	set -euo pipefail; \
	minikube addons enable ingress; \
	kubectl apply -f k8s/ingress.yaml; \
	echo "Add host entry: echo \"$$(minikube ip) shop.local\" | sudo tee -a /etc/hosts"; \
	echo "Open http://shop.local"
