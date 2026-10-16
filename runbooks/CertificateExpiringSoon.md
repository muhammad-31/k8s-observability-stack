# CertificateExpiringSoon / CertificateNotReady

**What it means:** cert-manager renews certificates 30 days before they expire.
A certificate within 14 days of expiry, or one that has stayed not-ready for 30
minutes, means issuance is failing. When it expires, browsers and clients will
refuse the connection.

## Triage

```bash
kubectl -n <namespace> describe certificate <name>
kubectl -n <namespace> get certificaterequests,orders,challenges
kubectl -n cert-manager logs deploy/cert-manager --since=1h | grep -i error
```

## Common causes

| Where it is stuck | Cause | Fix |
|---|---|---|
| Challenge pending (HTTP-01) | Port 80 not reachable, or no HTTP listener on the Gateway | Check DNS points at the load balancer and the Gateway's `http` listener allows the solver route. |
| Order invalid | DNS name does not resolve to this cluster | Fix the DNS record, then delete the CertificateRequest to retry. |
| Rate limited | Too many requests to Let's Encrypt | Wait for the limit to reset; test with the staging issuer first. |
| Issuer not ready | ACME account key or email problem | `kubectl describe clusterissuer <name>`. |

If expiry is less than 48 hours away, consider issuing a temporary certificate
manually while you fix automation.
