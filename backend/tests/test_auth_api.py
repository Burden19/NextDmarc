from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.api.v1 import auth as auth_module
from app.main import app
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def _generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


def _fake_settings(**overrides: object) -> SimpleNamespace:
    private_key, public_key = _generate_rsa_keypair()
    defaults: dict[str, object] = {
        "jwt_private_key": private_key,
        "jwt_public_key": public_key,
        "jwt_algorithm": "RS256",
        "jwt_access_token_expire_minutes": 15,
        "jwt_refresh_token_expire_days": 7,
        "auth_cookie_enabled": True,
        "auth_refresh_cookie_name": "nextdmarc_refresh_token",
        "auth_csrf_cookie_name": "nextdmarc_csrf_token",
        "auth_csrf_header_name": "X-CSRF-Token",
        "auth_refresh_cookie_path": "/",
        "auth_csrf_cookie_path": "/",
        "auth_allow_refresh_token_body_fallback": True,
        "cookie_secure": False,
        "cookie_samesite": "lax",
        "cookie_domain": "",
        "login_max_attempts": 3,
        "login_lockout_seconds": 120,
        "login_window_seconds": 60,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_auth_register_login_refresh_logout_flow(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    client = TestClient(app)

    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Acme Corp",
            "admin_email": "admin@acme.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    registration = register_response.json()
    tenant_id = registration["tenant_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@acme.test",
            "password": "Password!123",
            "tenant_id": tenant_id,
        },
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["token_type"] == "bearer"
    assert "access_token" in login_payload
    assert "refresh_token" in login_payload

    first_refresh_token = login_payload["refresh_token"]
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["refresh_token"] != first_refresh_token

    reuse_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert reuse_response.status_code == 401

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refreshed_payload["refresh_token"]},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "logged_out"

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed_payload["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401


def test_auth_login_rejects_invalid_password(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Contoso",
            "admin_email": "admin@contoso.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@contoso.test",
            "password": "WrongPassword",
            "tenant_id": tenant_id,
        },
    )
    assert login_response.status_code == 401
    assert login_response.json()["error"]["code"] == "invalid_credentials"


def test_auth_login_rate_limited_after_repeated_invalid_credentials(
    monkeypatch: MonkeyPatch,
) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Retry Ltd",
            "admin_email": "admin@retry.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant_id"]

    for _ in range(2):
        failed_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@retry.test",
                "password": "WrongPassword",
                "tenant_id": tenant_id,
            },
        )
        assert failed_login.status_code == 401
        assert failed_login.json()["error"]["code"] == "invalid_credentials"

    limited_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@retry.test",
            "password": "WrongPassword",
            "tenant_id": tenant_id,
        },
    )
    assert limited_login.status_code == 429
    assert limited_login.json()["error"]["code"] == "auth_rate_limited"
    assert limited_login.json()["error"]["details"]["scope"] == "login"

    blocked_valid_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@retry.test",
            "password": "Password!123",
            "tenant_id": tenant_id,
        },
    )
    assert blocked_valid_login.status_code == 429
    assert blocked_valid_login.json()["error"]["code"] == "auth_rate_limited"


def test_auth_login_lockout_expires_and_allows_success(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: _fake_settings(login_max_attempts=2, login_lockout_seconds=2),
    )

    now = {"value": datetime(2026, 4, 7, 10, 0, tzinfo=UTC)}
    monkeypatch.setattr(auth_module, "_utcnow", lambda: now["value"])

    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Window Corp",
            "admin_email": "admin@window.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant_id"]

    first_failed = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@window.test",
            "password": "WrongPassword",
            "tenant_id": tenant_id,
        },
    )
    assert first_failed.status_code == 401

    second_failed = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@window.test",
            "password": "WrongPassword",
            "tenant_id": tenant_id,
        },
    )
    assert second_failed.status_code == 429
    assert second_failed.json()["error"]["code"] == "auth_rate_limited"

    now["value"] = now["value"] + timedelta(seconds=3)

    successful_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@window.test",
            "password": "Password!123",
            "tenant_id": tenant_id,
        },
    )
    assert successful_login.status_code == 200
    assert "access_token" in successful_login.json()


def test_auth_register_tenant_is_rate_limited(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: _fake_settings(login_max_attempts=2, login_lockout_seconds=120),
    )

    client = TestClient(app)

    first_register = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Burst One",
            "admin_email": "admin@burst.test",
            "admin_password": "Password!123",
        },
    )
    assert first_register.status_code == 201

    second_register = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Burst Two",
            "admin_email": "admin@burst.test",
            "admin_password": "Password!123",
        },
    )
    assert second_register.status_code == 429
    assert second_register.json()["error"]["code"] == "auth_rate_limited"
    assert second_register.json()["error"]["details"]["scope"] == "register"


def test_auth_login_sets_refresh_and_csrf_cookies(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Cookies Corp",
            "admin_email": "admin@cookies.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@cookies.test",
            "password": "Password!123",
            "tenant_id": tenant_id,
        },
    )
    assert login_response.status_code == 200
    assert login_response.cookies.get("nextdmarc_refresh_token")
    assert login_response.cookies.get("nextdmarc_csrf_token")
    assert login_response.json()["csrf_token"]


def test_auth_refresh_and_logout_accept_cookie_transport(monkeypatch: MonkeyPatch) -> None:
    auth_module.reset_auth_store_for_tests()
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Cookie Transport",
            "admin_email": "admin@transport.test",
            "admin_password": "Password!123",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@transport.test",
            "password": "Password!123",
            "tenant_id": tenant_id,
        },
    )
    assert login_response.status_code == 200

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.cookies.get("nextdmarc_refresh_token")

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={},
    )
    assert logout_response.status_code == 200
    set_cookie_header = logout_response.headers.get("set-cookie", "")
    assert "nextdmarc_refresh_token" in set_cookie_header

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={},
    )
    assert refresh_after_logout.status_code == 401
