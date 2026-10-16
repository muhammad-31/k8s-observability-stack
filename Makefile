# Local workflow: validate, or run the whole stack on a kind cluster.
CLUSTER ?= observability
KPS_VERSION   ?= 92.9.0
LOKI_VERSION  ?= 18.16.1
ALLOY_VERSION ?= 1.13.0

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

.PHONY: validate
validate: ## Everything CI runs
	./hack/validate.sh

.PHONY: test-rules
test-rules: ## promtool check + unit tests for the alert rules
	./hack/test-rules.sh

.PHONY: test-routing
test-routing: ## amtool check-config + routing assertions
	./hack/test-alert-routing.sh

.PHONY: dashboards
dashboards: ## Regenerate dashboards/*.json from hack/generate-dashboards.py
	python3 hack/generate-dashboards.py
	python3 hack/lint-dashboards.py

.PHONY: up
up: cluster secrets install ## kind cluster with the full stack (direct Helm install)

.PHONY: cluster
cluster:
	kind create cluster --name $(CLUSTER)

.PHONY: secrets
secrets: ## Demo secrets: random Grafana password, placeholder receivers
	kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n monitoring create secret generic grafana-admin \
		--from-literal=admin-user=admin \
		--from-literal=admin-password="$$(openssl rand -base64 18)" \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n monitoring create secret generic alertmanager-receivers \
		--from-literal=slack-webhook-url=http://localhost:9/slack \
		--from-literal=pagerduty-routing-key=placeholder \
		--from-literal=deadmans-switch-url=http://localhost:9/heartbeat \
		--dry-run=client -o yaml | kubectl apply -f -

.PHONY: install
install: ## helm install the three charts, then apply this repo's config
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
	helm repo add grafana-community https://grafana-community.github.io/helm-charts --force-update
	helm repo add grafana https://grafana.github.io/helm-charts --force-update
	helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack --version $(KPS_VERSION) \
		-n monitoring -f values/kube-prometheus-stack.yaml --wait --timeout 10m
	kustomize build . | kubectl apply --server-side -f -
	helm upgrade --install loki grafana-community/loki --version $(LOKI_VERSION) \
		-n monitoring -f values/loki.yaml --wait --timeout 10m
	helm upgrade --install alloy grafana/alloy --version $(ALLOY_VERSION) \
		-n monitoring -f values/alloy.yaml --wait --timeout 5m

.PHONY: grafana
grafana: ## Grafana on http://localhost:3000 (prints the admin password)
	@kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo
	kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80

.PHONY: down
down: ## Delete the kind cluster
	kind delete cluster --name $(CLUSTER)
