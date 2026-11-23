"""CISA Known Exploited Vulnerabilities catalog ingestion."""

import json
from datetime import UTC, date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import IntelligenceType, Observation, Origin, Vulnerability
from watchtower.ingestion.contracts import SourceRegistration
from watchtower.ingestion.fixed_source import (
    FixedSourceDefinition,
    InvalidSourcePayloadError,
    ParsedSourcePayload,
    SourceObject,
)
from watchtower.ingestion.normalization import (
    CanonicalObservation,
    DeduplicationAction,
    DeduplicationDecision,
    NormalizationRecord,
    RejectedSourceRecord,
    SqlAlchemyObservationRepository,
)

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CISA_KEV_DEFINITION = FixedSourceDefinition(
    key="cisa-kev",
    url=CISA_KEV_URL,
    filename="cisa-known-exploited-vulnerabilities.json",
    accepted_media_types=frozenset({"application/json", "application/octet-stream"}),
    registration=SourceRegistration.model_validate(
        {
            "name": "CISA Known Exploited Vulnerabilities",
            "kind": "dataset",
            "base_url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            "policy_notes": (
                "Official CISA KEV catalog import. Preserve CISA remediation fields and do "
                "not infer CVSS or severity values not supplied by the catalog."
            ),
            "metadata": {
                "collection": "known-exploited-vulnerabilities",
                "format": "JSON",
            },
        }
    ),
)


class CisaKevEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    cveID: str = Field(pattern=r"^CVE-[0-9]{4}-[0-9]{4,}$")
    vendorProject: str = Field(min_length=1, max_length=255)
    product: str = Field(min_length=1, max_length=255)
    vulnerabilityName: str = Field(min_length=1, max_length=500)
    dateAdded: date
    shortDescription: str = Field(min_length=1)
    requiredAction: str = Field(min_length=1)
    dueDate: date
    knownRansomwareCampaignUse: Literal["Known", "Unknown"]
    notes: str = ""
    cwes: list[str] = Field(default_factory=list, max_length=100)
    forensicTriage: str | None = Field(default=None, max_length=100)

    @field_validator(
        "vendorProject",
        "product",
        "vulnerabilityName",
        "shortDescription",
        "requiredAction",
        "notes",
    )
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())


class CisaKevDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    title: str = Field(min_length=1, max_length=500)
    catalogVersion: str = Field(min_length=1, max_length=100)
    dateReleased: datetime
    count: int = Field(ge=0)
    vulnerabilities: list[CisaKevEntry] = Field(max_length=10000)

    @field_validator("dateReleased", mode="before")
    @classmethod
    def normalize_release_timestamp(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) == 10:
            return f"{value}T00:00:00Z"
        return value

    @field_validator("dateReleased")
    @classmethod
    def require_release_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("CISA release timestamp must include a timezone")
        return value.astimezone(UTC)


class CisaKevPayloadParser:
    def parse(self, content: bytes, *, fetched_at: datetime) -> ParsedSourcePayload:
        del fetched_at
        try:
            payload = json.loads(content)
            document = CisaKevDocument.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
            raise InvalidSourcePayloadError("Payload is not a valid CISA KEV catalog") from error
        if document.count != len(document.vulnerabilities):
            raise InvalidSourcePayloadError("CISA KEV count does not match the catalog entries")
        objects = tuple(
            SourceObject(
                source_native_id=entry.cveID,
                object_type="cisa-kev-vulnerability",
                payload=entry.model_dump(mode="json"),
            )
            for entry in document.vulnerabilities
        )
        return ParsedSourcePayload(
            source_native_id=f"cisa-kev:{document.catalogVersion}",
            published_at=document.dateReleased,
            metadata={
                "catalog_title": document.title,
                "catalog_version": document.catalogVersion,
                "date_released": document.dateReleased.isoformat(),
                "entry_count": document.count,
            },
            objects=objects,
        )


class CisaKevRecordParser:
    def parse(self, record: NormalizationRecord) -> CisaKevEntry:
        if record.object_type != "cisa-kev-vulnerability":
            raise RejectedSourceRecord("unsupported CISA KEV object type")
        try:
            entry = CisaKevEntry.model_validate(record.payload)
        except ValidationError as error:
            raise RejectedSourceRecord("invalid CISA KEV fields") from error
        if entry.cveID != record.source_native_id:
            raise RejectedSourceRecord("CISA CVE does not match source-native ID")
        return entry


class CisaKevNormalizer:
    def normalize(self, parsed: CisaKevEntry, record: NormalizationRecord) -> CanonicalObservation:
        metadata: dict[str, Any] = {
            "cve_id": parsed.cveID,
            "vendor_project": parsed.vendorProject,
            "product": parsed.product,
            "required_action": parsed.requiredAction,
            "due_date": parsed.dueDate.isoformat(),
            "known_ransomware_campaign_use": parsed.knownRansomwareCampaignUse,
            "notes": parsed.notes,
            "cwes": parsed.cwes,
        }
        if parsed.forensicTriage is not None:
            metadata["forensic_triage"] = parsed.forensicTriage
        added_at = datetime.combine(parsed.dateAdded, time.min, tzinfo=UTC)
        return CanonicalObservation(
            source_id=record.source_id,
            raw_evidence_id=record.raw_evidence_id,
            source_native_id=parsed.cveID,
            title=parsed.vulnerabilityName,
            summary=parsed.shortDescription,
            observed_at=added_at,
            first_seen=added_at,
            metadata=metadata,
        )


class CisaKevObservationRepository(SqlAlchemyObservationRepository):
    """Update corrected KEV records even when CISA retains their date-added value."""

    def deduplicate(
        self, session: Session, canonical: CanonicalObservation, fingerprint: str
    ) -> DeduplicationDecision:
        existing = session.scalar(
            select(Observation).where(
                Observation.source_id == canonical.source_id,
                Observation.source_native_id == canonical.source_native_id,
            )
        )
        if existing is None:
            return DeduplicationDecision(DeduplicationAction.CREATE, None)
        normalization = existing.observation_metadata.get("normalization")
        existing_fingerprint = (
            normalization.get("fingerprint") if isinstance(normalization, dict) else None
        )
        if existing_fingerprint == fingerprint:
            return DeduplicationDecision(
                DeduplicationAction.KEEP, existing, "canonical KEV record already exists"
            )
        return DeduplicationDecision(DeduplicationAction.UPDATE, existing)

    def persist(
        self,
        session: Session,
        canonical: CanonicalObservation,
        fingerprint: str,
        decision: DeduplicationDecision,
    ) -> Observation:
        observation = super().persist(session, canonical, fingerprint, decision)
        if decision.action is DeduplicationAction.KEEP:
            return observation
        metadata = canonical.metadata
        cve_id = metadata.get("cve_id")
        if not isinstance(cve_id, str):
            raise RejectedSourceRecord("CISA CVE is missing from canonical metadata")
        vulnerability = session.scalar(
            select(Vulnerability).where(
                Vulnerability.source_id == canonical.source_id,
                Vulnerability.cve_id == cve_id,
            )
        )
        title = canonical.title[:500]
        values = {
            "title": title,
            "description": canonical.summary,
            "published_at": canonical.first_seen,
            "intelligence_type": IntelligenceType.OBSERVED,
            "origin": Origin.IMPORTED,
            "vulnerability_metadata": {
                key: value for key, value in metadata.items() if key != "cve_id"
            },
        }
        if vulnerability is None:
            vulnerability = Vulnerability(
                source_id=canonical.source_id,
                cve_id=cve_id,
                severity=None,
                cvss_score=None,
                modified_at=None,
                **values,
            )
            session.add(vulnerability)
        else:
            for key, value in values.items():
                setattr(vulnerability, key, value)
        session.flush()
        return observation
