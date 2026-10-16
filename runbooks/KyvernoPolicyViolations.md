# KyvernoPolicyViolations

**What it means:** resources in a namespace violate a Kyverno policy. In dev
the policies run in Audit mode, so nothing is blocked yet. The same manifests
would be rejected in prod, where the policies Deny.

## Triage

```bash
kubectl get policyreports -n <namespace>
kubectl describe policyreport -n <namespace> <report> | grep -B2 -A6 fail
```

## Fix

Change the manifest (usually the app's Helm values), not the policy. Typical
fixes:

| Policy | Fix |
|---|---|
| disallow-latest-tag | Pin `image.tag` to a version or use `image.digest`. |
| require-requests-limits | Set `resources.requests.cpu/memory` and `resources.limits.memory`. |
| require-probes | Add readiness and liveness probes. |
| restrict-image-registries | Push the image to an approved registry (GHCR, ECR, ...). |

If a violation is legitimate (for example a third-party chart you cannot
change), add a scoped `PolicyException` and explain why in the pull request.
