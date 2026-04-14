from types import SimpleNamespace

import pytest
from app.services.collector.imap_client import ImapClient, resolve_imap_server


class FakeImapConnection:
    def __init__(self) -> None:
        self.logged_out = False

    async def wait_hello_from_server(self) -> None:
        return None

    async def login(self, username: str, password: str) -> tuple[str, list[bytes]]:
        assert username == "collector@example.test"
        assert password == "secret"
        return "OK", [b"LOGIN completed"]

    async def select(self, mailbox: str = "INBOX") -> tuple[str, list[bytes]]:
        assert mailbox == "INBOX"
        return "OK", [b"SELECT completed"]

    async def uid_search(self, *criteria: str, charset: str | None = None) -> tuple[str, list[bytes]]:
        assert charset is None
        assert criteria == ("UNSEEN",)
        return "OK", [b"10 11"]

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        return "OK", [(b"RFC822", f"message-{uid}".encode())]

    async def logout(self) -> None:
        self.logged_out = True


class FailingLoginImapConnection:
    def __init__(self) -> None:
        self.logged_out = False

    async def wait_hello_from_server(self) -> None:
        return None

    async def login(self, username: str, password: str) -> None:
        raise RuntimeError("auth failed")

    async def select(self, mailbox: str = "INBOX") -> None:
        return None

    async def uid_search(self, *criteria: str, charset: str | None = None) -> tuple[str, list[bytes]]:
        return "OK", []

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        return "OK", []

    async def logout(self) -> None:
        self.logged_out = True
        raise RuntimeError("command LOGOUT illegal in state STARTED")


class NonOkLoginImapConnection:
    def __init__(self) -> None:
        self.logged_out = False
        self.select_called = False

    async def wait_hello_from_server(self) -> None:
        return None

    async def login(self, username: str, password: str) -> tuple[str, list[bytes]]:
        return "NO", [b"AUTHENTICATIONFAILED invalid credentials"]

    async def select(self, mailbox: str = "INBOX") -> tuple[str, list[bytes]]:
        self.select_called = True
        return "OK", [b"SELECT completed"]

    async def uid_search(self, *criteria: str, charset: str | None = None) -> tuple[str, list[bytes]]:
        return "OK", []

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        return "OK", []

    async def logout(self) -> None:
        self.logged_out = True


class MultiLineSearchImapConnection(FakeImapConnection):
    async def uid_search(self, *criteria: str, charset: str | None = None) -> tuple[str, list[bytes]]:
        assert charset is None
        assert criteria == ("UNSEEN",)
        return "OK", [b"10 11", b"", b"12", b"SEARCH completed"]


class NonOkSearchImapConnection(FakeImapConnection):
    async def uid_search(self, *criteria: str, charset: str | None = None) -> tuple[str, list[bytes]]:
        assert charset is None
        assert criteria == ("UNSEEN",)
        return "BAD", [b"SEARCH unsupported charset"]


class FetchMetadataWrappedImapConnection(FakeImapConnection):
    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        raw_message = (
            b"From: reports@example.test\r\n"
            b"To: collector@example.test\r\n"
            b"Subject: DMARC\r\n"
            b"\r\n"
            + f"message-{uid}".encode()
        )
        return "OK", [
            f"{uid} FETCH (UID {uid} RFC822 {{{len(raw_message)}}}".encode(),
            raw_message,
            b")",
        ]


class FetchFallbackImapConnection(FakeImapConnection):
    def __init__(self) -> None:
        super().__init__()
        self.message_part_attempts: list[str] = []

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        message_parts = criteria[1]
        self.message_part_attempts.append(message_parts)

        if message_parts in {"(RFC822)", "RFC822"}:
            return "OK", [f"{uid} FETCH (UID {uid} FLAGS (\\Seen))".encode()]

        raw_message = (
            b"From: reports@example.test\r\n"
            b"To: collector@example.test\r\n"
            b"Subject: DMARC\r\n"
            b"\r\n"
            + f"message-{uid}".encode()
        )
        return "OK", [
            f"{uid} FETCH (UID {uid} BODY[] {{{len(raw_message)}}}".encode(),
            raw_message,
            b")",
        ]


class MetadataOnlyFetchImapConnection(FakeImapConnection):
    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        return "OK", [f"{uid} FETCH (UID {uid} FLAGS (\\Seen))".encode()]


class FetchBytearrayPayloadImapConnection(FakeImapConnection):
    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        raw_message = bytearray(
            b"X-Envelope-To: collector@example.test\r\n"
            b"Authentication-Results: mx.example.test; dkim=pass\r\n"
            b"\r\n"
            b"<?xml version=\"1.0\"?><feedback></feedback>"
        )
        return "OK", [
            f"{uid} FETCH (UID {uid} RFC822 {{{len(raw_message)}}}".encode(),
            raw_message,
            b")",
            b"UID FETCH completed",
        ]


@pytest.mark.asyncio
async def test_imap_client_fetches_unseen_messages_and_logs_out() -> None:
    connection = FakeImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert [message.uid for message in messages] == ["10", "11"]
    assert [message.raw_message for message in messages] == [b"message-10", b"message-11"]
    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_test_connection_logs_out() -> None:
    connection = FakeImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    await client.test_connection(
        username="collector@example.test",
        password="secret",
        mailbox="INBOX",
    )

    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_test_connection_preserves_login_error_when_logout_fails() -> None:
    connection = FailingLoginImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    with pytest.raises(RuntimeError, match="auth failed"):
        await client.test_connection(
            username="collector@example.test",
            password="secret",
            mailbox="INBOX",
        )

    assert connection.logged_out is False


@pytest.mark.asyncio
async def test_imap_client_test_connection_fails_fast_on_non_ok_login_response() -> None:
    connection = NonOkLoginImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    with pytest.raises(ValueError, match=r"IMAP LOGIN failed \(NO\)"):
        await client.test_connection(
            username="collector@example.test",
            password="secret",
            mailbox="INBOX",
        )

    assert connection.select_called is False
    assert connection.logged_out is False


@pytest.mark.asyncio
async def test_imap_client_fetches_uids_from_multiline_search_response() -> None:
    connection = MultiLineSearchImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert [message.uid for message in messages] == ["10", "11", "12"]
    assert [message.raw_message for message in messages] == [
        b"message-10",
        b"message-11",
        b"message-12",
    ]
    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_fetch_unseen_messages_fails_on_non_ok_search_response() -> None:
    connection = NonOkSearchImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    with pytest.raises(ValueError, match=r"IMAP UID SEARCH UNSEEN failed \(BAD\)"):
        await client.fetch_unseen_messages(
            username="collector@example.test",
            password="secret",
        )

    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_extracts_raw_message_from_fetch_wrapped_bytes_payload() -> None:
    connection = FetchMetadataWrappedImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert [message.uid for message in messages] == ["10", "11"]
    assert all(message.raw_message.startswith(b"From: reports@example.test") for message in messages)
    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_fetches_with_fallback_when_rfc822_returns_metadata_only() -> None:
    connection = FetchFallbackImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert [message.uid for message in messages] == ["10", "11"]
    assert all(message.raw_message.startswith(b"From: reports@example.test") for message in messages)
    assert "(RFC822)" in connection.message_part_attempts
    assert "(BODY.PEEK[])" in connection.message_part_attempts
    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_skips_messages_when_fetch_returns_only_metadata() -> None:
    connection = MetadataOnlyFetchImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert messages == []
    assert connection.logged_out is True


@pytest.mark.asyncio
async def test_imap_client_extracts_raw_message_from_bytearray_fetch_payload() -> None:
    connection = FetchBytearrayPayloadImapConnection()
    settings = SimpleNamespace(
        imap_use_ssl=True,
        imap_host="localhost",
        imap_port=993,
        imap_timeout_seconds=30,
    )
    client = ImapClient(settings=settings, client_factory=lambda: connection)

    messages = await client.fetch_unseen_messages(
        username="collector@example.test",
        password="secret",
    )

    assert [message.uid for message in messages] == ["10", "11"]
    assert messages[0].raw_message.startswith(b"X-Envelope-To: collector@example.test")
    assert connection.logged_out is True


def test_resolve_imap_server_uses_defaults_for_host_only() -> None:
    host, port, use_ssl = resolve_imap_server(
        server="imap.example.test",
        default_port=993,
        default_use_ssl=True,
    )

    assert host == "imap.example.test"
    assert port == 993
    assert use_ssl is True


def test_resolve_imap_server_supports_scheme_and_port() -> None:
    host, port, use_ssl = resolve_imap_server(
        server="imap://imap.example.test:143",
        default_port=993,
        default_use_ssl=True,
    )

    assert host == "imap.example.test"
    assert port == 143
    assert use_ssl is False


def test_resolve_imap_server_rejects_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="imap:// or imaps://"):
        resolve_imap_server(
            server="https://imap.example.test",
            default_port=993,
            default_use_ssl=True,
        )
