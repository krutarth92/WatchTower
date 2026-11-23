"""Approved ingestion processors used by Dramatiq jobs."""

from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import IngestionJobKind
from watchtower.ingestion.cisa_kev import (
    CISA_KEV_DEFINITION,
    CisaKevNormalizer,
    CisaKevObservationRepository,
    CisaKevPayloadParser,
    CisaKevRecordParser,
)
from watchtower.ingestion.connector import ConnectorRunResult, ConnectorRunStatus
from watchtower.ingestion.fixed_source import (
    FixedSourceConnector,
    FixedSourceDefinition,
    FixedSourceFetcher,
)
from watchtower.ingestion.job_runner import (
    PermanentIngestionError,
    RetryableIngestionError,
)
from watchtower.ingestion.jobs import JobClaim
from watchtower.ingestion.misp_galaxy import (
    MISP_GALAXY_DEFINITION,
    MispActorNormalizer,
    MispActorObservationRepository,
    MispActorRecordParser,
    MispGalaxyPayloadParser,
)
from watchtower.ingestion.mitre_attack import MitreAttackConnector, MitreAttackFetcher
from watchtower.ingestion.mitre_attack_normalization import (
    MitreAttackObservationNormalizer,
    MitreAttackRecordParser,
)
from watchtower.ingestion.normalization import NormalizationPipeline
from watchtower.ingestion.publication_feeds import (
    MICROSOFT_FEED,
    THE_HACKER_NEWS_FEED,
    UNIT42_FEED,
    PublicationNormalizer,
    PublicationObservationRepository,
    PublicationRecordParser,
    RssPublicationPayloadParser,
)
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.storage.factory import build_object_store


class ApprovedIngestionProcessor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def process(self, session: Session, claim: JobClaim) -> UUID | None:
        store = build_object_store(self._settings)
        intake = RawEvidenceIntake(store, self._settings.max_raw_evidence_bytes)
        if claim.job_kind is IngestionJobKind.MITRE_ATTACK_REFRESH:
            return self._process_mitre(session, claim, intake)
        if claim.job_kind is IngestionJobKind.MISP_GALAXY_REFRESH:
            pipeline = NormalizationPipeline(
                session,
                MispActorRecordParser(),
                MispActorNormalizer(),
                MispActorObservationRepository(),
            )
            connector = FixedSourceConnector(
                MISP_GALAXY_DEFINITION, MispGalaxyPayloadParser(), intake, pipeline
            )
            return self._run_fixed(session, claim, connector, MISP_GALAXY_DEFINITION)
        if claim.job_kind is IngestionJobKind.CISA_KEV_REFRESH:
            pipeline = NormalizationPipeline(
                session,
                CisaKevRecordParser(),
                CisaKevNormalizer(),
                CisaKevObservationRepository(),
            )
            connector = FixedSourceConnector(
                CISA_KEV_DEFINITION, CisaKevPayloadParser(), intake, pipeline
            )
            return self._run_fixed(session, claim, connector, CISA_KEV_DEFINITION)
        publication_feed = {
            IngestionJobKind.MICROSOFT_THREAT_INTELLIGENCE_REFRESH: MICROSOFT_FEED,
            IngestionJobKind.UNIT_42_REFRESH: UNIT42_FEED,
            IngestionJobKind.THE_HACKER_NEWS_REFRESH: THE_HACKER_NEWS_FEED,
        }.get(claim.job_kind)
        if publication_feed is not None:
            pipeline = NormalizationPipeline(
                session,
                PublicationRecordParser(),
                PublicationNormalizer(),
                PublicationObservationRepository(),
            )
            connector = FixedSourceConnector(
                publication_feed.source,
                RssPublicationPayloadParser(publication_feed),
                intake,
                pipeline,
            )
            return self._run_fixed(session, claim, connector, publication_feed.source)
        raise PermanentIngestionError("The ingestion job kind is not supported.")

    def _process_mitre(
        self, session: Session, claim: JobClaim, intake: RawEvidenceIntake
    ) -> UUID | None:
        pipeline = NormalizationPipeline(
            session,
            MitreAttackRecordParser(),
            MitreAttackObservationNormalizer(),
        )
        connector = MitreAttackConnector(intake, pipeline)
        result = connector.run_live(
            session,
            MitreAttackFetcher(
                self._settings.max_raw_evidence_bytes,
                timeout=httpx.Timeout(
                    self._settings.ingestion_fetch_timeout_seconds,
                    connect=self._settings.ingestion_fetch_connect_timeout_seconds,
                    pool=self._settings.ingestion_fetch_connect_timeout_seconds,
                    write=self._settings.ingestion_fetch_connect_timeout_seconds,
                ),
            ),
        )
        if result.source_id != claim.source_id:
            raise PermanentIngestionError("The connector returned a different Source.")
        if result.status is ConnectorRunStatus.SOURCE_UNAVAILABLE:
            raise RetryableIngestionError("The approved source is temporarily unavailable.")
        if result.status is ConnectorRunStatus.FAILED:
            raise PermanentIngestionError("Deterministic source processing failed.")
        return result.raw_evidence_id

    def _run_fixed(
        self,
        session: Session,
        claim: JobClaim,
        connector: FixedSourceConnector,
        definition: FixedSourceDefinition,
    ) -> UUID | None:
        result: ConnectorRunResult = connector.run_live(
            session,
            FixedSourceFetcher(
                definition,
                self._settings.max_raw_evidence_bytes,
                timeout=httpx.Timeout(
                    self._settings.ingestion_fetch_timeout_seconds,
                    connect=self._settings.ingestion_fetch_connect_timeout_seconds,
                    pool=self._settings.ingestion_fetch_connect_timeout_seconds,
                    write=self._settings.ingestion_fetch_connect_timeout_seconds,
                ),
            ),
        )
        if result.source_id != claim.source_id:
            raise PermanentIngestionError("The connector returned a different Source.")
        if result.status is ConnectorRunStatus.SOURCE_UNAVAILABLE:
            raise RetryableIngestionError("The approved source is temporarily unavailable.")
        if result.status is ConnectorRunStatus.FAILED:
            raise PermanentIngestionError("Deterministic source processing failed.")
        return result.raw_evidence_id
