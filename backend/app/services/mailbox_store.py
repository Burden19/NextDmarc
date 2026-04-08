import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from uuid import UUID, uuid4


@dataclass(slots=True)
class MailboxRecord:
    id: UUID
    tenant_id: UUID
    name: str
    username: str
    password: str
    server: str
    mailbox: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class InMemoryMailboxStore:
    def __init__(self) -> None:
        self._records: dict[UUID, MailboxRecord] = {}

    def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        username: str,
        password: str,
        server: str,
        mailbox: str,
    ) -> MailboxRecord:
        now = datetime.now(tz=UTC)
        record = MailboxRecord(
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
        self._records[record.id] = record
        return record

    def list(self, *, tenant_id: UUID) -> list[MailboxRecord]:
        return [item for item in self._records.values() if item.tenant_id == tenant_id]

    def list_enabled(self) -> builtins.list[MailboxRecord]:
        return [item for item in self._records.values() if item.enabled]

    def get(self, *, tenant_id: UUID, mailbox_id: UUID) -> MailboxRecord | None:
        found = self._records.get(mailbox_id)
        if found is None or found.tenant_id != tenant_id:
            return None
        return found

    def update(
        self,
        *,
        tenant_id: UUID,
        mailbox_id: UUID,
        name: str | None,
        username: str | None,
        password: str | None,
        server: str | None,
        mailbox: str | None,
        enabled: bool | None,
    ) -> MailboxRecord | None:
        found = self.get(tenant_id=tenant_id, mailbox_id=mailbox_id)
        if found is None:
            return None

        if name is not None:
            found.name = name
        if username is not None:
            found.username = username
        if password is not None:
            found.password = password
        if server is not None:
            found.server = server
        if mailbox is not None:
            found.mailbox = mailbox
        if enabled is not None:
            found.enabled = enabled
        found.updated_at = datetime.now(tz=UTC)
        return found

    def delete(self, *, tenant_id: UUID, mailbox_id: UUID) -> bool:
        found = self.get(tenant_id=tenant_id, mailbox_id=mailbox_id)
        if found is None:
            return False
        del self._records[mailbox_id]
        return True


@lru_cache(maxsize=1)
def get_mailbox_store() -> InMemoryMailboxStore:
    return InMemoryMailboxStore()


def reset_mailbox_store_for_tests() -> None:
    get_mailbox_store.cache_clear()
