# Supervisor Demo Guide (Backend In Progress)

This guide helps you present concrete progress to your supervisor even before full backend completion.

## 1) Goal of this demo

Show objective evidence of delivery using:

1. A repeatable verification test slice.
2. A generated progress snapshot report.
3. Clear scope boundaries for what is done vs what is still in progress.

## 2) Run the supervisor snapshot

From repository root:

```powershell
Set-Location backend
./scripts/supervisor-demo.ps1
```

This command will:

1. Run a curated backend showcase test suite.
2. Generate a report at `backend/artifacts/supervisor-progress-latest.md`.
3. Save raw pytest output in `backend/artifacts/supervisor-progress-latest.log`.

If you need to regenerate the report quickly without rerunning tests:

```powershell
Set-Location backend
./scripts/supervisor-demo.ps1 -SkipTests
```

## 3) Suggested 5-minute presentation flow

1. Open the generated snapshot report and show date/time, branch, and commit.
2. Highlight the test result summary (pass count + runtime).
3. Show the phase completion table from the backend execution checklist.
4. Explain representative implemented modules:
   - health/readiness
   - auth + RBAC
   - domains/reports APIs
   - analytics endpoints
   - alert triage + websocket flow
5. Close with the pending Phase 5 readiness items and expected next delivery checkpoint.

## 4) Talking points to keep the message clear

Use this sentence structure:

1. "Here is what is objectively working now (tests + report evidence)."
2. "Here is what is integrated but still being hardened for release."
3. "Here are the exact remaining validation gates before sign-off."

This frames progress as controlled engineering delivery, not partial completion.

## 5) Optional live proof during meeting

If you want to demonstrate repeatability live, run:

```powershell
Set-Location backend
c:/PFE/UML/NextDmarc/.venv/Scripts/python.exe -m pytest tests/test_health.py tests/test_auth_api.py tests/test_domains_api.py tests/test_reports_records_api.py tests/test_analytics_api.py tests/test_alerts_api.py tests/test_alerts_websocket_api.py tests/test_rbac.py --no-cov -q
```

If this command passes live, it strongly reinforces that current progress is stable and reproducible.