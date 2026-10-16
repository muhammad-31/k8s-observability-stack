#!/usr/bin/env python3
"""Static checks for Grafana dashboards before they reach a cluster.

- valid JSON, unique dashboard uid, title present
- every panel uses a datasource variable or a known uid (no hard-coded IDs)
- panels fit the 24-column grid and do not overlap
- every PromQL expression parses (checked with promtool)
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

ALLOWED_DATASOURCES = {"${datasource}", "loki"}
errors = []
uids = {}
exprs = []

for path in sorted(glob.glob("dashboards/*.json")):
    with open(path) as f:
        try:
            dash = json.load(f)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue

    uid = dash.get("uid")
    if not uid or not dash.get("title"):
        errors.append(f"{path}: missing uid or title")
    elif uid in uids:
        errors.append(f"{path}: uid {uid!r} already used by {uids[uid]}")
    uids[uid] = path

    occupied = {}
    for panel in dash.get("panels", []):
        title = panel.get("title", "?")
        grid = panel["gridPos"]
        if grid["x"] + grid["w"] > 24:
            errors.append(f"{path}: panel {title!r} is wider than the grid")
        for dx in range(grid["w"]):
            for dy in range(grid["h"]):
                cell = (grid["x"] + dx, grid["y"] + dy)
                if cell in occupied:
                    errors.append(f"{path}: panel {title!r} overlaps {occupied[cell]!r}")
                    break
                occupied[cell] = title
            else:
                continue
            break
        if panel["type"] == "row":
            continue
        uid_ds = panel.get("datasource", {}).get("uid")
        if uid_ds not in ALLOWED_DATASOURCES:
            errors.append(f"{path}: panel {title!r} uses datasource {uid_ds!r}")
        if not panel.get("targets"):
            errors.append(f"{path}: panel {title!r} has no queries")
        for target in panel.get("targets", []):
            if panel.get("datasource", {}).get("type") == "prometheus":
                exprs.append((path, title, target["expr"]))

# Substitute template variables and let promtool parse every expression.
rules = {"groups": [{"name": "dashboard-exprs", "rules": []}]}
for i, (_, _, expr) in enumerate(exprs):
    concrete = (expr.replace("$namespace", "default").replace("$job", "web")
                .replace("$pod", ".*"))
    rules["groups"][0]["rules"].append({"record": f"dashboard:expr_{i}", "expr": concrete})

with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
    json.dump(rules, tmp)
result = subprocess.run(["promtool", "check", "rules", tmp.name], capture_output=True, text=True)
os.unlink(tmp.name)
if result.returncode != 0:
    errors.append("PromQL errors:\n" + result.stdout + result.stderr)

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"{len(uids)} dashboards, {len(exprs)} PromQL expressions: OK")
