#!/usr/bin/env bash
# Everything CI checks, runnable locally: make validate
set -euo pipefail

K8S_VERSION="${K8S_VERSION:-1.35.0}"
CRD_SCHEMAS='https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# Chart versions, kept in sync with argocd/*.yaml
KPS_VERSION=92.9.0
LOKI_VERSION=18.16.1
ALLOY_VERSION=1.13.0

out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT

echo "==> Prometheus rules (promtool check + unit tests)"
./hack/test-rules.sh

echo "==> Alertmanager config and routing"
./hack/test-alert-routing.sh

echo "==> Alloy pipeline"
alloy fmt alloy/config.alloy | diff -u alloy/config.alloy - || { echo "run: alloy fmt -w alloy/config.alloy"; exit 1; }
alloy validate alloy/config.alloy

echo "==> Grafana dashboards"
python3 hack/generate-dashboards.py >/dev/null
git diff --exit-code -- dashboards/ || { echo "dashboards/*.json are out of date: run hack/generate-dashboards.py"; exit 1; }
python3 hack/lint-dashboards.py

echo "==> Render Helm charts and Kustomize"
# OFFLINE_CHARTS=<dir with unpacked charts> renders without network access.
if [[ -n "${OFFLINE_CHARTS:-}" ]]; then
  kps=(--version "$KPS_VERSION" "$OFFLINE_CHARTS/kube-prometheus-stack")
  loki=(--version "$LOKI_VERSION" "$OFFLINE_CHARTS/loki")
  alloy=(--version "$ALLOY_VERSION" "$OFFLINE_CHARTS/alloy")
else
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update >/dev/null
  helm repo add grafana-community https://grafana-community.github.io/helm-charts --force-update >/dev/null
  helm repo add grafana https://grafana.github.io/helm-charts --force-update >/dev/null
  kps=(--version "$KPS_VERSION" prometheus-community/kube-prometheus-stack)
  loki=(--version "$LOKI_VERSION" grafana-community/loki)
  alloy=(--version "$ALLOY_VERSION" grafana/alloy)
fi

for env in dev prod; do
  overlay() { [[ $env == prod && -f "values/$1-prod.yaml" ]] && echo "-f values/$1-prod.yaml"; true; }
  # shellcheck disable=SC2046
  helm template kube-prometheus-stack "${kps[@]}" -n monitoring \
    -f values/kube-prometheus-stack.yaml $(overlay kube-prometheus-stack) > "$out/kps-$env.yaml"
  # shellcheck disable=SC2046
  helm template loki "${loki[@]}" -n monitoring \
    -f values/loki.yaml $(overlay loki) > "$out/loki-$env.yaml"
  # shellcheck disable=SC2046
  helm template alloy "${alloy[@]}" -n monitoring \
    -f values/alloy.yaml $(overlay alloy) > "$out/alloy-$env.yaml"
done
kustomize build . > "$out/config.yaml"
cp argocd/*.yaml examples/*.yaml "$out/"

echo "==> kubeconform (Kubernetes $K8S_VERSION + CRD catalog)"
kubeconform -strict -summary -kubernetes-version "$K8S_VERSION" \
  -schema-location default -schema-location "$CRD_SCHEMAS" "$out"/*.yaml

echo "All checks passed."
