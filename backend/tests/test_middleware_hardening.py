import app.main as main_module
import pytest
from app.core.config import Settings, get_settings
from app.main import app, create_app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


class _FakeRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.events: list[str] = []

    def incr(self, key: str) -> int:
        next_value = self.counters.get(key, 0) + 1
        self.counters[key] = next_value
        return next_value

    def expire(self, key: str, ttl: int) -> None:
        _ = key
        _ = ttl

    def rpush(self, key: str, value: str) -> None:
        _ = key
        self.events.append(value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        _ = key
        _ = start
        _ = end

    def close(self) -> None:
        return None


class _RedisFactory:
    def __init__(self, client: _FakeRedis) -> None:
        self.client = client

    def from_url(self, url: str, decode_responses: bool = True) -> _FakeRedis:
        _ = url
        _ = decode_responses
        return self.client


def test_write_operations_are_rate_limited_and_audited(monkeypatch: MonkeyPatch) -> None:
    fake_redis = _FakeRedis()
    factory = _RedisFactory(fake_redis)

    from app.core import middleware as middleware_module

    monkeypatch.setattr(middleware_module, "Redis", factory)

    settings = get_settings()
    _ = settings

    client = TestClient(app)
    headers = {
        "X-Tenant-ID": "00000000-0000-0000-0000-000000000001",
        "X-Role": "client_admin",
    }

    # First request should pass middleware rate limit path.
    first = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={"name": "x", "kind": "slack", "config": {"webhook_url": "https://x"}},
    )
    assert first.status_code in {201, 422}

    # Force limiter over threshold.
    for key in list(fake_redis.counters.keys()):
        fake_redis.counters[key] = 120

    second = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={"name": "x", "kind": "slack", "config": {"webhook_url": "https://x"}},
    )
    assert second.status_code == 429

    # At least one write audit event should be recorded.
    assert any("write_operation" in event for event in fake_redis.events)


def test_create_app_rejects_staging_wildcard_cors(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(
        environment="staging",
        cors_origins=["*"],
        trusted_hosts=["api.nextdmarc.local"],
        cookie_secure=True,
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="wildcard"):
        create_app()


def test_create_app_rejects_staging_http_origin(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(
        environment="staging",
        cors_origins=["http://frontend.nextdmarc.local"],
        trusted_hosts=["api.nextdmarc.local"],
        cookie_secure=True,
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="https://"):
        create_app()


def test_create_app_rejects_staging_wildcard_trusted_hosts(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = Settings(
        environment="staging",
        cors_origins=["https://frontend.nextdmarc.local"],
        trusted_hosts=["*"],
        cookie_secure=True,
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="wildcard"):
        create_app()


def test_create_app_rejects_production_without_secure_cookie(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = Settings(
        environment="production",
        cors_origins=["https://frontend.nextdmarc.local"],
        trusted_hosts=["api.nextdmarc.local"],
        cookie_secure=False,
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="cookie_secure"):
        create_app()


def test_create_app_uses_development_security_defaults(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(
        environment="development",
        cors_origins=[],
        trusted_hosts=[],
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    configured_app = create_app()

    cors_middleware = next(
        middleware
        for middleware in configured_app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert "http://localhost:3000" in cors_middleware.kwargs["allow_origins"]
    assert "http://127.0.0.1:3000" in cors_middleware.kwargs["allow_origins"]

    trusted_host_middleware = next(
        middleware
        for middleware in configured_app.user_middleware
        if middleware.cls.__name__ == "TrustedHostMiddleware"
    )
    assert "localhost" in trusted_host_middleware.kwargs["allowed_hosts"]
    assert "127.0.0.1" in trusted_host_middleware.kwargs["allowed_hosts"]


def test_write_requests_with_refresh_cookie_require_csrf_header() -> None:
    client = TestClient(app)
    client.cookies.set("nextdmarc_refresh_token", "refresh-token")
    client.cookies.set("nextdmarc_csrf_token", "csrf-token")

    headers = {
        "X-Tenant-ID": "00000000-0000-0000-0000-000000000001",
        "X-Role": "client_admin",
    }
    response = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={"name": "x", "kind": "slack", "config": {"webhook_url": "https://x"}},
    )

    assert response.status_code == 403
    assert response.text == "csrf_invalid"


def test_write_requests_with_matching_csrf_header_pass_middleware() -> None:
    client = TestClient(app)
    client.cookies.set("nextdmarc_refresh_token", "refresh-token")
    client.cookies.set("nextdmarc_csrf_token", "csrf-token")

    headers = {
        "X-Tenant-ID": "00000000-0000-0000-0000-000000000001",
        "X-Role": "client_admin",
        "X-CSRF-Token": "csrf-token",
    }
    response = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={"name": "x", "kind": "slack", "config": {"webhook_url": "https://x"}},
    )

    assert response.status_code in {201, 422}


def test_security_headers_are_present_on_responses() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_header_is_added_for_staging_environment(monkeypatch: MonkeyPatch) -> None:
    from app.core import middleware as middleware_module

    settings = Settings(
        environment="staging",
        cookie_secure=True,
        cors_origins=["https://frontend.nextdmarc.local"],
        trusted_hosts=["api.nextdmarc.local"],
    )
    monkeypatch.setattr(middleware_module, "get_settings", lambda: settings)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
