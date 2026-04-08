from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from app.core.config import Settings, get_settings


class ImapConnection(Protocol):
    async def wait_hello_from_server(self) -> Any: ...

    async def login(self, username: str, password: str) -> Any: ...

    async def select(self, mailbox: str = "INBOX") -> Any: ...

    async def uid_search(self, charset: str | None, *criteria: str) -> tuple[str, list[bytes]]: ...

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[Any]]: ...

    async def logout(self) -> Any: ...


@dataclass(slots=True)
class ImapMessage:
    uid: str
    raw_message: bytes


class ImapClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[[], ImapConnection] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client_factory = client_factory

    async def fetch_unseen_messages(
        self,
        *,
        username: str,
        password: str,
        mailbox: str = "INBOX",
    ) -> list[ImapMessage]:
        connection = await self._connect()
        try:
            await connection.wait_hello_from_server()
            await connection.login(username, password)
            await connection.select(mailbox)

            status, data = await connection.uid_search(None, "UNSEEN")
            if status != "OK":
                return []

            message_uids = self._parse_uid_list(data)
            messages: list[ImapMessage] = []
            for uid in message_uids:
                fetch_status, fetch_data = await connection.uid("FETCH", uid, "(RFC822)")
                if fetch_status != "OK":
                    continue

                raw = self._extract_raw_message(fetch_data)
                if raw is not None:
                    messages.append(ImapMessage(uid=uid, raw_message=raw))

            return messages
        finally:
            await connection.logout()

    async def _connect(self) -> ImapConnection:
        if self._client_factory is not None:
            return self._client_factory()

        from aioimaplib import aioimaplib

        if self._settings.imap_use_ssl:
            return cast(
                ImapConnection,
                aioimaplib.IMAP4_SSL(
                    host=self._settings.imap_host,
                    port=self._settings.imap_port,
                    timeout=self._settings.imap_timeout_seconds,
                ),
            )

        return cast(
            ImapConnection,
            aioimaplib.IMAP4(
                host=self._settings.imap_host,
                port=self._settings.imap_port,
                timeout=self._settings.imap_timeout_seconds,
            ),
        )

    def _parse_uid_list(self, data: list[bytes]) -> list[str]:
        if not data:
            return []

        first_chunk = data[0].decode("utf-8", errors="ignore").strip()
        if not first_chunk:
            return []

        return [uid for uid in first_chunk.split(" ") if uid]

    def _extract_raw_message(self, payload: list[Any]) -> bytes | None:
        for item in payload:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
                return item[1]
            if isinstance(item, bytes):
                return item
        return None
