"""Pydantic contracts for operator integration management."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from watchtower.api.v1.job_schemas import IngestionJobRead, IngestionJobSubmission
from watchtower.db.models import IngestionJobKind
from watchtower.integrations.catalog import (
    EnrichmentDefinition,
    EnrichmentWave,
    IntegrationDefinition,
    IntegrationWave,
)


class IntegrationRead(BaseModel):
    key: str
    name: str
    wave: IntegrationWave
    description: str
    status: Literal["available", "planned", "candidate"]
    implemented: bool
    configured: bool
    can_sync: bool
    job_kind: IngestionJobKind | None
    required_settings: list[str]
    enrichments: list[str]
    latest_job: IngestionJobRead | None


class IntegrationCatalogResponse(BaseModel):
    data: list[IntegrationRead]
    enrichment_roadmap: list["EnrichmentRead"]


class EnrichmentRead(BaseModel):
    key: str
    name: str
    wave: EnrichmentWave
    description: str
    implemented: bool


class IntegrationSyncRequest(IngestionJobSubmission):
    model_config = ConfigDict(extra="forbid")

    integration_key: str = Field(min_length=1, max_length=64)


def integration_read(
    definition: IntegrationDefinition,
    latest_job: IngestionJobRead | None,
) -> IntegrationRead:
    status: Literal["available", "planned", "candidate"]
    if definition.implemented:
        status = "available"
    elif definition.wave == "candidate":
        status = "candidate"
    else:
        status = "planned"
    return IntegrationRead(
        key=definition.key,
        name=definition.name,
        wave=definition.wave,
        description=definition.description,
        status=status,
        implemented=definition.implemented,
        configured=definition.configured,
        can_sync=definition.can_sync,
        job_kind=definition.job_kind,
        required_settings=list(definition.required_settings),
        enrichments=list(definition.enrichments),
        latest_job=latest_job,
    )


def enrichment_read(definition: EnrichmentDefinition) -> EnrichmentRead:
    return EnrichmentRead(
        key=definition.key,
        name=definition.name,
        wave=definition.wave,
        description=definition.description,
        implemented=definition.implemented,
    )
