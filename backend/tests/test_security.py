from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.security import (
    SecurityError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


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


def test_hash_password_and_verify() -> None:
    password = "SuperSecret!123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_create_and_decode_roundtrip() -> None:
    private_key, public_key = _generate_rsa_keypair()
    tenant_id = uuid4()

    token = create_token(
        subject="user@example.com",
        private_key=private_key,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=15),
        tenant_id=tenant_id,
        role="client_admin",
    )

    payload = decode_token(
        token=token,
        public_key=public_key,
        expected_type=TokenType.ACCESS,
    )

    assert payload.sub == "user@example.com"
    assert payload.tenant_id == tenant_id
    assert payload.role == "client_admin"
    assert payload.type == TokenType.ACCESS


def test_decode_token_type_mismatch_raises() -> None:
    private_key, public_key = _generate_rsa_keypair()

    token = create_token(
        subject="user@example.com",
        private_key=private_key,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=7),
    )

    with pytest.raises(SecurityError):
        decode_token(
            token=token,
            public_key=public_key,
            expected_type=TokenType.ACCESS,
        )
