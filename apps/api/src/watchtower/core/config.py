from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


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
    operator_token: SecretStr | None = None
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

    @model_validator(mode="after")
    def validate_ingestion_timeouts(self) -> "Settings":
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
        return self
