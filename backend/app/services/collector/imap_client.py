import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.parse import urlparse

from app.core.config import Settings, get_settings


def resolve_imap_server(
    *,
    server: str,
    default_port: int,
    default_use_ssl: bool,
) -> tuple[str, int, bool]:
    raw_server = server.strip()
    if not raw_server:
        raise ValueError("IMAP server cannot be empty")

    if "://" in raw_server:
        parsed = urlparse(raw_server)
        scheme = parsed.scheme.lower()
        if scheme not in {"imap", "imaps"}:
            raise ValueError("IMAP server scheme must be imap:// or imaps://")
        use_ssl = scheme == "imaps"
    else:
        parsed = urlparse(f"imap://{raw_server}")
        use_ssl = default_use_ssl

    host = parsed.hostname
    if not host:
        raise ValueError("IMAP server host is invalid")

    try:
        port = parsed.port or default_port
    except ValueError as exc:
        raise ValueError("IMAP server port is invalid") from exc

    if port < 1 or port > 65535:
        raise ValueError("IMAP server port must be between 1 and 65535")

    return host, port, use_ssl


class ImapConnection(Protocol):
    async def wait_hello_from_server(self) -> Any: ...

    async def login(self, username: str, password: str) -> Any: ...

    async def select(self, mailbox: str = "INBOX") -> Any: ...

    async def uid_search(self, *criteria: str, charset: str | None = None) -> Any: ...

    async def uid(self, command: str, *criteria: str) -> Any: ...

    async def logout(self) -> Any: ...


@dataclass(slots=True)
class ImapMessage:
    uid: str
    raw_message: bytes


class ImapClient:
    _FETCH_PART_CANDIDATES = (
        "(RFC822)",
        "RFC822",
        "(BODY.PEEK[])",
        "BODY.PEEK[]",
        "(BODY[])",
        "BODY[]",
    )

    _FETCH_METADATA_LINE_RE = re.compile(rb"^\d+\s+fetch\s+\(", re.IGNORECASE)

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[[], ImapConnection] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client_factory = client_factory
        self._imap_host = self._settings.imap_host
        self._imap_port = self._settings.imap_port
        self._imap_use_ssl = self._settings.imap_use_ssl
        self._imap_timeout_seconds = self._settings.imap_timeout_seconds

    def configure_connection(self, *, host: str, port: int, use_ssl: bool) -> None:
        self._imap_host = host
        self._imap_port = port
        self._imap_use_ssl = use_ssl

    async def test_connection(
        self,
        *,
        username: str,
        password: str,
        mailbox: str = "INBOX",
    ) -> None:
        connection = await self._connect()
        logged_in = False
        had_error = False
        try:
            await connection.wait_hello_from_server()
            login_response = await connection.login(username, password)
            self._ensure_ok_response(command="LOGIN", response=login_response)
            logged_in = True
            select_response = await connection.select(mailbox)
            self._ensure_ok_response(command="SELECT", response=select_response)
        except Exception:
            had_error = True
            raise
        finally:
            if logged_in:
                try:
                    await connection.logout()
                except Exception:
                    if not had_error:
                        raise

    async def fetch_unseen_messages(
        self,
        *,
        username: str,
        password: str,
        mailbox: str = "INBOX",
    ) -> list[ImapMessage]:
        connection = await self._connect()
        logged_in = False
        had_error = False
        try:
            await connection.wait_hello_from_server()
            login_response = await connection.login(username, password)
            self._ensure_ok_response(command="LOGIN", response=login_response)
            logged_in = True
            select_response = await connection.select(mailbox)
            self._ensure_ok_response(command="SELECT", response=select_response)

            data = await self._uid_search_unseen(connection)

            message_uids = self._parse_uid_list(data)
            messages: list[ImapMessage] = []
            for uid in message_uids:
                raw = await self._fetch_raw_message_for_uid(connection, uid)
                if raw is not None:
                    messages.append(ImapMessage(uid=uid, raw_message=raw))

            return messages
        except Exception:
            had_error = True
            raise
        finally:
            if logged_in:
                try:
                    await connection.logout()
                except Exception:
                    if not had_error:
                        raise

    async def _connect(self) -> ImapConnection:
        if self._client_factory is not None:
            return self._client_factory()

        from aioimaplib import aioimaplib

        if self._imap_use_ssl:
            return cast(
                ImapConnection,
                aioimaplib.IMAP4_SSL(
                    host=self._imap_host,
                    port=self._imap_port,
                    timeout=self._imap_timeout_seconds,
                ),
            )

        return cast(
            ImapConnection,
            aioimaplib.IMAP4(
                host=self._imap_host,
                port=self._imap_port,
                timeout=self._imap_timeout_seconds,
            ),
        )

    def _parse_uid_list(self, data: list[Any]) -> list[str]:
        if not data:
            return []

        parsed_uids: list[str] = []
        seen_uids: set[str] = set()

        for chunk in data:
            if isinstance(chunk, bytes):
                decoded = chunk.decode("utf-8", errors="ignore").strip()
            else:
                decoded = str(chunk).strip()

            if not decoded:
                continue

            for token in decoded.split():
                if not token.isdigit():
                    continue
                if token in seen_uids:
                    continue
                seen_uids.add(token)
                parsed_uids.append(token)

        return parsed_uids

    def _extract_raw_message(self, payload: list[Any]) -> bytes | None:
        fallback_candidate: bytes | None = None

        for item in payload:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                candidate = bytes(item[1])
                if self._looks_like_fetch_metadata(candidate):
                    continue
                if self._looks_like_message_payload(candidate):
                    return candidate
                if fallback_candidate is None:
                    fallback_candidate = candidate

        byte_items = [bytes(item) for item in payload if isinstance(item, (bytes, bytearray))]
        for item in byte_items:
            if self._looks_like_fetch_metadata(item):
                continue
            if self._looks_like_message_payload(item):
                return item
            if fallback_candidate is None:
                fallback_candidate = item

        return fallback_candidate

    async def _fetch_raw_message_for_uid(self, connection: ImapConnection, uid: str) -> bytes | None:
        for message_parts in self._FETCH_PART_CANDIDATES:
            fetch_status, fetch_data = self._status_and_lines(
                await connection.uid("FETCH", uid, message_parts)
            )
            if fetch_status != "OK":
                continue

            raw = self._extract_raw_message(fetch_data)
            if raw is not None:
                return raw

        return None

    def _looks_like_fetch_metadata(self, payload: bytes) -> bool:
        sample = payload.strip().lower()
        if sample in {b")", b""}:
            return True
        if b"fetch completed" in sample:
            return True
        return bool(self._FETCH_METADATA_LINE_RE.match(sample))

    def _looks_like_message_payload(self, payload: bytes) -> bool:
        head = payload.lstrip()[:512].lower()
        if not head:
            return False
        if head.startswith(b"<?xml") or head.startswith(b"<feedback"):
            return True
        # Common RFC822 headers found at the start of raw email messages.
        return any(
            marker in head
            for marker in [
                b"from:",
                b"to:",
                b"subject:",
                b"date:",
                b"content-type:",
                b"mime-version:",
                b"return-path:",
            ]
        )

    async def _uid_search_unseen(self, connection: ImapConnection) -> list[Any]:
        # aioimaplib changed uid_search signature from (charset, *criteria)
        # to (*criteria, charset=...). Support both for compatibility.
        try:
            response = await connection.uid_search("UNSEEN")
        except TypeError:
            response = await cast(Any, connection).uid_search(None, "UNSEEN")

        self._ensure_ok_response(command="UID SEARCH UNSEEN", response=response)
        _status, lines = self._status_and_lines(response)
        return lines

    def _ensure_ok_response(self, *, command: str, response: Any) -> None:
        status, lines = self._status_and_lines(response)
        if status in (None, "OK"):
            return

        details = self._format_response_lines(lines)
        if details:
            raise ValueError(f"IMAP {command} failed ({status}): {details}")
        raise ValueError(f"IMAP {command} failed ({status})")

    def _status_and_lines(self, response: Any) -> tuple[str | None, list[Any]]:
        if response is None:
            return "OK", []

        if isinstance(response, tuple) and len(response) == 2 and isinstance(response[0], str):
            lines = response[1]
            if isinstance(lines, list):
                return response[0], lines
            if lines is None:
                return response[0], []
            return response[0], [lines]

        result = getattr(response, "result", None)
        if not isinstance(result, str):
            return None, []

        lines = getattr(response, "lines", [])
        if isinstance(lines, list):
            return result, lines
        if lines is None:
            return result, []
        return result, [lines]

    def _format_response_lines(self, lines: list[Any]) -> str:
        rendered: list[str] = []
        for line in lines:
            if isinstance(line, bytes):
                decoded = line.decode("utf-8", errors="ignore").strip()
            else:
                decoded = str(line).strip()
            if decoded:
                rendered.append(decoded)
        return " | ".join(rendered)
