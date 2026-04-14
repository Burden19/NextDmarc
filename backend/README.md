# NextDmarc Backend

Backend service for NextDmarc built with FastAPI, Celery, PostgreSQL, Redis, Elasticsearch, and MinIO.
This backend is actively wired with the frontend and provides tenant-scoped APIs, worker pipelines, alerting workflows, and operational artifacts.

## Current Status

- Phases 0 to 5 are marked complete in `plan-nextdmarc-backend.prompt.md`.
- Frontend data-bearing pages are wired to live APIs (mock data retired).
- Alerts triage + realtime stream, recommendations resolve/reopen, and integrations CRUD/test flows are implemented.
- Latest handoff checkpoint: `artifacts/session-checkpoint-2026-04-08.md`.

## Quick Start (Local)

From `backend/`:

```bash
pip install -e .
docker compose up -d postgres redis elasticsearch minio
alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Optional worker start (separate terminal):

```bash
celery -A app.workers.celery_app.celery_app worker -l info
```

On Windows, use a single-process pool to avoid billiard spawn handle errors:

```bash
celery -A app.workers.celery_app.celery_app worker -l info --pool=solo
```

API docs:
- OpenAPI: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`

## Decision Log

### Phase 0 Decisions

1. Scope
- MVP backend only.
- Excluded in MVP: RUF deep analysis, billing, and ML anomaly detection.

2. Authentication Model
- JWT with RS256 signing.
- Access token + refresh token flow.

3. Multi-Tenancy Isolation
- PostgreSQL Row-Level Security (RLS).
- Tenant context injected in DB session per request/task.

4. SIEM Export Format (MVP)
- JSON export for MVP.
- CEF/STIX deferred to later phase.

5. Backend Root Structure
- Implementation root is `backend/`.
- Planned key folders: `app/`, `infra/`, `tests/`, `scripts/`, and `.github/workflows/`.

## Quality Gates (Phase 1 - Step 3)

Configured gates for the backend foundation:
- `ruff` for linting and formatting checks.
- `mypy --strict` for static typing.
- `bandit` for source security scanning.
- `pip-audit` for dependency vulnerability scanning.
- `pytest` + `pytest-cov` for test execution and coverage reporting.

Current temporary audit exceptions in gate scripts (revisit when upstream fixes are available):
- `CVE-2024-23342` (`ecdsa`)
- `CVE-2026-4539` (`Pygments`)

Run all gates from `backend/`:
- PowerShell: `./scripts/quality-gates.ps1`
- Bash: `./scripts/quality-gates.sh`

Optional:
- Skip dependency audit temporarily when offline: `./scripts/quality-gates.ps1 -SkipAudit`
- Skip dependency audit in bash: `SKIP_AUDIT=1 ./scripts/quality-gates.sh`

## Local Docker Stack (Phase 1 - Step 13)

The backend now includes a local container skeleton for:
- `postgres`
- `redis`
- `elasticsearch`
- `minio`
- `api`

Run from `backend/`:
- Start: `docker compose up --build`
- Stop: `docker compose down`

Exposed ports:
- API: `8000`
- PostgreSQL: `5432`
- Redis: `6379`
- Elasticsearch: `9200`
- MinIO API: `9000`
- MinIO Console: `9001`

## Security Baseline Configuration (Phase 1)

Phase 1 introduces explicit security configuration for CORS, trusted hosts, cookie behavior, and login-throttle thresholds.

Environment variables:
- `CORS_ORIGINS` (CSV): allowed browser origins.
- `TRUSTED_HOSTS` (CSV): allowed `Host` header values.
- `CORS_ALLOW_CREDENTIALS` (bool): whether credentials are allowed in CORS responses.
- `CORS_ALLOWED_METHODS` (CSV): allowed methods for CORS preflight.
- `CORS_ALLOWED_HEADERS` (CSV): allowed headers for CORS preflight.
- `COOKIE_SECURE` (bool): secure-cookie flag for staged cookie migration.
- `COOKIE_SAMESITE` (`lax|strict|none`): same-site policy.
- `COOKIE_DOMAIN` (string): cookie domain scope.
- `AUTH_COOKIE_ENABLED` (bool): enable HttpOnly refresh-cookie transport.
- `AUTH_REFRESH_COOKIE_NAME` (string): refresh-cookie key.
- `AUTH_CSRF_COOKIE_NAME` (string): CSRF cookie key.
- `AUTH_CSRF_HEADER_NAME` (string): CSRF request header required on write operations when refresh cookie is present.
- `AUTH_REFRESH_COOKIE_PATH` (string): path scope for refresh cookie.
- `AUTH_CSRF_COOKIE_PATH` (string): path scope for CSRF cookie.
- `AUTH_ALLOW_REFRESH_TOKEN_BODY_FALLBACK` (bool): temporary compatibility mode for legacy body refresh/logout payloads.
- `LOGIN_MAX_ATTEMPTS` (int): max failed attempts before lockout.
- `LOGIN_LOCKOUT_SECONDS` (int): lockout duration in seconds.
- `LOGIN_WINDOW_SECONDS` (int): failure counting window in seconds.

Cookie and CSRF behavior:
- Login and refresh now set refresh and CSRF cookies.
- Logout clears refresh and CSRF cookies.
- For write methods, CSRF header validation is enforced when refresh cookie transport is active outside auth endpoints.

Startup enforcement rules:
- Development:
	- If `CORS_ORIGINS` is unset/empty, defaults are `http://localhost:3000,http://127.0.0.1:3000`.
	- If `TRUSTED_HOSTS` is unset/empty, defaults are `localhost,127.0.0.1`.
- Staging/Production:
	- `CORS_ORIGINS` must be explicitly configured.
	- Wildcard values are rejected for CORS origins and trusted hosts.
	- CORS origins must use `https://`.
	- `TRUSTED_HOSTS` must be explicitly configured.
	- `COOKIE_SECURE` must be enabled.

## Phase 4 Operations Runbook

### Alerts Realtime and Triage

HTTP endpoints:
- `GET /api/v1/alerts?page=1&page_size=25` (optional filters: `status`, `severity`)
- `POST /api/v1/alerts/{alert_id}/status`
- `POST /api/v1/alerts/{alert_id}/assign`
- `POST /api/v1/alerts/{alert_id}/comment`
- `POST /api/v1/alerts/{alert_id}/escalate`
- `GET /api/v1/alerts/{alert_id}/audit`

WebSocket endpoint:
- `GET /api/v1/alerts/ws` with tenant provided by either:
	- `X-Tenant-ID` header (UUID)
	- `tenant_id` query parameter (browser-compatible fallback)
- Uses Redis Pub/Sub channel format `alerts:tenant:{tenant_id}`

### Integrations API

- `POST /api/v1/integrations`
- `GET /api/v1/integrations`
- `GET /api/v1/integrations/{integration_id}`
- `PATCH /api/v1/integrations/{integration_id}`
- `DELETE /api/v1/integrations/{integration_id}`
- `POST /api/v1/integrations/{integration_id}/test`

Supported integration kinds:
- `email`
- `slack`
- `siem`

### Recommendations and IOC Feeds

Recommendations:
- `GET /api/v1/recommendations`
- `GET /api/v1/recommendations/{report_db_id}`
- `POST /api/v1/recommendations/{report_db_id}/resolve`
- `POST /api/v1/recommendations/{report_db_id}/reopen`

IOC feeds:
- `GET /api/v1/ioc/json`
- `GET /api/v1/ioc/csv`

### Observability and Hardening

- Structured JSON logging configured via `structlog`.
- Metrics exposed at `GET /metrics`.
- FastAPI OpenTelemetry instrumentation enabled when dependency is available.
- Baseline write-operation rate limit is enforced per tenant/IP in middleware.
- Write operation audit events are stored in Redis list `audit:write_ops`.

### Kubernetes Staging Rollout

Manifests:
- Base: `infra/k8s/base/`
- Staging overlay: `infra/k8s/overlays/staging/`

Deploy staging overlay:
- `kubectl apply -k infra/k8s/overlays/staging`

## Phase 5 Verification Runbook

### Fixture-driven E2E DMARC checks

Representative XML fixtures:
- `tests/fixtures/dmarc/google-aggregate.xml`
- `tests/fixtures/dmarc/microsoft-aggregate.xml`

Run fixture-based E2E checks:
- `python -m pytest tests/test_dmarc_e2e_fixtures.py -q --no-cov`

### Tenant isolation checks

Run explicit cross-tenant denial validation:
- `python -m pytest tests/test_tenant_isolation.py -q --no-cov`

What is validated:
- Cross-tenant `domains` access returns not found.
- Cross-tenant `mailboxes` access returns not found.
- Migration SQL includes tenant-context RLS policies.

### Collector/parser retry and idempotency checks

Run worker behavior checks:
- `python -m pytest tests/test_collect_task.py tests/test_parse_task.py tests/test_worker_retry_idempotency.py -q --no-cov`

What is validated:
- Collector run-level lock and message-level idempotency.
- Retry delay backoff capped at 300 seconds.
- Parser persistence uses conflict-safe upserts for repeat report ingestion.

### Quality gate execution and report

Run all gates:
- PowerShell: `./scripts/quality-gates.ps1`
- Bash: `./scripts/quality-gates.sh`

Latest documented output:
- `artifacts/quality-gates-latest.md`

### Performance smoke baseline

Run smoke baseline benchmark:
- `python scripts/performance_smoke.py --iterations 250`

Latest baseline artifact:
- `artifacts/performance-smoke-baseline-latest.md`

## API Usage Notes

### Tenant-scoped requests

Most API routes require the tenant header:
- `X-Tenant-ID: <uuid>`

For frontend integrations, also include:
- `Authorization: Bearer <access_token>`
- `X-Role: <role_value>`

Examples:
- List reports: `GET /api/v1/reports`
- Search records: `GET /api/v1/records?query=*`
- List alerts: `GET /api/v1/alerts?page=1&page_size=25`
- Alerts stream: `GET /api/v1/alerts/ws` (WebSocket with `X-Tenant-ID`)

### Running backend tests from repository root

If running from repo root instead of `backend/`, use:
- `python -m pytest -c backend/pyproject.toml backend/tests/<test_file>.py -q --no-cov`

This avoids import-path issues for `app.*` modules.
