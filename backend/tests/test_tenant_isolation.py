from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.api.v1 import mailboxes as mailbox_module
from app.main import app
from app.repositories.mailbox_repository import MailboxEntity
from app.services.domain_store import get_domain_store, reset_domain_store_for_tests
from fastapi.testclient import TestClient


class _FakeMailboxRepository:
    def __init__(self) -> None:
        self._records: dict[str, MailboxEntity] = {}

    async def create(
        self,
        *,
        tenant_id,
        name: str,
        username: str,
        password: str,
        server: str,
        mailbox: str,
    ) -> MailboxEntity:
        now = datetime.now(tz=UTC)
        record = MailboxEntity(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            username=username,
            password=password,
            server=server,
            mailbox=mailbox,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._records[str(record.id)] = record
        return record

    async def get(self, *, tenant_id, mailbox_id) -> MailboxEntity | None:
        found = self._records.get(str(mailbox_id))
        if found is None or found.tenant_id != tenant_id:
            return None
        return found


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


def test_mailbox_cross_tenant_access_is_denied(monkeypatch) -> None:
    mailbox_repository = _FakeMailboxRepository()
    monkeypatch.setattr(mailbox_module, "get_mailbox_repository", lambda: mailbox_repository)

    owner_tenant = uuid4()
    other_tenant = uuid4()

    client = TestClient(app)
    create_response = client.post(
        "/api/v1/mailboxes",
        headers={"X-Tenant-ID": str(owner_tenant)},
        json={
            "name": "primary",
            "username": "collector@example.test",
            "password": "secret",
            "server": "imap.example.test",
            "mailbox": "INBOX",
        },
    )
    assert create_response.status_code == 201
    mailbox_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/mailboxes/{mailbox_id}",
        headers={"X-Tenant-ID": str(other_tenant)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "mailbox_not_found"


def test_migrations_define_rls_policies_with_tenant_context() -> None:
    migrations_dir = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations" / "versions"
    initial_migration = migrations_dir / "20260325_01_initial_core_tables.py"
    audit_migration = migrations_dir / "20260406_02_alert_triage_audit.py"
    mailbox_migration = migrations_dir / "20260413_03_mailboxes_table.py"

    initial_sql = initial_migration.read_text(encoding="utf-8")
    audit_sql = audit_migration.read_text(encoding="utf-8")
    mailbox_sql = mailbox_migration.read_text(encoding="utf-8")

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

    assert "ENABLE ROW LEVEL SECURITY" in mailbox_sql
    assert "current_setting('app.current_tenant_id', true)::uuid" in mailbox_sql
    assert '_enable_tenant_rls("mailboxes")' in mailbox_sql
