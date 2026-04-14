from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db.session import get_session_factory


@dataclass(slots=True)
class MailboxEntity:
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


class MailboxRepository:
    async def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        username: str,
        password: str,
        server: str,
        mailbox: str,
    ) -> MailboxEntity:
        mailbox_id = uuid4()
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO mailboxes (
                        id,
                        tenant_id,
                        name,
                        username,
                        password,
                        server,
                        mailbox,
                        enabled,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :tenant_id,
                        :name,
                        :username,
                        :password,
                        :server,
                        :mailbox,
                        true,
                        now(),
                        now()
                    )
                    RETURNING id, tenant_id, name, username, password, server, mailbox,
                              enabled, created_at, updated_at
                    """
                ),
                {
                    "id": mailbox_id,
                    "tenant_id": tenant_id,
                    "name": name,
                    "username": username,
                    "password": password,
                    "server": server,
                    "mailbox": mailbox,
                },
            )
            row = result.mappings().first()
            await session.commit()

        if row is None:
            raise RuntimeError("Failed to create mailbox")
        return self._map_row(dict(row))

    async def list(self, *, tenant_id: UUID) -> list[MailboxEntity]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, name, username, password, server, mailbox,
                           enabled, created_at, updated_at
                    FROM mailboxes
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    """
                ),
                {"tenant_id": tenant_id},
            )
            rows = result.mappings().all()

        return [self._map_row(dict(row)) for row in rows]

    async def list_enabled(self) -> list[MailboxEntity]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, name, username, password, server, mailbox,
                           enabled, created_at, updated_at
                    FROM mailboxes
                    WHERE enabled = true
                    ORDER BY created_at ASC
                    """
                )
            )
            rows = result.mappings().all()

        return [self._map_row(dict(row)) for row in rows]

    async def get(self, *, tenant_id: UUID, mailbox_id: UUID) -> MailboxEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, name, username, password, server, mailbox,
                           enabled, created_at, updated_at
                    FROM mailboxes
                    WHERE tenant_id = :tenant_id AND id = :mailbox_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "mailbox_id": mailbox_id},
            )
            row = result.mappings().first()

        if row is None:
            return None
        return self._map_row(dict(row))

    async def update(
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
    ) -> MailboxEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE mailboxes
                    SET
                        name = COALESCE(:name, name),
                        username = COALESCE(:username, username),
                        password = COALESCE(:password, password),
                        server = COALESCE(:server, server),
                        mailbox = COALESCE(:mailbox, mailbox),
                        enabled = COALESCE(:enabled, enabled),
                        updated_at = now()
                    WHERE tenant_id = :tenant_id AND id = :mailbox_id
                    RETURNING id, tenant_id, name, username, password, server, mailbox,
                              enabled, created_at, updated_at
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "mailbox_id": mailbox_id,
                    "name": name,
                    "username": username,
                    "password": password,
                    "server": server,
                    "mailbox": mailbox,
                    "enabled": enabled,
                },
            )
            row = result.mappings().first()
            await session.commit()

        if row is None:
            return None
        return self._map_row(dict(row))

    async def delete(self, *, tenant_id: UUID, mailbox_id: UUID) -> bool:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM mailboxes
                    WHERE tenant_id = :tenant_id AND id = :mailbox_id
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "mailbox_id": mailbox_id},
            )
            deleted = result.scalar_one_or_none()
            await session.commit()

        return deleted is not None

    def _map_row(self, row: dict[str, object]) -> MailboxEntity:
        return MailboxEntity(
            id=UUID(str(row["id"])),
            tenant_id=UUID(str(row["tenant_id"])),
            name=str(row["name"]),
            username=str(row["username"]),
            password=str(row["password"]),
            server=str(row["server"]),
            mailbox=str(row["mailbox"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@lru_cache(maxsize=1)
def get_mailbox_repository() -> MailboxRepository:
    return MailboxRepository()


def reset_mailbox_repository_for_tests() -> None:
    get_mailbox_repository.cache_clear()