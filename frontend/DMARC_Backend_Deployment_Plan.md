# DMARC Analyzer Platform — Backend Deployment Plan

> **Project:** PFE03-2026-SOC · **Version:** 1.0 · **Date:** March 2026  
> **Scope:** Backend Architecture, API Services, Workers, Data Layer & DevOps  
> **Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Overview](#1-executive-overview)
2. [Technology Stack](#2-technology-stack)
3. [Backend Architecture](#3-backend-architecture)
4. [Database Design](#4-database-design)
5. [REST API Design](#5-rest-api-design)
6. [Worker Modules — Implementation Detail](#6-worker-modules--implementation-detail)
7. [Project Directory Structure](#7-project-directory-structure)
8. [Docker Compose — Local Dev Stack](#8-docker-compose--local-dev-stack)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [Kubernetes Deployment (Production)](#11-kubernetes-deployment-production)
12. [Observability Stack](#12-observability-stack)
13. [Security Hardening](#13-security-hardening)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Full Python Dependency List](#15-full-python-dependency-list)
16. [Future Extensions (Bonus Track)](#16-future-extensions-bonus-track)

---

## 1. Executive Overview

The backend is the operational core of the DMARC Analyzer Platform — a multi-tenant, SOC-driven system for ingesting, parsing, analyzing, and responding to DMARC aggregate (RUA) and forensic (RUF) reports.

**The backend is responsible for:**
- Automated DMARC report collection via IMAP
- XML parsing, normalization, and structured storage
- SPF / DKIM / DMARC alignment analysis and anomaly detection
- IP enrichment, risk scoring, and threat intelligence integration
- Real-time alerting, SIEM/SOAR push, and IOC generation
- REST + WebSocket API exposure for the frontend and third-party integrations
- Full multi-tenant RBAC governance

The frontend is considered delivered. This plan covers only the backend, its infrastructure, data layer, and DevOps pipeline.

---

## 2. Technology Stack

### 2.1 Core Runtime & Framework

| Layer | Technology | Version | Justification |
|---|---|---|---|
| Runtime | Python | 3.12 | Ecosystem dominance for security tooling, async support, typing |
| API Framework | FastAPI | 0.111+ | Async-native, OpenAPI auto-generation, Pydantic v2 validation |
| Task Queue | Celery | 5.4+ | Distributed workers, beat scheduler for IMAP polling, retry logic |
| Message Broker | Redis | 7.2 (Redis Stack) | Celery broker + result backend + pub/sub for real-time events |
| WebSocket | FastAPI WebSocket + Redis Pub/Sub | — | Real-time dashboard updates and alert streaming |
| ASGI Server | Uvicorn + Gunicorn | 0.30+ | Production-grade process management with async workers |

### 2.2 Data Layer

| Store | Technology | Version | Role |
|---|---|---|---|
| Primary DB | PostgreSQL | 16 | Tenants, RBAC, Users, Config, Policies, Recommendations |
| ORM | SQLAlchemy | 2.0 (async) | Async queries, migrations, relationship modeling |
| Migrations | Alembic | 1.13+ | Schema versioning, rollback-safe migrations |
| Search / Analytics | Elasticsearch | 8.13 | High-volume DMARC record indexing and SOC querying |
| ES Client | elasticsearch-py (async) | 8.13+ | Async bulk indexing, aggregation queries |
| Cache | Redis | 7.2 | API response cache, session store, rate limiting |
| Object Storage | MinIO (S3-compatible) | Latest | Raw report XML/ZIP archival — immutable forensic store |

### 2.3 Security & Authentication

| Component | Technology | Notes |
|---|---|---|
| Auth | JWT (RS256) | Short-lived access tokens (15min) + refresh tokens (7d) |
| OAuth2 / SSO | python-jose + FastAPI OAuth2 | Supports SSO integration for enterprise tenants |
| RBAC | Custom middleware | Roles: `nextstep_admin`, `client_admin`, `soc_analyst`, `client_user` |
| Tenant Isolation | PostgreSQL Row-Level Security (RLS) | Every query scoped to `tenant_id` via RLS policies |
| Password Hashing | bcrypt (passlib) | Cost factor 12 |
| TLS | Let's Encrypt / Cert-Manager (K8s) | TLS termination at Nginx/Traefik ingress |
| Secrets | HashiCorp Vault / Docker Secrets | No secrets in env files or images |
| API Rate Limiting | slowapi + Redis | Per-tenant and per-endpoint limits |

### 2.4 External Integrations & Enrichment

| Service | Library / Method | Purpose |
|---|---|---|
| IMAP Collection | imaplib / aioimaplib | Poll dedicated mailboxes for DMARC reports |
| DNS Lookup | dnspython (async) | SPF/DKIM/DMARC record validation |
| GeoIP | MaxMind GeoLite2 (mmdb-reader) | Country + city resolution from IP |
| ASN | pyasn + BGP data | Autonomous System Number lookup |
| Threat Intel | AbuseIPDB API / VirusTotal API | IP reputation scoring |
| Email Alerts | aiosmtplib / SendGrid API | Alert notifications to SOC analysts |
| Slack/Teams | httpx (webhook) | ChatOps integration for critical alerts |
| SIEM Push | REST/Syslog (httpx) | CEF/JSON IOC export to SIEM/SOAR |
| Ticketing | Jira/ServiceNow REST API | Automated ticket creation on critical alerts |

### 2.5 DevOps & Infrastructure

| Tool | Technology | Role |
|---|---|---|
| Containerization | Docker 26 + Docker Compose v2 | Service isolation, local dev stack |
| Orchestration | Kubernetes (K8s) 1.30 | Production HA deployment, auto-scaling |
| Ingress | Nginx Ingress Controller | TLS termination, routing, rate limiting |
| CI/CD | GitHub Actions | Lint → Test → Build → Push → Deploy pipeline |
| Container Registry | GitHub Container Registry (GHCR) | Private image storage |
| Monitoring | Prometheus + Grafana | Metrics, dashboards, alerts |
| Log Aggregation | Loki + Grafana | Centralized log shipping from all containers |
| Tracing | OpenTelemetry + Jaeger | Distributed trace across services |
| Health Checks | FastAPI `/health` + K8s probes | Liveness and readiness probes on all services |

---

## 3. Backend Architecture

### 3.1 Service Decomposition

Each service is independently deployable and maps directly to the UML component architecture (Figure 17 & 18).

| Service | Type | Responsibility |
|---|---|---|
| `api-gateway` | FastAPI App | All REST endpoints, WebSocket, JWT auth, RBAC enforcement, rate limiting |
| `collector-worker` | Celery Worker | IMAP polling, attachment download, decompression, raw storage to MinIO |
| `parser-worker` | Celery Worker | XML schema validation, DMARC parsing, normalization, DB + ES indexing |
| `analysis-worker` | Celery Worker | SPF/DKIM/DMARC alignment checks, conformance scoring, anomaly flagging |
| `correlation-worker` | Celery Worker | Cross-event correlation, spoofing pattern detection, incident classification |
| `scoring-worker` | Celery Worker | Risk score computation, threat intel enrichment, GeoIP/ASN resolution |
| `recommendation-worker` | Celery Worker | Policy maturity evaluation, SPF/DKIM fix generation, DMARC progression |
| `alert-service` | Celery Worker | Alert creation, severity routing, channel notification (email/Slack/SIEM) |
| `scheduler` | Celery Beat | Cron-based triggers: IMAP polling, re-scoring, cleanup tasks |
| `flower` | Flower UI | Celery task monitoring and worker health dashboard |

### 3.2 Request Flow — API

```
Client (Frontend / 3rd Party)
  → Nginx Ingress (TLS termination)
  → api-gateway (FastAPI, JWT validation, RBAC)
  → PostgreSQL / Elasticsearch / Redis
  → JSON Response
```

### 3.3 Async Processing Pipeline

Each step publishes a Celery task consumed by the next worker:

| Step | Queue | Worker | Output |
|---|---|---|---|
| 1. Schedule | `beat` | scheduler | Triggers collect task per mailbox config |
| 2. Collect | `collect.queue` | collector-worker | Raw XML/ZIP stored in MinIO, DB record created |
| 3. Parse | `parse.queue` | parser-worker | Structured `DmarcReport` + `ReportRecord` rows in PostgreSQL |
| 4. Analyse | `analysis.queue` | analysis-worker | SPF/DKIM/DMARC results, alignment flags, conformance rate |
| 5. Correlate | `correlate.queue` | correlation-worker | Incident classification, spoofing pattern tags |
| 6. Score | `score.queue` | scoring-worker | Risk score per `Source` entity, threat intel enrichment |
| 7. Recommend | `recommend.queue` | recommendation-worker | Recommendation records persisted, policy stage updated |
| 8. Alert | `alert.queue` | alert-service | Alert created, SOC notified, SIEM push if configured |

---

## 4. Database Design

All tables include `created_at`, `updated_at` timestamps and are scoped with `tenant_id` for multi-tenancy. Row-Level Security (RLS) is enforced at the PostgreSQL level.

### 4.1 Tenant & Identity

```sql
-- tenants
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'free',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('nextstep_admin','client_admin','soc_analyst','client_user')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- memberships (user <-> tenant many-to-many with role override)
CREATE TABLE memberships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, tenant_id)
);

-- audit_logs (immutable)
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    user_id     UUID,
    action      TEXT NOT NULL,
    resource    TEXT NOT NULL,
    metadata    JSONB,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- api_keys
CREATE TABLE api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id),
    key_hash    TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    last_used_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.2 Domain & Mailbox Configuration

```sql
-- domains
CREATE TABLE domains (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    fqdn            TEXT NOT NULL,
    dmarc_policy    TEXT,
    spf_record      TEXT,
    dkim_selectors  TEXT[],
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, fqdn)
);

-- mailbox_configs
CREATE TABLE mailbox_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    domain_id           UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    imap_host           TEXT NOT NULL,
    imap_port           INTEGER NOT NULL DEFAULT 993,
    username            TEXT NOT NULL,
    encrypted_password  TEXT NOT NULL,  -- Fernet encrypted
    folder              TEXT NOT NULL DEFAULT 'INBOX',
    poll_interval_min   INTEGER NOT NULL DEFAULT 15,
    last_polled_at      TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- dmarc_policies
CREATE TABLE dmarc_policies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id   UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    policy      TEXT NOT NULL CHECK (policy IN ('none','quarantine','reject')),
    pct         INTEGER NOT NULL DEFAULT 100,
    rua_uri     TEXT,
    ruf_uri     TEXT,
    version     TEXT NOT NULL DEFAULT 'DMARC1',
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- policy_versions (immutable history)
CREATE TABLE policy_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id   UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    policy_id   UUID REFERENCES dmarc_policies(id),
    changed_by  UUID REFERENCES users(id),
    diff        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.3 Report Ingestion

```sql
-- report_raws (forensic evidence — never delete)
CREATE TABLE report_raws (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    domain_id       UUID REFERENCES domains(id),
    mailbox_config_id UUID REFERENCES mailbox_configs(id),
    s3_key          TEXT NOT NULL,  -- MinIO object path
    filename        TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    size_bytes      BIGINT,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    parse_status    TEXT NOT NULL DEFAULT 'pending'
                    CHECK (parse_status IN ('pending','parsed','failed','skipped'))
);

-- dmarc_reports
CREATE TABLE dmarc_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    domain_id           UUID NOT NULL REFERENCES domains(id),
    raw_id              UUID REFERENCES report_raws(id),
    reporter_org        TEXT NOT NULL,
    report_id           TEXT NOT NULL,
    date_range_begin    TIMESTAMPTZ NOT NULL,
    date_range_end      TIMESTAMPTZ NOT NULL,
    policy_published    JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, report_id)
);

-- report_records (one row per IP/policy combo in a report)
CREATE TABLE report_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id           UUID NOT NULL REFERENCES dmarc_reports(id) ON DELETE CASCADE,
    source_ip           INET NOT NULL,
    source_id           UUID REFERENCES sources(id),
    count               INTEGER NOT NULL DEFAULT 1,
    policy_disposition  TEXT NOT NULL CHECK (policy_disposition IN ('none','quarantine','reject')),
    dkim_aligned        BOOLEAN NOT NULL DEFAULT FALSE,
    spf_aligned         BOOLEAN NOT NULL DEFAULT FALSE,
    header_from         TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- spf_results
CREATE TABLE spf_results (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id   UUID NOT NULL REFERENCES report_records(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL,
    result      TEXT NOT NULL CHECK (result IN ('pass','fail','softfail','neutral','none','temperror','permerror'))
);

-- dkim_results
CREATE TABLE dkim_results (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id   UUID NOT NULL REFERENCES report_records(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL,
    selector    TEXT,
    result      TEXT NOT NULL CHECK (result IN ('pass','fail','none','policy','neutral','temperror','permerror'))
);

-- dmarc_results
CREATE TABLE dmarc_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id       UUID NOT NULL REFERENCES report_records(id) ON DELETE CASCADE,
    result          TEXT NOT NULL CHECK (result IN ('pass','fail')),
    override_reason TEXT
);
```

### 4.4 Source Intelligence

```sql
-- sources
CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    ip              INET NOT NULL,
    asn             INTEGER,
    asn_org         TEXT,
    country_code    CHAR(2),
    city            TEXT,
    is_known_provider BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, ip)
);

-- source_risk_scores (latest score)
CREATE TABLE source_risk_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    score           INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    risk_level      TEXT NOT NULL CHECK (risk_level IN ('low','medium','high','critical')),
    threat_intel_data JSONB,
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_id)  -- one active score per source
);

-- source_score_history (time-series)
CREATE TABLE source_score_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    score       INTEGER NOT NULL,
    risk_level  TEXT NOT NULL,
    scored_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.5 Incidents, Alerts & Recommendations

```sql
-- incidents
CREATE TABLE incidents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    domain_id   UUID NOT NULL REFERENCES domains(id),
    title       TEXT NOT NULL,
    type        TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    status      TEXT NOT NULL DEFAULT 'open',
    source_ids  UUID[],
    evidence    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- alerts
CREATE TABLE alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    incident_id UUID REFERENCES incidents(id),
    domain_id   UUID REFERENCES domains(id),
    severity    TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    status      TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','acknowledged','in_progress','escalated','resolved','false_positive','closed')),
    assigned_to UUID REFERENCES users(id),
    notes       TEXT,
    closed_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- alert_events (full audit trail of status transitions)
CREATE TABLE alert_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id),
    action      TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT,
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- recommendations
CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    domain_id       UUID NOT NULL REFERENCES domains(id),
    category        TEXT NOT NULL CHECK (category IN ('spf','dkim','dmarc_policy','alignment')),
    priority        TEXT NOT NULL CHECK (priority IN ('low','medium','high')),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    suggested_value TEXT,
    current_value   TEXT,
    is_resolved     BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.6 Row-Level Security (RLS)

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_raws ENABLE ROW LEVEL SECURITY;
ALTER TABLE dmarc_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (repeat for each table)
CREATE POLICY tenant_isolation ON domains
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Set tenant context in every DB session (done in SQLAlchemy event listener)
-- SET app.current_tenant_id = '<uuid>';
```

### 4.7 Elasticsearch Index Strategy

```json
// Index: dmarc-records-{tenant_id}
// Shards: 3 | Replicas: 1
{
  "mappings": {
    "properties": {
      "source_ip":       { "type": "ip" },
      "domain":          { "type": "keyword" },
      "date":            { "type": "date" },
      "spf_result":      { "type": "keyword" },
      "dkim_result":     { "type": "keyword" },
      "dmarc_result":    { "type": "keyword" },
      "country_code":    { "type": "keyword" },
      "asn":             { "type": "integer" },
      "asn_org":         { "type": "keyword" },
      "risk_score":      { "type": "integer" },
      "risk_level":      { "type": "keyword" },
      "count":           { "type": "integer" },
      "disposition":     { "type": "keyword" },
      "reporter_org":    { "type": "keyword" },
      "tenant_id":       { "type": "keyword" }
    }
  }
}

// Additional indices:
// dmarc-alerts-{tenant_id}   — shards: 1
// dmarc-sources-{tenant_id}  — shards: 2
```

---

## 5. REST API Design

### 5.1 Conventions

- **Base URL:** `/api/v1/`
- **Auth:** `Authorization: Bearer <jwt>` on all protected routes
- **Tenant scope:** Resolved from JWT `tenant_id` claim. `nextstep_admin` can pass `?tenant_id=` override
- **Pagination:** Cursor-based for large sets (reports, records), offset for small lists
- **Response envelope:** `{ "data": ..., "meta": { "page": ..., "total": ... }, "errors": [] }`
- **OpenAPI spec:** Auto-generated at `/api/docs` and `/api/redoc`

### 5.2 Route Map

| Module | Prefix | Key Endpoints |
|---|---|---|
| Auth | `/auth` | `POST /login` · `POST /refresh` · `POST /logout` · `POST /register-tenant` |
| Tenants | `/tenants` | `GET /me` · `PATCH /me` · `GET /` *(admin)* · `POST /` *(admin)* |
| Users | `/users` | `GET /` · `POST /` · `GET /{id}` · `PATCH /{id}` · `DELETE /{id}` · `POST /{id}/roles` |
| Domains | `/domains` | `GET /` · `POST /` · `GET /{id}` · `PATCH /{id}` · `DELETE /{id}` · `GET /{id}/policy` |
| Mailboxes | `/mailboxes` | `GET /` · `POST /` · `PATCH /{id}` · `DELETE /{id}` · `POST /{id}/test` · `POST /{id}/trigger` |
| Reports | `/reports` | `GET /` *(paginated, filtered)* · `GET /{id}` · `GET /{id}/records` |
| Records | `/records` | `GET /` *(ES-backed, full filter)* · `GET /{id}` · `GET /export` |
| Sources | `/sources` | `GET /` · `GET /{id}` · `GET /{id}/history` · `GET /{id}/records` |
| Alerts | `/alerts` | `GET /` · `GET /{id}` · `PATCH /{id}/status` · `POST /{id}/assign` · `POST /{id}/comment` · `POST /{id}/escalate` |
| Incidents | `/incidents` | `GET /` · `GET /{id}` · `POST /{id}/close` |
| Recommendations | `/recommendations` | `GET /` · `GET /{id}` · `PATCH /{id}/resolve` |
| Analytics | `/analytics` | `GET /conformance` · `GET /risk-trend` · `GET /top-sources` · `GET /volume` · `GET /spf-dkim-breakdown` |
| Integrations | `/integrations` | `GET /` · `POST /` · `PATCH /{id}` · `DELETE /{id}` · `POST /{id}/test` |
| IOC Feed | `/ioc` | `GET /feed` *(JSON/STIX)* · `GET /feed.csv` |
| WebSocket | `/ws` | `ws://.../api/v1/ws/alerts` — real-time alert push |

### 5.3 Pydantic Schema Examples

```python
# app/schemas/auth.py
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# app/schemas/alerts.py
from enum import Enum
from pydantic import BaseModel
from uuid import UUID

class AlertStatus(str, Enum):
    new = "new"
    acknowledged = "acknowledged"
    in_progress = "in_progress"
    escalated = "escalated"
    resolved = "resolved"
    false_positive = "false_positive"
    closed = "closed"

class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    comment: str | None = None

class AlertResponse(BaseModel):
    id: UUID
    severity: str
    status: AlertStatus
    domain_id: UUID
    assigned_to: UUID | None
    created_at: str

    model_config = {"from_attributes": True}
```

---

## 6. Worker Modules — Implementation Detail

### 6.1 Collector Worker

**Queue:** `collect.queue` | **Triggered by:** Celery Beat (default: 15 min per mailbox)

```python
# app/workers/collector.py
from celery import shared_task
from app.services.collector.imap_client import ImapClient
from app.services.collector.storage import upload_to_minio
from app.db.repositories.report_raw import ReportRawRepository

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def collect_reports(self, mailbox_config_id: str):
    """
    1. Connect to IMAP via aioimaplib (TLS, port 993)
    2. Fetch unseen messages with DMARC report attachments
    3. Extract .zip / .gz / .xml attachments
    4. Decompress using zipfile + gzip modules
    5. Upload raw bytes to MinIO: /{tenant_id}/{domain}/{yyyy-mm}/{report_id}.xml
    6. Create ReportRaw DB record (parse_status=PENDING)
    7. Publish parse_report.delay(raw_id) to parse.queue
    8. Duplicate detection via report_id hash (SHA-256)
    """
    ...
```

**Key behaviours:**
- TLS-secured IMAP via `aioimaplib`
- Handles ZIP, GZIP, plain XML attachments
- MinIO path: `/{tenant_id}/{domain_fqdn}/{year-month}/{filename}`
- Idempotent: skips already-processed `report_id`s

### 6.2 Parser Worker

**Queue:** `parse.queue`

```python
# app/workers/parser.py
from celery import shared_task
from app.services.parser.dmarc_parser import DmarcXmlParser
from app.services.parser.normalizer import normalize_provider_quirks

@shared_task(bind=True, max_retries=3)
def parse_report(self, raw_id: str):
    """
    1. Fetch raw XML from MinIO using s3_key from ReportRaw record
    2. Validate XML against DMARC RUA schema (defusedxml — prevents XXE)
    3. Parse: reporter_org, report_id, date_range, policy_published
    4. Normalize provider quirks (Google vs Microsoft vs Proofpoint)
    5. Bulk insert: DmarcReport → ReportRecord → SPFResult, DKIMResult, DmarcResult
    6. Bulk index to Elasticsearch: dmarc-records-{tenant_id}
    7. Update ReportRaw.parse_status = PARSED | FAILED
    8. Publish analysis_report.delay(report_id) to analysis.queue
    """
    ...
```

**Parser handles these provider quirks:**
- Google: wraps records in `<record>` with implicit encoding
- Microsoft: sometimes omits `<policy_override_reasons>`
- Proofpoint: non-standard `<ext_source_ip>` fields

### 6.3 Analysis Worker

**Queue:** `analysis.queue`

```python
# app/workers/analysis.py
from celery import shared_task, chord

@shared_task(bind=True)
def analysis_report(self, report_id: str):
    """
    1. Load all ReportRecords for report_id
    2. For each record:
       - SPF alignment: envelope-from domain vs header-from domain
       - DKIM alignment: d= tag vs header-from domain (strict/relaxed per policy)
       - DMARC result: pass if either SPF or DKIM aligned + passes
    3. Aggregate per domain:
       - total_messages, dmarc_pass, dmarc_fail, conformance_rate
    4. Flag non-conformant sources (DMARC fail + volume > threshold)
    5. Publish in parallel:
       - correlate_report.delay(report_id) → correlate.queue
       - score_sources.delay(source_ids) → score.queue
    """
    ...
```

### 6.4 Correlation Worker

**Queue:** `correlate.queue`

**Detection logic:**
- Repeated auth failures from same IP across N reports in T timeframe
- Volume anomaly: Z-score on rolling 7-day window per source (threshold: Z > 3)
- New source detection: IPs not previously seen sending for this domain
- Cross-domain spoofing: same IP failing DMARC on multiple tenant domains

**Classification thresholds:**

| Score Range | Classification |
|---|---|
| 0 – 30 | Legitimate |
| 31 – 60 | Suspicious |
| 61 – 100 | Potentially Malicious |

```python
# app/workers/correlation.py
@shared_task(bind=True)
def correlate_report(self, report_id: str):
    """
    1. Load records + existing source history
    2. Run detection rules (repeated failures, volume anomaly, new source)
    3. Classify each source: legitimate | suspicious | potentially_malicious
    4. Create Incident if classification >= suspicious AND severity > threshold
    5. Tag ReportRecords with correlation findings
    6. Publish alert_incident.delay(incident_id) if incident created
    """
    ...
```

### 6.5 Scoring Worker

**Queue:** `score.queue`

**Risk score formula (0–100):**

```
score = (
    dmarc_failure_rate * 0.40  +   # 40% weight
    volume_anomaly_score * 0.20 +  # 20% weight
    threat_intel_score * 0.25 +    # 25% weight (AbuseIPDB + VirusTotal)
    geo_asn_risk * 0.15            # 15% weight
)
```

**Risk level thresholds:**
- `low`: score < 40
- `medium`: score 40–70
- `high`: score 71–90
- `critical`: score > 90

**State machine transitions:** `new → observed → scored → [low|medium|high|critical]`

### 6.6 Recommendation Worker

**Queue:** `recommend.queue`

**Checks performed per domain:**

| Check | Logic |
|---|---|
| SPF lookup count | Flag if > 10 DNS lookups (RFC 7208 limit) |
| SPF `+all` | Flag as critical misconfiguration |
| DKIM key rotation | Flag if selector unchanged > 180 days |
| DMARC policy | Suggest `p=none → p=quarantine → p=reject` with `pct` ramping |
| Alignment | Recommend strict alignment if relaxed is causing false positives |

**Maturity score:** 0 (no enforcement) → 100 (full `p=reject`, strict alignment, DKIM + SPF passing)

### 6.7 Alert Service

**Queue:** `alert.queue`

**Alert severity routing:**

| Condition | Severity | Channels |
|---|---|---|
| score > 90 OR critical incident | Critical | Email + Slack + SIEM + Ticket |
| score 71–90 | High | Email + Slack + SIEM |
| score 40–70 | Medium | Email + Slack |
| score < 40 | Low | Dashboard only |

---

## 7. Project Directory Structure

```
dmarc-platform-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── tenants.py
│   │       ├── users.py
│   │       ├── domains.py
│   │       ├── mailboxes.py
│   │       ├── reports.py
│   │       ├── records.py
│   │       ├── sources.py
│   │       ├── alerts.py
│   │       ├── incidents.py
│   │       ├── recommendations.py
│   │       ├── analytics.py
│   │       ├── integrations.py
│   │       ├── ioc.py
│   │       └── ws.py                  # WebSocket endpoint
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── security.py                # JWT RS256 helpers
│   │   ├── rbac.py                    # Role/permission enforcement
│   │   ├── dependencies.py            # FastAPI DI: get_db, get_current_user
│   │   ├── exceptions.py              # Custom HTTP exceptions
│   │   └── middleware.py              # Tenant context, logging, tracing
│   ├── db/
│   │   ├── base.py                    # SQLAlchemy async engine setup
│   │   ├── session.py                 # AsyncSession factory
│   │   ├── models/
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── domain.py
│   │   │   ├── mailbox_config.py
│   │   │   ├── report_raw.py
│   │   │   ├── dmarc_report.py
│   │   │   ├── report_record.py
│   │   │   ├── source.py
│   │   │   ├── alert.py
│   │   │   ├── incident.py
│   │   │   └── recommendation.py
│   │   ├── repositories/              # Data access layer (DAL)
│   │   │   ├── base.py
│   │   │   ├── tenant.py
│   │   │   ├── report.py
│   │   │   ├── source.py
│   │   │   └── alert.py
│   │   └── migrations/                # Alembic migration files
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   ├── services/
│   │   ├── collector/
│   │   │   ├── imap_client.py         # aioimaplib wrapper
│   │   │   ├── decompressor.py        # ZIP/GZIP extraction
│   │   │   └── storage.py             # MinIO upload
│   │   ├── parser/
│   │   │   ├── dmarc_parser.py        # defusedxml DMARC XML parser
│   │   │   ├── normalizer.py          # Provider quirk normalization
│   │   │   └── schema_validator.py    # XSD validation
│   │   ├── analysis/
│   │   │   ├── alignment.py           # SPF/DKIM/DMARC alignment logic
│   │   │   └── conformance.py         # Conformance rate calculator
│   │   ├── correlation/
│   │   │   ├── detector.py            # Anomaly detection rules
│   │   │   └── classifier.py          # Spoofing classification
│   │   ├── scoring/
│   │   │   ├── risk_scorer.py         # Score formula
│   │   │   └── state_machine.py       # Source risk state transitions
│   │   ├── enrichment/
│   │   │   ├── geoip.py               # MaxMind GeoLite2
│   │   │   ├── asn.py                 # pyasn lookup
│   │   │   ├── abuseipdb.py           # AbuseIPDB API client
│   │   │   └── virustotal.py          # VirusTotal API client
│   │   ├── recommendation/
│   │   │   ├── spf_analyzer.py
│   │   │   ├── dkim_analyzer.py
│   │   │   ├── policy_advisor.py
│   │   │   └── maturity_scorer.py
│   │   └── alerting/
│   │       ├── alert_router.py        # Severity → channel routing
│   │       ├── email_notifier.py      # aiosmtplib
│   │       ├── slack_notifier.py      # Webhook
│   │       └── siem_pusher.py         # REST/CEF export
│   ├── workers/
│   │   ├── celery_app.py              # Celery app + queue config
│   │   ├── collector.py
│   │   ├── parser.py
│   │   ├── analysis.py
│   │   ├── correlation.py
│   │   ├── scoring.py
│   │   ├── recommendations.py
│   │   └── alerts.py
│   ├── schemas/                       # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── tenant.py
│   │   ├── domain.py
│   │   ├── report.py
│   │   ├── alert.py
│   │   ├── source.py
│   │   └── analytics.py
│   ├── es/
│   │   ├── client.py                  # Async ES client singleton
│   │   ├── indices.py                 # Index template definitions
│   │   └── queries.py                 # Reusable aggregation queries
│   └── main.py                        # FastAPI app entrypoint
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   └── Dockerfile.worker
│   ├── k8s/
│   │   ├── base/
│   │   │   ├── namespace.yaml
│   │   │   ├── serviceaccount.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── services.yaml
│   │   ├── services/
│   │   │   ├── api-deployment.yaml
│   │   │   ├── worker-collector.yaml
│   │   │   ├── worker-parser.yaml
│   │   │   ├── worker-analysis.yaml
│   │   │   ├── scheduler.yaml
│   │   │   └── hpa.yaml
│   │   ├── monitoring/
│   │   │   ├── prometheus.yaml
│   │   │   ├── grafana.yaml
│   │   │   └── loki.yaml
│   │   ├── overlays/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── kustomization.yaml
│   └── docker-compose.yml
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_alignment.py
│   │   ├── test_scoring.py
│   │   └── test_recommendation.py
│   ├── integration/
│   │   ├── test_api_auth.py
│   │   ├── test_api_reports.py
│   │   ├── test_pipeline.py           # collect → parse → analyse → score
│   │   └── conftest.py                # pytest fixtures: DB, Redis, ES
│   └── e2e/
│       ├── test_full_pipeline.py      # Real DMARC XML scenarios
│       └── fixtures/
│           ├── google_rua_sample.xml
│           └── microsoft_rua_sample.xml
├── scripts/
│   ├── seed_dev_data.py
│   ├── create_es_indices.py
│   └── rotate_encryption_key.py
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint + Test
│       ├── build.yml                  # Docker build + push
│       └── deploy.yml                 # K8s deploy
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── .env.example
├── .pre-commit-config.yaml
└── README.md
```

---

## 8. Docker Compose — Local Dev Stack

```yaml
# infra/docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: dmarc_db
      POSTGRES_USER: dmarc_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dmarc_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis/redis-stack:7.2.0-v9
    ports:
      - "6379:6379"
      - "8001:8001"   # RedisInsight UI
    volumes:
      - redisdata:/data

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -v red"]
      interval: 20s
      timeout: 10s
      retries: 10

  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: '["http://elasticsearch:9200"]'
    depends_on:
      elasticsearch:
        condition: service_healthy

  minio:
    image: minio/minio:latest
    command: server /data --console-address ':9001'
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"   # MinIO Console UI
    volumes:
      - miniodata:/data

  api:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment: &common-env
      DATABASE_URL: postgresql+asyncpg://dmarc_user:${POSTGRES_PASSWORD}@postgres/dmarc_db
      REDIS_URL: redis://redis:6379/0
      ELASTICSEARCH_URL: http://elasticsearch:9200
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET_REPORTS: dmarc-reports
      JWT_PRIVATE_KEY: ${JWT_PRIVATE_KEY}
      JWT_PUBLIC_KEY: ${JWT_PUBLIC_KEY}
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG
      CORS_ORIGINS: "http://localhost:3000,http://localhost:5173"
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ../app:/app/app  # hot reload

  worker-collector:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile.worker
    command: celery -A app.workers.celery_app worker -Q collect.queue -c 2 -n collector@%h --loglevel=info
    environment: *common-env
    depends_on:
      - postgres
      - redis
      - minio

  worker-parser:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile.worker
    command: celery -A app.workers.celery_app worker -Q parse.queue -c 4 -n parser@%h --loglevel=info
    environment: *common-env
    depends_on:
      - postgres
      - redis
      - elasticsearch

  worker-analysis:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile.worker
    command: >
      celery -A app.workers.celery_app worker
      -Q analysis.queue,correlate.queue,score.queue,recommend.queue,alert.queue
      -c 4 -n analysis@%h --loglevel=info
    environment: *common-env
    depends_on:
      - postgres
      - redis
      - elasticsearch

  scheduler:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile.worker
    command: celery -A app.workers.celery_app beat --loglevel=info
    environment: *common-env
    depends_on:
      - redis

  flower:
    image: mher/flower:2.0
    ports:
      - "5555:5555"
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    depends_on:
      - redis

volumes:
  pgdata:
  redisdata:
  esdata:
  miniodata:
```

---

## 9. Environment Variables Reference

Create a `.env` file based on `.env.example`. **Never commit real values.**

```bash
# .env.example

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://dmarc_user:changeme@localhost/dmarc_db
POSTGRES_PASSWORD=changeme

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Elasticsearch ─────────────────────────────────────────────────────────────
ELASTICSEARCH_URL=http://localhost:9200

# ── MinIO / S3 ────────────────────────────────────────────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=changeme
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=changeme
MINIO_BUCKET_REPORTS=dmarc-reports

# ── JWT (RS256) ───────────────────────────────────────────────────────────────
# Generate: openssl genrsa -out private.pem 2048 && openssl rsa -in private.pem -pubout -out public.pem
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Encryption (Fernet) ───────────────────────────────────────────────────────
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here

# ── Threat Intelligence ───────────────────────────────────────────────────────
ABUSEIPDB_API_KEY=
VIRUSTOTAL_API_KEY=
MAXMIND_DB_PATH=/data/GeoLite2-City.mmdb

# ── Email Alerts ──────────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=

# ── Integrations (optional) ───────────────────────────────────────────────────
SLACK_WEBHOOK_URL=
SIEM_ENDPOINT_URL=

# ── App ───────────────────────────────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 10. CI/CD Pipeline

### 10.1 Pipeline Stages

| Stage | Trigger | Steps | Gate |
|---|---|---|---|
| Lint & Format | Every push | `ruff check`, `ruff format --check`, `mypy --strict` | Fail on error |
| Security Scan | Every push | `bandit -r app/`, `pip-audit` | Fail on HIGH severity |
| Unit Tests | Every push | `pytest tests/unit/ --cov=app --cov-report=xml` | ≥ 80% coverage |
| Integration Tests | Every push | Spin up docker-compose.test.yml + `pytest tests/integration/` | All pass |
| Build Images | `main` + release tags | `docker build` per service; tag with Git SHA + semver | Build success |
| Push to GHCR | `main` + release tags | `docker push ghcr.io/nextstep/dmarc-*:sha` | Push success |
| Deploy Staging | `main` branch | `kubectl apply -k infra/k8s/overlays/staging/` | Smoke tests pass |
| Deploy Production | Release tag `v*.*.*` | `kubectl apply -k infra/k8s/overlays/production/` | **Manual approval required** |

### 10.2 GitHub Actions — CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { python-version: "3.12" }
      - run: uv sync --frozen
      - run: uv run ruff check app/
      - run: uv run ruff format --check app/
      - run: uv run mypy app/ --strict

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { python-version: "3.12" }
      - run: uv sync --frozen
      - run: uv run bandit -r app/ -ll
      - run: uv run pip-audit

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_DB: dmarc_test, POSTGRES_USER: test, POSTGRES_PASSWORD: test }
        options: --health-cmd pg_isready
      redis:
        image: redis:7.2-alpine
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { python-version: "3.12" }
      - run: uv sync --frozen
      - run: uv run pytest tests/unit/ tests/integration/ --cov=app --cov-fail-under=80
```

### 10.3 Dockerfile (API Service)

```dockerfile
# infra/docker/Dockerfile.api

# Stage 1: dependency resolver
FROM python:3.12-slim AS deps
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: lean runtime image
FROM python:3.12-slim AS runtime
WORKDIR /app

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=deps /app/.venv /app/.venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

---

## 11. Kubernetes Deployment (Production)

### 11.1 Namespaces

| Namespace | Contents |
|---|---|
| `dmarc-platform` | All application workloads (API, workers, scheduler) |
| `dmarc-data` | PostgreSQL, Redis, Elasticsearch, MinIO (via Helm or Operator) |
| `dmarc-monitoring` | Prometheus, Grafana, Loki, Jaeger |
| `dmarc-ingress` | Nginx Ingress Controller, cert-manager |

### 11.2 Workload Specs

| Workload | Kind | Replicas | CPU Request | Memory Request | CPU Limit | Memory Limit | HPA |
|---|---|---|---|---|---|---|---|
| `api` | Deployment | 2–10 | 250m | 256Mi | 1000m | 1Gi | Yes (CPU 70%) |
| `worker-collector` | Deployment | 1–3 | 100m | 128Mi | 500m | 512Mi | Yes (queue depth) |
| `worker-parser` | Deployment | 2–8 | 250m | 512Mi | 1000m | 2Gi | Yes (queue depth) |
| `worker-analysis` | Deployment | 2–6 | 250m | 512Mi | 1000m | 2Gi | Yes (queue depth) |
| `scheduler` | Deployment | 1 | 100m | 128Mi | 250m | 256Mi | No (singleton) |
| `flower` | Deployment | 1 | 100m | 128Mi | 250m | 256Mi | No |

### 11.3 API Deployment Manifest

```yaml
# infra/k8s/services/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: dmarc-platform
spec:
  replicas: 2
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: dmarc-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: api
          image: ghcr.io/nextstep/dmarc-api:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef: { name: dmarc-config }
            - secretRef: { name: dmarc-secrets }
          resources:
            requests: { cpu: "250m", memory: "256Mi" }
            limits: { cpu: "1000m", memory: "1Gi" }
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet: { path: /health/ready, port: 8000 }
            initialDelaySeconds: 10
            periodSeconds: 5
          securityContext:
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
```

### 11.4 HorizontalPodAutoscaler

```yaml
# infra/k8s/services/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: dmarc-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### 11.5 Ingress

```yaml
# infra/k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dmarc-ingress
  namespace: dmarc-platform
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
    - hosts: [api.yourdomain.com]
      secretName: dmarc-tls
  rules:
    - host: api.yourdomain.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port: { number: 8000 }
```

---

## 12. Observability Stack

### 12.1 Prometheus Metrics

| Metric | Source | Alert Threshold |
|---|---|---|
| `dmarc_reports_ingested_total` | parser-worker | Rate drop > 50% vs 1h avg |
| `dmarc_parse_failures_total` | parser-worker | > 5 failures in 5 min |
| `celery_queue_depth{queue}` | Redis exporter | collect > 100, parse > 500 |
| `dmarc_risk_score_high_sources` | scoring-worker | > 10 new high-risk sources in 1h |
| `dmarc_alerts_created_total` | alert-service | Spike > 3× baseline |
| `api_request_duration_seconds` | FastAPI middleware | p99 > 500ms |
| `api_error_rate` | FastAPI middleware | > 1% 5xx in 5 min |
| `postgres_connections_active` | postgres-exporter | > 80% of `max_connections` |
| `elasticsearch_indexing_latency` | ES exporter | p95 > 1s |

### 12.2 Structured Logging

All services log to stdout in JSON format using `structlog`:

```python
# app/core/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

# Every log entry includes: timestamp, level, service, tenant_id, request_id, message
```

### 12.3 OpenTelemetry Tracing

```python
# app/main.py
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument()
# Trace spans flow: API request → task publish → worker → DB write → ES index
```

---

## 13. Security Hardening

### 13.1 Application Security

| Control | Implementation |
|---|---|
| Multi-tenancy isolation | PostgreSQL RLS on all tables — `tenant_id` enforced at DB level, not app level |
| Credential encryption | Mailbox IMAP passwords encrypted at rest with Fernet (AES-128-CBC) |
| SQL injection prevention | SQLAlchemy parameterized queries only — no raw SQL with user input |
| Input validation | Pydantic v2 strict models on all API endpoints |
| DMARC XML injection | `defusedxml` — prevents XXE attacks in DMARC reports |
| CORS | Strict whitelist via `CORS_ORIGINS` env variable |
| Rate limiting | slowapi: 100 req/min per user, 10/min on auth endpoints |
| JWT security | RS256 asymmetric signing — private key never leaves Vault/K8s Secret |
| API key hashing | SHA-256 hash stored — raw key shown only once at creation |
| Audit logging | All create/update/delete operations logged to `audit_logs` with user + IP |

### 13.2 Infrastructure Security

- All container images built from `python:3.12-slim` — no root user in containers
- Read-only root filesystem on all K8s pods
- Network policies enforce microsegmentation — workers cannot reach internet except enrichment APIs
- Secrets in Vault or Sealed Secrets — never in plaintext ConfigMaps
- Container image scanning: **Trivy** in CI pipeline — fail on CRITICAL CVEs
- Dependency scanning: **pip-audit** in CI pipeline

---

## 14. Implementation Roadmap

### Phase 1 — Foundation (Weeks 1–3)

| Task | Output |
|---|---|
| Repository setup, `pyproject.toml`, `uv.lock`, pre-commit hooks | Repo structure ready |
| PostgreSQL schema design + Alembic migrations (all tables from Section 4) | DB schema v1 deployed |
| Core FastAPI app: config, RBAC middleware, error handlers, `/health` | API gateway skeleton |
| JWT auth endpoints: `POST /auth/login`, `/refresh`, `/logout`, `/register-tenant` | Auth working |
| Docker Compose full stack (PG + Redis + ES + MinIO + API) | Local stack running |
| GitHub Actions: lint + security + test pipeline | CI pipeline green |
| Elasticsearch index templates for all 3 indices | ES indices created |

### Phase 2 — Ingestion Pipeline (Weeks 4–6)

| Task | Output |
|---|---|
| Celery app setup, queue config, beat scheduler | Task infrastructure ready |
| Collector worker: IMAP → decompression → MinIO upload | Reports collected |
| Parser worker: defusedxml parsing → normalization → DB + ES dual-write | Reports parsed |
| Domain + Mailbox CRUD API endpoints | Config API complete |
| Report + Record read API endpoints (paginated, filtered) | Report viewing API live |
| Integration tests: full collect → parse → store pipeline | Pipeline verified |

### Phase 3 — Analysis & Detection (Weeks 7–9)

| Task | Output |
|---|---|
| Analysis worker: SPF/DKIM/DMARC alignment checks, conformance rates | Analysis engine |
| Correlation worker: anomaly detection, spoofing classification, incident creation | Detection engine |
| Scoring worker: risk formula, GeoIP + ASN + AbuseIPDB enrichment | Risk scores live |
| Source entity management + score history API | Source intelligence |
| Analytics API endpoints: conformance, risk trends, top sources, volume | Analytics API |
| Elasticsearch aggregation queries tuned for SOC dashboards | ES queries optimized |

### Phase 4 — Alerting & SOC Integration (Weeks 10–11)

| Task | Output |
|---|---|
| Alert service: creation, severity routing, full lifecycle management | Alert system |
| Alert API: CRUD + status transitions + annotation + assignment | Alert API |
| WebSocket endpoint: real-time alert push to frontend | Live dashboard feed |
| Email + Slack + SIEM notification channels | Notifications live |
| Recommendation worker: maturity evaluation + auto-generation | Recommendations engine |
| IOC feed endpoint: JSON/STIX + CSV export | IOC feed live |

### Phase 5 — Hardening & Deployment (Weeks 12–13)

| Task | Output |
|---|---|
| K8s manifests + Kustomize overlays (staging + production) | K8s ready |
| Prometheus metrics + Grafana dashboards + Loki logging | Observability stack |
| OTel tracing instrumentation across all services | Distributed traces |
| Security audit: OWASP, bandit, Trivy, RLS test suite | Security sign-off |
| Load testing with k6 (target: 1,000 reports/hr sustained) | Performance baseline |
| E2E tests with real DMARC reports (Google + Microsoft XML samples) | E2E verified |
| OpenAPI spec finalization + deployment runbook | Docs complete |

---

## 15. Full Python Dependency List

```toml
# pyproject.toml
[project]
name = "dmarc-backend"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    # ── API Framework ──────────────────────────────────────────────────────────
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "gunicorn>=22",

    # ── Validation ─────────────────────────────────────────────────────────────
    "pydantic>=2.7",
    "pydantic-settings>=2.3",

    # ── Database ───────────────────────────────────────────────────────────────
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",

    # ── Task Queue ─────────────────────────────────────────────────────────────
    "celery[redis]>=5.4",
    "redis>=5.0",

    # ── Search ─────────────────────────────────────────────────────────────────
    "elasticsearch[async]>=8.13",

    # ── Object Storage ─────────────────────────────────────────────────────────
    "minio>=7.2",

    # ── IMAP Collection ────────────────────────────────────────────────────────
    "aioimaplib>=1.1",

    # ── DMARC Parsing ──────────────────────────────────────────────────────────
    "defusedxml>=0.7",           # XXE-safe XML parsing

    # ── DNS ────────────────────────────────────────────────────────────────────
    "dnspython>=2.6",

    # ── Enrichment ─────────────────────────────────────────────────────────────
    "maxminddb>=2.5",            # GeoIP
    "pyasn>=1.6",                # ASN lookups

    # ── Auth & Security ────────────────────────────────────────────────────────
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "slowapi>=0.1",
    "cryptography>=42",          # Fernet for credential encryption

    # ── HTTP Client ────────────────────────────────────────────────────────────
    "httpx>=0.27",               # Threat intel APIs, SIEM push, webhooks

    # ── Email ──────────────────────────────────────────────────────────────────
    "aiosmtplib>=3.0",

    # ── Observability ──────────────────────────────────────────────────────────
    "structlog>=24.2",
    "prometheus-fastapi-instrumentator>=7.0",
    "opentelemetry-sdk>=1.25",
    "opentelemetry-instrumentation-fastapi>=0.46b0",
    "opentelemetry-instrumentation-celery>=0.46b0",
    "opentelemetry-instrumentation-sqlalchemy>=0.46b0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.25",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "httpx>=0.27",               # AsyncClient for FastAPI testing
    "ruff>=0.5",
    "mypy>=1.10",
    "bandit>=1.7",
    "pip-audit>=2.7",
    "factory-boy>=3.3",          # Test data factories
]
```

---

## 16. Future Extensions (Bonus Track)

As defined in section 5 of PFE03-2026-SOC, the following enhancements are planned post-MVP:

### ML Anomaly Detection
- **Stack:** scikit-learn / PyTorch + dedicated Celery ML worker
- **Approach:** Unsupervised clustering (DBSCAN/IsolationForest) of source behaviour; LSTM for time-series volume anomaly detection
- **Replaces:** Threshold-based heuristics in the correlation worker

### BIMI & Brand Indicators
- **Stack:** DNS lookup + VMC validation API
- **Approach:** Validate BIMI DNS records, check VMC certificate chain, surface BIMI readiness score in dashboard

### Forensic RUF Analysis
- **Stack:** RUF parser module + dedicated `dmarc-forensic-{tenant_id}` ES index
- **Approach:** Parse RUF failure reports, extract full email headers and authentication chain, correlate with RUA incidents for deep-dive investigations

### Multi-Tenant SaaS Mode
- **Stack:** Stripe API + tenant provisioning worker
- **Approach:** Self-service tenant onboarding, plan-based feature gating, per-tenant usage metering and billing

---

*End of Backend Deployment Plan — NEXTSTEP · PFE03-2026-SOC · March 2026*
