"""Authoritative source registration dispatch for approved ingestion jobs."""

from sqlalchemy.orm import Session

from watchtower.db.models import IngestionJobKind, Source
from watchtower.ingestion.cisa_kev import CISA_KEV_DEFINITION
from watchtower.ingestion.fixed_source import FixedSourceDefinition
from watchtower.ingestion.misp_galaxy import MISP_GALAXY_DEFINITION
from watchtower.ingestion.mitre_attack import register_mitre_attack_source
from watchtower.ingestion.publication_feeds import (
    MICROSOFT_FEED,
    THE_HACKER_NEWS_FEED,
    UNIT42_FEED,
)
from watchtower.ingestion.source_registry import SourceRegistry

FIXED_SOURCE_JOBS: dict[IngestionJobKind, FixedSourceDefinition] = {
    IngestionJobKind.MISP_GALAXY_REFRESH: MISP_GALAXY_DEFINITION,
    IngestionJobKind.CISA_KEV_REFRESH: CISA_KEV_DEFINITION,
    IngestionJobKind.MICROSOFT_THREAT_INTELLIGENCE_REFRESH: MICROSOFT_FEED.source,
    IngestionJobKind.UNIT_42_REFRESH: UNIT42_FEED.source,
    IngestionJobKind.THE_HACKER_NEWS_REFRESH: THE_HACKER_NEWS_FEED.source,
}


def register_job_source(session: Session, job_kind: IngestionJobKind) -> Source:
    if job_kind is IngestionJobKind.MITRE_ATTACK_REFRESH:
        return register_mitre_attack_source(session)
    definition = FIXED_SOURCE_JOBS.get(job_kind)
    if definition is None:
        raise ValueError("The ingestion job kind has no approved source registration")
    return SourceRegistry().register(session, definition.registration).source
