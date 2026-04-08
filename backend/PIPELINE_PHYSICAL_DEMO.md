# NextDmarc Backend Physical Demo Runbook

This runbook is designed for supervisor meetings where you need to show concrete backend activity before full release readiness.

## 1) What to show live

1. Stage-by-stage pipeline proof using targeted worker tests.
2. API behavior in Postman using real requests and responses.
3. Current completion boundary (implemented pipeline vs pending release gates).

## 2) Live pipeline proof (physical activity)

From repository root:

```powershell
Set-Location backend
./scripts/pipeline-live-demo.ps1
```

This command runs each pipeline stage separately and produces:

1. Report: backend/artifacts/pipeline-live-demo-latest.md
2. Logs: backend/artifacts/pipeline-live-demo-latest.log

Stages covered:

1. Collect
2. Parse
3. Analyze
4. Correlate
5. Score
6. Recommend
7. Alert
8. Collect-Parse integration handoff

If you only need the stage map (no test execution):

```powershell
Set-Location backend
./scripts/pipeline-live-demo.ps1 -SkipTests
```

## 3) What each backend stage does

1. Collect
- Pulls unseen mailbox messages.
- Prevents duplicate processing using idempotency keys.
- Stores attachments or message payloads in object storage.

2. Parse
- Reads stored DMARC object bytes.
- Parses and normalizes report data.
- Persists report metadata and indexes report records.

3. Analyze
- Computes SPF, DKIM, and DMARC conformance metrics.
- Produces summary payload for downstream processing.

4. Correlate
- Detects suspicious signals (for example anomalies or repeated failures).
- Classifies severity and creates incidents.
- Enqueues alert dispatch for created incidents.

5. Score
- Calculates tenant risk score and risk state.
- Stores current score and appends score history.

6. Recommend
- Generates actionable remediation recommendations.
- Computes maturity score and maturity level.
- Stores current recommendation set and history.

7. Alert
- Creates and dispatches alerts to mapped channels.
- Writes alert audit events.
- Publishes realtime events for websocket consumers.

8. API consumption layer
- Exposes domains, reports, records, analytics, incidents, alerts, integrations, recommendations, and IOC feeds.

## 4) API check in Postman (quick path)

Use the provided collection file:

1. Import backend/postman/NextDmarc-Quick-Check.postman_collection.json
2. Set collection variable baseUrl to http://localhost:8000
3. Run requests in order (folder order is already arranged)

## 5) Manual Postman steps (if you prefer to build requests yourself)

Base URL:

- http://localhost:8000

Common headers for tenant-scoped routes:

- X-Tenant-ID: any UUID, or the tenant_id returned by register-tenant
- X-Role: client_admin

Request order:

1. GET /health
2. POST /api/v1/auth/register-tenant
3. POST /api/v1/auth/login
4. POST /api/v1/domains
5. GET /api/v1/domains
6. POST /api/v1/mailboxes
7. POST /api/v1/mailboxes/{mailbox_id}/trigger-collect
8. GET /api/v1/reports
9. GET /api/v1/analytics/conformance

Register-tenant body:

```json
{
  "tenant_name": "Acme Corp",
  "admin_email": "admin@acme.test",
  "admin_password": "Password!123"
}
```

Login body:

```json
{
  "email": "admin@acme.test",
  "password": "Password!123",
  "tenant_id": "{{tenantId}}"
}
```

Create domain body:

```json
{
  "fqdn": "example.com",
  "dmarc_policy": "none"
}
```

Create mailbox body:

```json
{
  "name": "Primary",
  "username": "collector@example.test",
  "password": "secret",
  "server": "imap.example.test",
  "mailbox": "INBOX"
}
```

## 6) Important troubleshooting note for auth endpoints

If auth endpoints return 503 with message about missing JWT keys, configure JWT_PRIVATE_KEY and JWT_PUBLIC_KEY in backend environment settings before retrying auth calls.

## 7) Suggested meeting narrative (2 minutes)

1. "I will run stage-by-stage proof now so each pipeline part is visible."
2. "Now I will call the same backend through Postman to show API behavior."
3. "Finally, here are the remaining release-readiness checks still pending in Phase 5."