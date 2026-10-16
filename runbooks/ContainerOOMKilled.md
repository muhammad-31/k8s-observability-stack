# ContainerOOMKilled

**What it means:** a container used more memory than its limit and the kernel
killed it. Kubernetes restarted it, so the alert is a warning, but repeated OOM
kills mean dropped requests and a crash loop is close.

## Triage

```bash
kubectl -n <namespace> describe pod <pod> | grep -A5 "Last State"
kubectl -n <namespace> top pod <pod> --containers
```

On the **Workload overview** dashboard, compare *Memory working set* with the
limit line for that pod:

- **Climbs steadily until it hits the limit:** a memory leak. Restarting only hides it.
- **Jumps on certain requests or traffic peaks:** the limit is too low for real load.
- **Flat, then a sudden spike:** an unusually large payload, a batch job, or a cache warm-up.

## Fix

- Limit too low: raise `resources.limits.memory` (and the request) in the app's
  values file and merge. Keep the limit 1.5-2x the normal working set.
- Leak: capture a heap profile before the next kill, open a bug, and raise the
  limit temporarily so the service stays up.
- JVM, Node.js and Go apps: make sure the runtime knows the container limit
  (`-XX:MaxRAMPercentage`, `--max-old-space-size`, `GOMEMLIMIT`).
