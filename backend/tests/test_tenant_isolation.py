from pathlib import Path
from uuid import uuid4

from app.main import app
from app.services.domain_store import get_domain_store, reset_domain_store_for_tests
from app.services.mailbox_store import get_mailbox_store, reset_mailbox_store_for_tests
from fastapi.testclient import TestClient


def test_domain_cross_tenant_access_is_denied() -> None:
    reset_domain_store_for_tests()
    store = get_domain_store()

    owner_tenant = uuid4()
    other_tenant = uuid4()
    created = store.create(
        tenant_id=owner_tenant,
        fqdn="isolated.example.com",
        dmarc_policy="none",
    )

    client = TestClient(app)
    response = client.get(
        f"/api/v1/domains/{created.id}",
        headers={"X-Tenant-ID": str(other_tenant)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "domain_not_found"


def test_mailbox_cross_tenant_access_is_denied() -> None:
    reset_mailbox_store_for_tests()
    store = get_mailbox_store()

    owner_tenant = uuid4()
    other_tenant = uuid4()
    created = store.create(
        tenant_id=owner_tenant,
        name="primary",
        username="collector@example.test",
        password="secret",
        server="imap.example.test",
        mailbox="INBOX",
    )

    client = TestClient(app)
    response = client.get(
        f"/api/v1/mailboxes/{created.id}",
        headers={"X-Tenant-ID": str(other_tenant)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "mailbox_not_found"


def test_migrations_define_rls_policies_with_tenant_context() -> None:
    migrations_dir = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations" / "versions"
    initial_migration = migrations_dir / "20260325_01_initial_core_tables.py"
    audit_migration = migrations_dir / "20260406_02_alert_triage_audit.py"

    initial_sql = initial_migration.read_text(encoding="utf-8")
    audit_sql = audit_migration.read_text(encoding="utf-8")

    assert "ENABLE ROW LEVEL SECURITY" in initial_sql
    assert "current_setting('app.current_tenant_id', true)::uuid" in initial_sql
    assert '_enable_tenant_rls("users")' in initial_sql
    assert '_enable_tenant_rls("domains")' in initial_sql
    assert '_enable_tenant_rls("dmarc_reports")' in initial_sql
    assert '_enable_tenant_rls("sources")' in initial_sql
    assert '_enable_tenant_rls("alerts")' in initial_sql

    assert "ENABLE ROW LEVEL SECURITY" in audit_sql
    assert "current_setting('app.current_tenant_id', true)::uuid" in audit_sql
    assert '_enable_tenant_rls("alert_audit_logs")' in audit_sql
