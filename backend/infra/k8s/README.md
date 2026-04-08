# Kubernetes Manifests

## Layout
- base/: shared manifests for API, workers, beat, service, ingress, and config.
- overlays/staging/: staging-specific patches (replica count and environment overrides).

## Apply Staging Overlay

Run from `backend/`:

```bash
kubectl apply -k infra/k8s/overlays/staging
```

## Verify

```bash
kubectl get pods -n nextdmarc
kubectl get svc -n nextdmarc
kubectl get ingress -n nextdmarc
```

## Rollback

```bash
kubectl rollout undo deployment/nextdmarc-api -n nextdmarc
kubectl rollout undo deployment/nextdmarc-worker -n nextdmarc
```

## Notes
- Provide real secrets from a secure secret manager before deployment.
- Update image references in base deployments to your registry and tag.
- Ensure Redis/PostgreSQL/Elasticsearch are reachable from cluster networking.
