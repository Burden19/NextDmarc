from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
DEFAULT_DEVELOPMENT_TRUSTED_HOSTS = (
    "localhost",
    "127.0.0.1",
)
DEFAULT_CORS_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
DEFAULT_CORS_ALLOWED_HEADERS = (
    "Authorization",
    "Content-Type",
    "X-Tenant-ID",
    "X-Role",
    "X-Request-ID",
    "X-CSRF-Token",
)

BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "NextDmarc Backend"
    api_prefix: str = "/api/v1"
    environment: Literal["development", "staging", "production"] = "development"
    database_url: str = "postgresql+asyncpg://nextdmarc:nextdmarc@localhost:5432/nextdmarc"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = True
    cors_allowed_methods: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ALLOWED_METHODS)
    )
    cors_allowed_headers: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ALLOWED_HEADERS)
    )
    jwt_algorithm: str = "RS256"
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str = ""
    auth_cookie_enabled: bool = True
    auth_refresh_cookie_name: str = "nextdmarc_refresh_token"
    auth_csrf_cookie_name: str = "nextdmarc_csrf_token"
    auth_csrf_header_name: str = "X-CSRF-Token"
    auth_refresh_cookie_path: str = "/"
    auth_csrf_cookie_path: str = "/"
    auth_allow_refresh_token_body_fallback: bool = True
    login_max_attempts: int = 5
    login_lockout_seconds: int = 900
    login_window_seconds: int = 60
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_timezone: str = "UTC"
    imap_host: str = "localhost"
    imap_port: int = 993
    imap_use_ssl: bool = True
    imap_timeout_seconds: int = 30
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_reports: str = "dmarc-raw-reports"
    minio_secure: bool = False
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_records_index: str = "dmarc-records"
    enrichment_cache_ttl_seconds: int = 900
    enrichment_timeout_seconds: float = 8.0
    enrichment_geoip_base_url: str = "http://ip-api.com"
    enrichment_asn_base_url: str = "http://ip-api.com"
    enrichment_abuseipdb_base_url: str = "https://api.abuseipdb.com"
    enrichment_abuseipdb_api_key: str = ""
    enrichment_virustotal_base_url: str = "https://www.virustotal.com"
    enrichment_virustotal_api_key: str = ""
    alert_route_low: str = "siem"
    alert_route_medium: str = "email"
    alert_route_high: str = "email,slack"
    alert_route_critical: str = "email,slack,siem"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    alert_email_from: str = "alerts@nextdmarc.local"
    alert_email_recipients: list[str] = Field(default_factory=list)
    alert_slack_webhook_url: str = ""
    alert_siem_endpoint: str = ""
    alert_siem_api_key: str = ""
    alert_siem_timeout_seconds: float = 8.0
    alert_realtime_heartbeat_seconds: float = 15.0

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator(
        "cors_origins",
        "trusted_hosts",
        "alert_email_recipients",
        "cors_allowed_methods",
        "cors_allowed_headers",
        mode="before",
    )
    @classmethod
    def parse_csv_list(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = [item.strip() for item in value.split(",") if item.strip()]
            return cleaned
        return [item.strip() for item in value if item.strip()]

    @field_validator("login_max_attempts", "login_lockout_seconds", "login_window_seconds")
    @classmethod
    def validate_positive_security_values(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Security threshold values must be greater than zero")
        return value

    @field_validator(
        "auth_refresh_cookie_name",
        "auth_csrf_cookie_name",
        "auth_csrf_header_name",
        "auth_refresh_cookie_path",
        "auth_csrf_cookie_path",
    )
    @classmethod
    def validate_non_empty_security_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Security string values cannot be empty")
        return cleaned

    @field_validator("auth_refresh_cookie_path", "auth_csrf_cookie_path")
    @classmethod
    def validate_cookie_path_format(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("Cookie paths must start with '/'")
        return value

    @model_validator(mode="after")
    def validate_cookie_security(self) -> "Settings":
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("cookie_secure must be true when cookie_samesite is 'none'")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
