# NextDmarc Backend

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
