# Kubernetes Manifests

## Layout
- base/: shared manifests for API, workers, beat, service, ingress, and config.
- overlays/staging/: staging-specific patches (replica count and environment overrides).

## Apply Staging Overlay
```bash
kubectl apply -k infra/k8s/overlays/staging
```

## Notes
- Provide real secrets from a secure secret manager before deployment.
- Update image references in base deployments to your registry and tag.
- Ensure Redis/PostgreSQL/Elasticsearch are reachable from cluster networking.
