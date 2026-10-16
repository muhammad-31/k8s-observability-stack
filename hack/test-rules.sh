#!/usr/bin/env bash
# promtool needs plain rule files, so pull .spec out of each PrometheusRule,
# then lint and unit-test them.
set -euo pipefail

mkdir -p build/rules
for file in rules/*.yaml; do
  yq -o yaml '.spec' "$file" > "build/rules/$(basename "$file")"
done

promtool check rules build/rules/*.yaml
promtool test rules rules/tests/*.test.yaml
