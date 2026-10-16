# ArgoCDAppDegraded / ArgoCDAppOutOfSync

**What it means:**

- **Degraded:** a resource managed by the application is unhealthy, such as a
  Deployment that cannot roll out or a pod in CrashLoopBackOff.
- **OutOfSync for 30 minutes:** the cluster does not match Git and automated
  sync has not been able to fix it.

## Triage

```bash
argocd app get <app>               # which resources are Degraded / OutOfSync
argocd app diff <app>              # what differs from Git
kubectl -n argocd logs deploy/argocd-application-controller --since=30m | grep <app>
```

## Common causes

| Symptom | Cause | Fix |
|---|---|---|
| Sync fails with "admission webhook denied" | A Kyverno policy (prod: Deny) rejects the change | Fix the manifest. CI shows the same error on the pull request. |
| OutOfSync on every refresh | Another controller mutates a field (HPA replicas, injected sidecars) | Add an `ignoreDifferences` entry for that field. |
| Degraded Deployment | Image pull error, failing probes, OOM | `kubectl describe` the pods. See ContainerOOMKilled.md. |
| OutOfSync after a manual `kubectl edit` | Drift; self-heal reverts it | Make the change in Git instead. |
