"""Approved ingestion processors used by Dramatiq jobs."""

from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import IngestionJobKind
from watchtower.ingestion.job_runner import (
    PermanentIngestionError,
    RetryableIngestionError,
)
from watchtower.ingestion.jobs import JobClaim
from watchtower.ingestion.mitre_attack import (
    ConnectorRunStatus,
    MitreAttackConnector,
    MitreAttackFetcher,
)
from watchtower.ingestion.mitre_attack_normalization import (
    MitreAttackObservationNormalizer,
    MitreAttackRecordParser,
)
from watchtower.ingestion.normalization import NormalizationPipeline
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.storage.local import LocalObjectStore


class ApprovedIngestionProcessor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def process(self, session: Session, claim: JobClaim) -> UUID | None:
        if claim.job_kind is not IngestionJobKind.MITRE_ATTACK_REFRESH:
            raise PermanentIngestionError("The ingestion job kind is not supported.")
        store = LocalObjectStore(
            self._settings.raw_storage_path,
            self._settings.max_raw_evidence_bytes,
        )
        intake = RawEvidenceIntake(store, self._settings.max_raw_evidence_bytes)
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
