## Plan: NextDmarc Backend Execution Checklist

Build the backend from scratch in phased increments, with each task tracked as a checkbox so an implementation agent can mark completed work as done by changing [ ] to [x]. This plan is ordered to reduce risk: foundation first, ingestion second, analysis third, alerting/deployment fourth.

**How to mark done**
1. For every completed task, replace [ ] with [x].
2. Do not mark a phase complete until all verification items for that phase pass.
3. Keep this file as the source of truth for progress status.

**Steps**
1. Phase 0 - Setup Decisions (blocks all later phases)
[x] Confirm scope is MVP backend only (exclude RUF, billing, ML anomaly detection).
[x] Confirm auth model is JWT RS256 with refresh tokens.
[x] Confirm multi-tenancy isolation model is PostgreSQL RLS + tenant context in session.
[x] Confirm SIEM export format for MVP (recommended: JSON; defer CEF/STIX variants).
[x] Confirm backend root structure under backend/ based on deployment plan.
[x] Phase exit criteria: all five decisions documented in backend README decision log.

2. Phase 1 - Foundation (depends on Step 1)
[x] Initialize backend project scaffolding in backend/ with app/, infra/, tests/, scripts/, .github/workflows/.
[x] Create pyproject.toml and uv.lock with core runtime/dev dependencies from the deployment plan.
[x] Configure quality gates: ruff, mypy --strict, bandit, pip-audit, pytest, pytest-cov.
[x] Implement app core bootstrap: app/main.py, app/core/config.py, app/core/exceptions.py, app/core/dependencies.py, app/core/middleware.py.
[x] Implement security primitives: app/core/security.py (password hashing, JWT encode/decode).
[x] Implement RBAC matrix and enforcement in app/core/rbac.py.
[x] Set up async SQLAlchemy engine/session and base model wiring in app/db/base.py and app/db/session.py.
[x] Initialize Alembic and create first migration covering tenant/auth/domain/report/source/alert tables.
[x] Add PostgreSQL RLS enablement + tenant isolation policies in migrations.
[x] Implement health endpoints: /health and /health/ready.
[x] Implement auth endpoints: /api/v1/auth/login, /refresh, /logout, /register-tenant.
[x] Add CI workflow for lint, security scan, and tests.
[x] Add Dockerfiles and docker-compose local stack skeleton (postgres, redis, elasticsearch, minio, api).
[x] Phase exit criteria: local API boots, migration runs, auth flow works, CI job passes.

3. Phase 2 - Ingestion Pipeline (depends on Step 2)
[x] Configure Celery app and queues: collect.queue, parse.queue, analysis.queue, correlate.queue, score.queue, recommend.queue, alert.queue.
[x] Implement collector services: IMAP client, attachment decompressor, MinIO uploader.
[x] Implement collector worker task with retries and idempotency guard.
[x] Implement parser services: safe XML parse (defusedxml), provider normalization, optional schema validation.
[x] Implement parser worker task with DB persistence and Elasticsearch indexing.
[x] Implement repository layer for report raw/report/report records CRUD and pagination helpers.
[x] Implement domains API CRUD + domain policy read route.
[x] Implement mailboxes API CRUD + mailbox test + manual trigger endpoint.
[x] Implement reports API list/detail/records.
[x] Implement records API search/detail/export backed by Elasticsearch queries.
[x] Add scheduler (Celery Beat) for periodic mailbox polling.
[x] Add Flower monitoring service to local compose stack.
[x] Phase exit criteria: collect -> parse -> persist -> index flow works end to end in integration tests.

4. Phase 3 - Analysis, Correlation, Scoring (depends on Step 3)
[x] Implement alignment analysis module (SPF/DKIM/DMARC alignment and conformance metrics).
[x] Implement analysis worker that computes conformance and enqueues downstream tasks.
[x] Implement correlation detector rules (repeated failures, volume anomaly, new source, cross-domain spoofing).
[x] Implement correlation classifier and incident creation logic.
[x] Implement enrichment clients (GeoIP, ASN, AbuseIPDB, VirusTotal) with caching/rate protection.
[x] Implement scoring formula and risk state transitions.
[x] Implement scoring worker to upsert current score and append history.
[x] Implement recommendation analyzers (SPF, DKIM, policy advisor, maturity scorer).
[x] Implement recommendation worker to persist recommendations.
[x] Implement sources API list/detail/history/records.
[x] Implement analytics API (conformance, risk-trend, top-sources, volume, spf-dkim-breakdown).
[x] Implement incidents API list/detail/close.
[x] Phase exit criteria: analytics and source intelligence endpoints return real computed data.

5. Phase 4 - Alerting, Integrations, Realtime, Hardening (depends on Step 4)
[x] Implement alert router with severity-to-channel mapping.
[x] Implement notifiers: email, Slack webhook, SIEM push.
[x] Implement alerts worker for lifecycle creation and channel dispatch.
[x] Implement alerts API triage actions (status updates, assign, comment, escalate) with audit trail.
[x] Implement WebSocket alerts endpoint using Redis Pub/Sub for tenant-scoped realtime events.
[x] Implement integrations API CRUD and connector test endpoint.
[x] Implement recommendations API list/detail/resolve.
[x] Implement IOC feed endpoints (JSON + CSV; optional STIX deferred unless confirmed in Phase 0).
[x] Implement structured logging (structlog JSON), metrics exposure, and OpenTelemetry instrumentation.
[x] Finalize rate limiting and audit logging across write operations.
[x] Complete Kubernetes manifests and overlays for staging rollout.
[x] Phase exit criteria: alert lifecycle, realtime push, and staging deployment are validated.

6. Phase 5 - Verification and Release Readiness (depends on Steps 2-5)
[x] Unit tests for parser, alignment, scoring, recommendations, correlation.
[x] Integration tests for auth, reports, pipeline, alerts.
[x] E2E test with representative DMARC XML fixtures (Google + Microsoft formats).
[x] Validate tenant isolation via explicit RLS tests (cross-tenant access must fail).
[x] Validate retry/idempotency behavior for collector/parser workers.
[x] Run lint/type/security/coverage gates and document outputs.
[x] Execute performance smoke test target and capture baseline metrics.
[x] Finalize backend README runbook and API usage notes.
[x] Release readiness checklist signed off.

7. Phase 6 - ML Anomaly Detection (post-MVP, depends on Step 6)
[ ] Define anomaly detection use-cases and labels (source-level, domain-level, time-window level).
[ ] Implement feature engineering pipeline from parsed records and source history.
[ ] Build offline training job for baseline unsupervised model (Isolation Forest recommended for v1).
[ ] Add model artifact/version registry metadata (model_id, feature_version, trained_at, metrics).
[ ] Implement batch inference worker to score new report records and emit anomaly signals.
[ ] Add anomaly score storage schema and history retention policy.
[ ] Add fallback logic to rules-only scoring when model is unavailable or stale.
[ ] Add drift monitoring and scheduled retraining policy.
[ ] Add tenant-level feature flag for controlled rollout of ML scoring.
[ ] Add evaluation suite (precision/recall proxy metrics + false positive review workflow).
[ ] Phase exit criteria: offline metrics documented, inference stable in staging, and rollback path validated.

8. Phase 7 - Model Implementation in Platform (post-MVP, depends on Step 7)
[ ] Implement model loading service with strict model/version compatibility checks.
[ ] Implement online inference endpoint/service contract for anomaly scoring requests.
[ ] Integrate model inference into existing analysis/scoring pipeline with timeout and circuit-breaker guards.
[ ] Add prediction persistence (score, confidence, model_id, feature_version, inference_timestamp).
[ ] Expose anomaly results in analytics/reporting APIs and tenant dashboards.
[ ] Add real-time anomaly event publishing into alert pipeline with severity mapping.
[ ] Add tenant-level rollout controls (enable/disable, percentage rollout, canary tenants).
[ ] Implement platform fallback behavior when inference service is degraded (rules-only path).
[ ] Add observability for inference latency, error rate, throughput, and model-specific health.
[ ] Implement rollback playbook for model/version revert without service downtime.
[ ] Phase exit criteria: model is fully integrated in platform flows, SLOs are met in staging, and rollback is validated.

**Parallelism and Dependencies**
1. Can run in parallel after Phase 1 core is stable: CI pipeline setup, Docker compose hardening, and API schema definitions.
2. Can run in parallel during Phase 2: domains/mailboxes APIs and parser normalization tests.
3. Can run in parallel during Phase 3: enrichment clients and recommendation analyzers.
4. Must stay sequential: migration baseline -> auth and RBAC -> ingestion -> analysis/scoring -> alerting/realtime.

**Relevant files**
- frontend/DMARC_Backend_Deployment_Plan.md - primary functional and architecture source.
- backend/ - target implementation root (currently empty placeholder).
- frontend/src/data/mock.js - implied data contract examples for early API response shaping.
- frontend/src/access/roles.js - role model that should map to backend RBAC enforcement.
- frontend/src/pages/alerts.js - expected alert list and realtime flow target.
- frontend/src/pages/dashboard.js - expected analytics response surfaces.
- frontend/src/pages/domains.js - expected domain and policy management outputs.

**Verification**
1. Every phase must end with passing tests for that phase and an updated [x] completion state in this file.
2. Minimum quality gates before merge: lint, type check, security scan, and tests all pass.
3. Coverage target for MVP backend: at least 80% on unit + integration suites.
4. Manual checks required: login flow, report ingestion flow, alert triage flow, tenant isolation checks.

**Decisions**
- Included scope: backend API, workers, data model, observability, security controls, local dev stack, and staging deployment manifests.
- Excluded for MVP: forensic RUF deep analysis, billing, and full SOAR automation.
- Post-MVP planned scope: ML anomaly detection and model lifecycle in Phase 6.
- Progress tracking rule: this checklist is the live execution tracker for the implementation agent.
