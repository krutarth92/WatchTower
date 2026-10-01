"""Connector-facing raw intake services."""

from watchtower.ingestion.contracts import RawEvidenceSubmission, SourceRegistration
from watchtower.ingestion.mitre_attack import MitreAttackConnector, MitreAttackFetcher
from watchtower.ingestion.mitre_attack_normalization import (
    MitreAttackObservationNormalizer,
    MitreAttackRecordParser,
)
from watchtower.ingestion.normalization import (
    NormalizationEmitter,
    NormalizationPipeline,
    NormalizationRecord,
)
from watchtower.ingestion.raw_evidence import IntakeResult, RawEvidenceIntake
from watchtower.ingestion.source_registry import SourceRegistry

__all__ = [
    "IntakeResult",
    "MitreAttackConnector",
    "MitreAttackFetcher",
    "MitreAttackObservationNormalizer",
    "MitreAttackRecordParser",
    "NormalizationEmitter",
    "NormalizationPipeline",
    "NormalizationRecord",
    "RawEvidenceIntake",
    "RawEvidenceSubmission",
    "SourceRegistration",
    "SourceRegistry",
]
