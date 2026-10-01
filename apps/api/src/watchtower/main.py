import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dramatiq.brokers.redis import RedisBroker
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware

from watchtower.api.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from watchtower.api.health import router
from watchtower.api.request_id import add_request_id
from watchtower.api.security import RequestBodyLimitMiddleware
from watchtower.api.v1.router import router as v1_router
from watchtower.core.config import Settings
from watchtower.core.logging import configure_logging
from watchtower.db.session import build_engine
from watchtower.ingestion.jobs import IngestionJobService
from watchtower.workers.queue import DramatiqJobQueue


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()  # pyright: ignore[reportCallIssue]

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        logger = logging.getLogger("watchtower.lifecycle")
        engine = build_engine(config)
        ingestion_broker = RedisBroker(url=config.redis_url.get_secret_value())
        app.state.engine = engine
        app.state.settings = config
        app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        app.state.ingestion_job_service = IngestionJobService(
            lease_seconds=config.ingestion_job_lease_seconds,
            retry_base_seconds=config.ingestion_job_retry_base_seconds,
            max_active_jobs=config.ingestion_max_active_jobs,
            recovery_batch_size=config.ingestion_recovery_batch_size,
        )
        app.state.ingestion_job_queue = DramatiqJobQueue(ingestion_broker)
        # A live provider must be explicitly configured before this is populated.
        app.state.research_service = None
        logger.info("application_started")
        try:
            yield
        finally:
            ingestion_broker.close()
            engine.dispose()
            logger.info("application_stopped")

    app = FastAPI(title="WATCHTOWER", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=config.max_request_body_bytes)
    app.add_middleware(
        GZipMiddleware,
        minimum_size=config.response_gzip_minimum_size,
        compresslevel=config.response_gzip_compresslevel,
    )
    app.middleware("http")(add_request_id)
    app.add_exception_handler(ApiError, api_error_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(  # pyright: ignore[reportArgumentType]
        RequestValidationError,
        validation_error_handler,  # pyright: ignore[reportArgumentType]
    )
    app.add_exception_handler(  # pyright: ignore[reportArgumentType]
        StarletteHTTPException,
        http_error_handler,  # pyright: ignore[reportArgumentType]
    )
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.include_router(router)
    app.include_router(v1_router)
    return app
