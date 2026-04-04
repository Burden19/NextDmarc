from types import SimpleNamespace

import pytest
from app.services.collector.imap_client import ImapClient


class FakeImapConnection:
    def __init__(self) -> None:
        self.logged_out = False

    async def wait_hello_from_server(self) -> None:
        return None

    async def login(self, username: str, password: str) -> None:
        assert username == "collector@example.test"
        assert password == "secret"

    async def select(self, mailbox: str = "INBOX") -> None:
        assert mailbox == "INBOX"

    async def uid_search(self, charset: str | None, *criteria: str) -> tuple[str, list[bytes]]:
        assert charset is None
        assert criteria == ("UNSEEN",)
        return "OK", [b"10 11"]

    async def uid(self, command: str, *criteria: str) -> tuple[str, list[object]]:
        assert command == "FETCH"
        uid = criteria[0]
        return "OK", [(b"RFC822", f"message-{uid}".encode())]

    async def logout(self) -> None:
        self.logged_out = True


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
