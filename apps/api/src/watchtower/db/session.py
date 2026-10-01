from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from watchtower.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_use_lifo=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
        },
    )


def get_session(request: Request) -> Iterator[Session]:
    # The caller explicitly commits writes; uncommitted work rolls back on close.
    with request.app.state.session_factory() as session:
        yield session
