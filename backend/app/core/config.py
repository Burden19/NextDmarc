from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NextDmarc Backend"
    api_prefix: str = "/api/v1"
    environment: Literal["development", "staging", "production"] = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nextdmarc"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(default_factory=lambda: ["*"])
    jwt_algorithm: str = "RS256"
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            cleaned = [item.strip() for item in value.split(",") if item.strip()]
            return cleaned
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
