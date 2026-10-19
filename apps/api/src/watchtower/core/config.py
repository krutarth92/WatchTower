import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

SAFE_AUTH_VALUE = re.compile(r"^[A-Za-z0-9._:@/-]{1,255}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WATCHTOWER_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: SecretStr
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    db_connect_timeout: int = Field(default=3, ge=1, le=30)
    db_pool_timeout: int = Field(default=3, ge=1, le=30)
    db_pool_size: int = Field(default=10, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    db_statement_timeout_ms: int = Field(default=3000, ge=100, le=30000)
    response_gzip_minimum_size: int = Field(default=1024, ge=256, le=1048576)
    response_gzip_compresslevel: int = Field(default=5, ge=1, le=9)
    api_slow_request_ms: int = Field(default=500, ge=50, le=60000)
    max_request_body_bytes: int = Field(default=64 * 1024, ge=1024, le=10 * 1024 * 1024)
    raw_storage_path: Path = Path("storage/raw")
    max_raw_evidence_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    operator_auth_mode: Literal["static", "oidc"] = "static"
    operator_token: SecretStr | None = None
    oidc_issuer: str | None = None
    oidc_jwks_url: str | None = None
    oidc_client_id: str | None = None
    oidc_operator_group: str = "operator"
    oidc_publisher_group: str = "publisher"
    oidc_jwks_cache_seconds: int = Field(default=300, ge=60, le=3600)
    oidc_http_timeout_seconds: int = Field(default=3, ge=1, le=10)
    oidc_clock_skew_seconds: int = Field(default=30, ge=0, le=120)
    trusted_hosts: list[str] = Field(default_factory=list)
    proxy_trusted_hosts: list[str] = Field(default_factory=list)
    ingestion_job_max_attempts: int = Field(default=3, ge=1, le=10)
    ingestion_job_lease_seconds: int = Field(default=300, ge=30, le=3600)
    ingestion_job_timeout_seconds: int = Field(default=240, ge=10, le=3595)
    ingestion_job_retry_base_seconds: int = Field(default=5, ge=1, le=300)
    ingestion_max_active_jobs: int = Field(default=1000, ge=1, le=100000)
    ingestion_recovery_batch_size: int = Field(default=100, ge=1, le=1000)
    ingestion_worker_processes: int = Field(default=1, ge=1, le=16)
    ingestion_worker_threads: int = Field(default=2, ge=1, le=32)
    ingestion_fetch_timeout_seconds: int = Field(default=30, ge=5, le=300)
    ingestion_fetch_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    rag_enabled: bool = False
    rag_context_token_budget: int = Field(default=4000, ge=500, le=32000)
    rag_retrieval_limit: int = Field(default=12, ge=1, le=50)
    rag_max_cosine_distance: float = Field(default=0.45, ge=0, le=2)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("A valid PostgreSQL connection URL is required") from None
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError("Use postgresql+psycopg with a host and database name")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: SecretStr) -> SecretStr:
        parsed = urlsplit(value.get_secret_value())
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise ValueError("Use a redis:// or rediss:// URL with a host")
        return value

    @field_validator("operator_token")
    @classmethod
    def validate_operator_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("WATCHTOWER_OPERATOR_TOKEN must contain at least 32 characters")
        return value

    @field_validator("oidc_issuer", "oidc_jwks_url")
    @classmethod
    def validate_oidc_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "OIDC URLs must be absolute HTTPS URLs without credentials or fragments"
            )
        return value.rstrip("/")

    @field_validator("oidc_client_id", "oidc_operator_group", "oidc_publisher_group")
    @classmethod
    def validate_oidc_value(cls, value: str | None) -> str | None:
        if value is not None and not SAFE_AUTH_VALUE.fullmatch(value):
            raise ValueError("OIDC identifiers must use a safe 1–255 character value")
        return value

    @field_validator("trusted_hosts", "proxy_trusted_hosts")
    @classmethod
    def validate_host_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(
            not item or len(item) > 255 or any(char.isspace() for char in item) for item in cleaned
        ):
            raise ValueError("Trusted host entries must be non-empty and contain no whitespace")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Trusted host entries must be unique")
        return cleaned

    @model_validator(mode="after")
    def validate_security_and_ingestion_settings(self) -> "Settings":
        if self.ingestion_job_timeout_seconds > self.ingestion_job_lease_seconds - 5:
            raise ValueError(
                "WATCHTOWER_INGESTION_JOB_TIMEOUT_SECONDS must leave five seconds "
                "before the lease expires"
            )
        if self.ingestion_fetch_connect_timeout_seconds > self.ingestion_fetch_timeout_seconds:
            raise ValueError(
                "WATCHTOWER_INGESTION_FETCH_CONNECT_TIMEOUT_SECONDS cannot exceed "
                "the total fetch timeout"
            )
        if self.operator_auth_mode == "oidc" and not all(
            (self.oidc_issuer, self.oidc_jwks_url, self.oidc_client_id)
        ):
            raise ValueError(
                "OIDC authentication requires WATCHTOWER_OIDC_ISSUER, "
                "WATCHTOWER_OIDC_JWKS_URL and WATCHTOWER_OIDC_CLIENT_ID"
            )
        if self.oidc_operator_group == self.oidc_publisher_group:
            raise ValueError("OIDC operator and publisher groups must be different")
        if self.environment == "production":
            if self.operator_auth_mode != "oidc":
                raise ValueError("Production requires WATCHTOWER_OPERATOR_AUTH_MODE=oidc")
            if self.operator_token is not None:
                raise ValueError("WATCHTOWER_OPERATOR_TOKEN is forbidden in production")
            if not self.trusted_hosts or "*" in self.trusted_hosts:
                raise ValueError(
                    "Production requires an explicit WATCHTOWER_TRUSTED_HOSTS allowlist"
                )
            if not self.proxy_trusted_hosts or "*" in self.proxy_trusted_hosts:
                raise ValueError(
                    "Production requires an explicit WATCHTOWER_PROXY_TRUSTED_HOSTS allowlist"
                )
        return self
