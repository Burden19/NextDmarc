from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityError(Exception):
    pass


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: TokenType
    jti: str
    tenant_id: UUID | None = None
    role: str | None = None


def hash_password(password: str) -> str:
    if not password:
        raise SecurityError("Password cannot be empty")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_token(
    *,
    subject: str,
    private_key: str,
    token_type: TokenType,
    expires_delta: timedelta,
    tenant_id: UUID | None = None,
    role: str | None = None,
    algorithm: str = "RS256",
) -> str:
    if not private_key:
        raise SecurityError("JWT private key is not configured")

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid4()),
    }

    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    if role is not None:
        payload["role"] = role

    return jwt.encode(payload, private_key, algorithm=algorithm)


def decode_token(
    *,
    token: str,
    public_key: str,
    expected_type: TokenType | None = None,
    algorithms: list[str] | None = None,
) -> TokenPayload:
    if not public_key:
        raise SecurityError("JWT public key is not configured")

    allowed_algorithms = algorithms or ["RS256"]

    try:
        payload = jwt.decode(token, public_key, algorithms=allowed_algorithms)
        token_payload = TokenPayload.model_validate(payload)
    except (JWTError, ValidationError) as exc:
        raise SecurityError("Invalid or expired token") from exc

    if expected_type is not None and token_payload.type != expected_type:
        raise SecurityError("Token type mismatch")

    return token_payload
