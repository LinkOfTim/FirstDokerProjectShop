SHELL := /bin/bash
.PHONY: k8s k8s-down k8s-port compose-up compose-down recreate
PORT ?= 8000

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
