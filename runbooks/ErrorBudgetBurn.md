# ErrorBudgetBurnFast / ErrorBudgetBurnSlow

**What it means:** the service returns more 5xx responses than its SLO allows
(99.9% success over 30 days).

| Alert | Severity | Meaning |
|---|---|---|
| ErrorBudgetBurnFast | page | The monthly error budget would be gone in under ~2 days at this rate. |
| ErrorBudgetBurnSlow | ticket | Errors have stayed above the SLO for hours. Not urgent, but the month's budget is at risk. |

## Triage (first 5 minutes)

1. Open the **SLO overview** dashboard and pick the namespace and service from the alert.
2. Check *Requests by status code*: one status (502, 503, 500) or all of them?
3. Did something just change?
   ```bash
   kubectl -n <namespace> rollout history deploy/<name>
   argocd app history <app>          # or the Argo CD UI
   ```
4. Look at the errors themselves in Grafana Explore (Loki):
   ```logql
   {namespace="<namespace>"} |= "error" | json | level="error"
   ```

## Common causes and fixes

| Symptom | Likely cause | Action |
|---|---|---|
| Errors started right after a deploy | Bad release | Roll back: revert the commit in Git and let Argo CD sync it. In an emergency, first turn off auto-sync (`argocd app set <app> --sync-policy none`), otherwise self-heal reverts a `kubectl rollout undo`. |
| 503s, pods restarting | Readiness failing, OOM kills | Check the **Workload overview** dashboard and `kubectl describe pod`. |
| 502/504s, latency spike | Slow dependency (database, external API) | Check the dependency's dashboard; consider shedding load or scaling. |
| Errors only on some pods | One bad node or zone | `kubectl get pods -o wide`, cordon the node. |

## After the incident

Write a short postmortem if the budget dropped below 50%. The SLO overview
dashboard shows how much was spent.
