#!/usr/bin/env bash
# Validate the Alertmanager config and assert where each kind of alert goes.
set -euo pipefail

config=alertmanager/alertmanager.yaml
amtool check-config "$config"

failures=0
expect() {
  local want="$1"; shift
  local got
  got="$(amtool config routes test --config.file="$config" "$@" | tr -d '\n')"
  if [[ "$got" == "$want" ]]; then
    printf '  ok    %-40s -> %s\n' "$*" "$got"
  else
    printf '  FAIL  %-40s -> got "%s", want "%s"\n' "$*" "$got" "$want"
    failures=$((failures + 1))
  fi
}

echo "Routing tests:"
expect "pagerduty,slack-incidents" alertname=ErrorBudgetBurnFast severity=page namespace=shop
expect "pagerduty,slack-incidents" alertname=ArgoCDAppDegraded severity=critical
expect "slack-alerts"              alertname=ErrorBudgetBurnSlow severity=ticket namespace=shop
expect "slack-alerts"              alertname=ContainerOOMKilled severity=warning
expect "deadmans-switch"           alertname=Watchdog severity=none
expect "blackhole"                 alertname=InfoInhibitor severity=none
expect "blackhole"                 alertname=KubeQuotaAlmostFull severity=info
expect "slack-alerts"              alertname=SomethingNew

exit "$failures"
