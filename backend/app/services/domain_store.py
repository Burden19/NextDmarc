from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from uuid import UUID, uuid4


@dataclass(slots=True)
class DomainRecord:
    id: UUID
    tenant_id: UUID
    fqdn: str
    status: str
    dmarc_policy: str
    created_at: datetime
    updated_at: datetime


class InMemoryDomainStore:
    def __init__(self) -> None:
        self._records: dict[UUID, DomainRecord] = {}

    def create(self, *, tenant_id: UUID, fqdn: str, dmarc_policy: str) -> DomainRecord:
        now = datetime.now(tz=UTC)
        record = DomainRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            fqdn=fqdn.lower(),
            status="active",
            dmarc_policy=dmarc_policy,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    def list(self, *, tenant_id: UUID) -> list[DomainRecord]:
        return [item for item in self._records.values() if item.tenant_id == tenant_id]

    def get(self, *, tenant_id: UUID, domain_id: UUID) -> DomainRecord | None:
        found = self._records.get(domain_id)
        if found is None or found.tenant_id != tenant_id:
            return None
        return found

    def update(
        self,
        *,
        tenant_id: UUID,
        domain_id: UUID,
        fqdn: str | None,
        status: str | None,
        dmarc_policy: str | None,
    ) -> DomainRecord | None:
        found = self.get(tenant_id=tenant_id, domain_id=domain_id)
        if found is None:
            return None

        if fqdn is not None:
            found.fqdn = fqdn.lower()
        if status is not None:
            found.status = status
        if dmarc_policy is not None:
            found.dmarc_policy = dmarc_policy
        found.updated_at = datetime.now(tz=UTC)
        return found

    def delete(self, *, tenant_id: UUID, domain_id: UUID) -> bool:
        found = self.get(tenant_id=tenant_id, domain_id=domain_id)
        if found is None:
            return False
        del self._records[domain_id]
        return True


@lru_cache(maxsize=1)
def get_domain_store() -> InMemoryDomainStore:
    return InMemoryDomainStore()


def reset_domain_store_for_tests() -> None:
    get_domain_store.cache_clear()
