"""Versioned public API router."""

from fastapi import APIRouter

from watchtower.api.v1.actors import router as actors_router
from watchtower.api.v1.advisories import operator_router as advisory_operator_router
from watchtower.api.v1.advisories import public_router as advisory_public_router
from watchtower.api.v1.artifacts import router as artifacts_router
from watchtower.api.v1.ingestion import router as ingestion_router
from watchtower.api.v1.research import router as research_router
from watchtower.api.v1.search import router as search_router
from watchtower.api.v1.stix_exports import router as stix_exports_router

router = APIRouter()
router.include_router(advisory_public_router)
router.include_router(advisory_operator_router)
router.include_router(artifacts_router)
router.include_router(actors_router)
router.include_router(ingestion_router)
router.include_router(research_router)
router.include_router(search_router)
router.include_router(stix_exports_router)
