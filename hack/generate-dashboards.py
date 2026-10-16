#!/usr/bin/env python3
"""Generates dashboards/*.json. Edit this file, run it, commit both."""
import json

DS = {"type": "prometheus", "uid": "${datasource}"}
LOKI = {"type": "loki", "uid": "loki"}

def ds_var():
    return {"name": "datasource", "label": "Prometheus", "type": "datasource",
            "query": "prometheus", "current": {}, "hide": 0, "refresh": 1}

def query_var(name, label, query, include_all=True, multi=True):
    return {"name": name, "label": label, "type": "query", "datasource": DS,
            "query": {"query": query, "refId": f"{name}-var"}, "definition": query,
            "refresh": 2, "includeAll": include_all, "multi": multi,
            "current": {}, "sort": 1, "hide": 0}

pid = [0]
def panel(kind, title, targets, x, y, w, h, unit=None, desc=None, thresholds=None,
          decimals=None, ds=DS, options=None, overrides=None, min_=None, max_=None):
    pid[0] += 1
    p = {"id": pid[0], "type": kind, "title": title, "datasource": ds,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [dict(t, refId=chr(65 + i), datasource=ds) for i, t in enumerate(targets)],
         "fieldConfig": {"defaults": {}, "overrides": overrides or []},
         "options": options or {}}
    d = p["fieldConfig"]["defaults"]
    if unit: d["unit"] = unit
    if decimals is not None: d["decimals"] = decimals
    if min_ is not None: d["min"] = min_
    if max_ is not None: d["max"] = max_
    if thresholds:
        d["thresholds"] = {"mode": "absolute", "steps": thresholds}
        if kind == "stat":
            d["color"] = {"mode": "thresholds"}
    if desc: p["description"] = desc
    return p

def row(title, y):
    pid[0] += 1
    return {"id": pid[0], "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}

def dashboard(uid, title, tags, variables, panels, description):
    return {"uid": uid, "title": title, "description": description, "tags": tags,
            "timezone": "utc", "editable": False, "graphTooltip": 1,
            "schemaVersion": 39, "version": 1, "refresh": "1m",
            "time": {"from": "now-24h", "to": "now"},
            "templating": {"list": variables}, "annotations": {"list": []},
            "links": [], "panels": panels}

# ---------------------------------------------------------------- SLO overview
sel = 'namespace=~"$namespace", job=~"$job"'
total = f'http_request_duration_seconds_count{{{sel}}}'
errors = f'http_request_duration_seconds_count{{{sel}, status=~"5.."}}'
slo_panels = [
    row("Service level objective: 99.9% of requests succeed (30-day window)", 0),
    panel("stat", "Availability, last 30 days",
          [{"expr": f"1 - (sum(increase({errors}[30d])) / sum(increase({total}[30d])))", "instant": True}],
          0, 1, 6, 5, unit="percentunit", decimals=3,
          thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 0.995}, {"color": "green", "value": 0.999}],
          desc="Share of requests that did not return 5xx over the last 30 days."),
    panel("stat", "Error budget remaining",
          [{"expr": f"min(slo:http_error_budget:remaining_ratio30d{{{sel}}})", "instant": True}],
          6, 1, 6, 5, unit="percentunit", decimals=1,
          thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 0.25}, {"color": "green", "value": 0.5}],
          desc="1 = no errors this month, 0 = budget used up, negative = SLO missed."),
    panel("stat", "Burn rate, last hour",
          [{"expr": f"max(slo:http_errors:ratio_rate1h{{{sel}}}) / 0.001", "instant": True}],
          12, 1, 6, 5, unit="x", decimals=1,
          thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 14.4}],
          desc="1x spends exactly the monthly budget in 30 days. 14.4x pages (2% of the budget in 1 hour)."),
    panel("stat", "Requests per second",
          [{"expr": f"sum(rate({total}[5m]))", "instant": True}],
          18, 1, 6, 5, unit="reqps", decimals=1,
          thresholds=[{"color": "blue", "value": None}]),
    panel("timeseries", "Burn rate by alert window",
          [{"expr": f"max(slo:http_errors:ratio_rate5m{{{sel}}}) / 0.001", "legendFormat": "5m"},
           {"expr": f"max(slo:http_errors:ratio_rate1h{{{sel}}}) / 0.001", "legendFormat": "1h"},
           {"expr": f"max(slo:http_errors:ratio_rate6h{{{sel}}}) / 0.001", "legendFormat": "6h"},
           {"expr": f"max(slo:http_errors:ratio_rate3d{{{sel}}}) / 0.001", "legendFormat": "3d"}],
          0, 6, 12, 9, unit="x", min_=0,
          thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 6}, {"color": "red", "value": 14.4}],
          desc="Page fires when the 1h and 5m lines are both above 14.4x (or 6h and 30m above 6x)."),
    panel("timeseries", "Requests by status code",
          [{"expr": f"sum by (status) (rate({total}[5m]))", "legendFormat": "{{status}}"}],
          12, 6, 12, 9, unit="reqps", min_=0),
    panel("timeseries", "Latency percentiles",
          [{"expr": f'histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "legendFormat": "p50"},
           {"expr": f'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "legendFormat": "p95"},
           {"expr": f'histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "legendFormat": "p99"}],
          0, 15, 12, 8, unit="s", min_=0),
    panel("timeseries", "Error ratio",
          [{"expr": f"sum(rate({errors}[5m])) / sum(rate({total}[5m]))", "legendFormat": "5xx ratio"}],
          12, 15, 12, 8, unit="percentunit", min_=0,
          thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 0.001}],
          options={"legend": {"displayMode": "list", "placement": "bottom"}}),
]
slo = dashboard(
    "slo-overview", "SLO overview", ["slo", "observability-stack"],
    [ds_var(),
     query_var("namespace", "Namespace", "label_values(http_request_duration_seconds_count, namespace)"),
     query_var("job", "Service", 'label_values(http_request_duration_seconds_count{namespace=~"$namespace"}, job)')],
    slo_panels,
    "Availability SLO, error budget and burn rate for HTTP services. Matches the ErrorBudgetBurn alerts.")

# ------------------------------------------------------ Workload golden signals
pid[0] = 0
ns = 'namespace="$namespace"'
pod_sel = f'{ns}, pod=~"$pod"'
work_panels = [
    row("Resources", 0),
    panel("timeseries", "CPU usage vs request",
          [{"expr": f'sum by (pod) (rate(container_cpu_usage_seconds_total{{{pod_sel}, container!=""}}[5m]))', "legendFormat": "{{pod}}"},
           {"expr": f'sum by (pod) (kube_pod_container_resource_requests{{{pod_sel}, resource="cpu"}})', "legendFormat": "{{pod}} request"}],
          0, 1, 12, 8, unit="cores", min_=0,
          desc="Series ending in \"request\" show the CPU request. Usage far below it means over-provisioned; far above means contention."),
    panel("timeseries", "Memory working set vs limit",
          [{"expr": f'sum by (pod) (container_memory_working_set_bytes{{{pod_sel}, container!=""}})', "legendFormat": "{{pod}}"},
           {"expr": f'sum by (pod) (kube_pod_container_resource_limits{{{pod_sel}, resource="memory"}})', "legendFormat": "{{pod}} limit"}],
          12, 1, 12, 8, unit="bytes", min_=0,
          desc="The kernel OOM-kills a container when the working set reaches its limit."),
    row("Stability", 9),
    panel("timeseries", "Container restarts (1h)",
          [{"expr": f'sum by (pod, container) (increase(kube_pod_container_status_restarts_total{{{pod_sel}}}[1h]))', "legendFormat": "{{pod}}/{{container}}"}],
          0, 10, 8, 8, unit="short", min_=0),
    panel("stat", "OOM-killed containers",
          [{"expr": f'sum(kube_pod_container_status_last_terminated_reason{{{pod_sel}, reason="OOMKilled"}}) or vector(0)', "instant": True}],
          8, 10, 4, 8, unit="short",
          thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 1}]),
    panel("timeseries", "HPA replicas",
          [{"expr": f'sum by (horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{{{ns}}})', "legendFormat": "{{horizontalpodautoscaler}} current"},
           {"expr": f'sum by (horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{{{ns}}})', "legendFormat": "{{horizontalpodautoscaler}} max"}],
          12, 10, 12, 8, unit="short", min_=0,
          desc="Current replicas sitting at max means the autoscaler has no room left."),
    row("Logs", 18),
    panel("logs", "Logs (Loki)",
          [{"expr": '{namespace="$namespace", pod=~"$pod"} |= "$search"'}],
          0, 19, 24, 12, ds=LOKI,
          options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}),
]
workload = dashboard(
    "workload-overview", "Workload overview", ["kubernetes", "observability-stack"],
    [ds_var(),
     query_var("namespace", "Namespace", "label_values(kube_pod_info, namespace)", include_all=False, multi=False),
     query_var("pod", "Pod", 'label_values(kube_pod_info{namespace="$namespace"}, pod)'),
     {"name": "search", "label": "Log search", "type": "textbox", "query": "", "current": {"value": ""}, "hide": 0}],
    work_panels,
    "CPU, memory, restarts, OOM kills, autoscaling and logs for the pods in one namespace.")

for name, d in [("slo-overview", slo), ("workload-overview", workload)]:
    with open(f"dashboards/{name}.json", "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")
print("ok")
