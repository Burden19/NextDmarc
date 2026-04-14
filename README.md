# NextDmarc

<p align="center">
  <strong>Multi-tenant DMARC monitoring platform with a FastAPI backend and a SOC-oriented Next.js frontend.</strong>
</p>

<p align="center">
  <img alt="Backend" src="https://img.shields.io/badge/Backend-FastAPI%20%2B%20Celery-0f766e" />
  <img alt="Frontend" src="https://img.shields.io/badge/Frontend-Next.js%2014-111827?logo=next.js" />
  <img alt="UI" src="https://img.shields.io/badge/UI-Material%20UI%20%2B%20Tailwind-0f4c97" />
  <img alt="Status" src="https://img.shields.io/badge/Status-Backend%2FFrontend%20Wired-1f8f5f" />
</p>

---

## Overview

NextDmarc provides tenant-scoped DMARC visibility, risk scoring, recommendations, integrations, and alert triage workflows.
The application now runs as a full stack system:

- `backend/` contains FastAPI APIs, Celery workers, persistence, security hardening, and operational scripts.
- `frontend/` contains the Next.js UI fully wired to backend APIs (mock data dependency removed).

---

## Current Status

- Real authentication flow is enabled (register/login/refresh/logout).
- Tenant-scoped APIs are active with role-aware frontend behavior.
- Realtime alerts are available through WebSocket stream consumption.
- Alert triage, recommendation resolve/reopen, and integration CRUD/test workflows are implemented.
- Verification artifacts and quality gate reports are tracked under `backend/artifacts/`.

---

## Tech Stack

### Backend
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL + Redis + Elasticsearch + MinIO
- Celery workers for collect/parse/analyze/correlate/score/recommend/alert stages
- Security baseline: JWT RS256, refresh-cookie + CSRF, RBAC, tenant scoping

### Frontend
- Next.js 14 (Pages Router) + React 18
- Material UI + Tailwind CSS
- Shared auth session + API client with refresh retry and CSRF forwarding

---

## Repository Layout

```text
NextDmarc/
|-- backend/
|   |-- app/                # FastAPI app, services, repositories, workers
|   |-- tests/              # Backend unit/integration tests
|   |-- infra/              # Kubernetes and infra resources
|   |-- scripts/            # Quality, demo, and smoke scripts
|   `-- artifacts/          # Latest quality/progress/performance checkpoints
|-- frontend/
|   |-- src/pages/          # Next.js routes
|   |-- src/components/     # Shared UI/layout components
|   |-- src/lib/            # Auth session and API client
|   |-- src/access/         # Role and route permissions
|   `-- src/theme.js        # MUI theme tokens
`-- README.md
```

---

## Local Development

### 1) Backend

From `backend/`:

```bash
pip install -e .
docker compose up -d postgres redis elasticsearch minio
alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`
Backend URL: `http://localhost:8000`

---

## Quality Checks

Backend (from `backend/`):

```bash
./scripts/quality-gates.ps1
```

Frontend (from `frontend/`):

```bash
npm run lint
npm run build
```

---

## Operational Artifacts

Most recent checkpoints and execution summaries:

- `backend/artifacts/supervisor-progress-latest.md`
- `backend/artifacts/session-checkpoint-2026-04-08.md`
- `backend/artifacts/quality-gates-latest.md`
- `backend/artifacts/pipeline-live-demo-latest.md`
- `backend/artifacts/performance-smoke-baseline-latest.md`

---

## Role Model

Roles used by both frontend and backend:

- `nextstep_admin`
- `client_admin`
- `analyst_soc`
- `client_user`

---

## License

No open-source license is currently declared.

