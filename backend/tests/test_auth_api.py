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


def _fake_settings() -> SimpleNamespace:
    private_key, public_key = _generate_rsa_keypair()
    return SimpleNamespace(
        jwt_private_key=private_key,
        jwt_public_key=public_key,
        jwt_algorithm="RS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
    )


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
