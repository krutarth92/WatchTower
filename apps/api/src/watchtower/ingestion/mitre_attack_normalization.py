"""Source-specific ATT&CK parsing and canonical observation mapping."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from watchtower.ingestion.normalization import (
    CanonicalObservation,
    NormalizationRecord,
    RejectedSourceRecord,
    UnsupportedSourceRecord,
)


class AttackExternalReference(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    source_name: str = Field(min_length=1, max_length=255)
    external_id: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)


class ParsedAttackIntrusionSet(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    type: Literal["intrusion-set"]
    spec_version: Literal["2.1"]
    id: str = Field(min_length=1, max_length=512)
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    created: datetime
    modified: datetime
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    aliases: list[str] = Field(default_factory=list)
    external_references: list[AttackExternalReference] = Field(default_factory=list)
    confidence: int | None = Field(default=None, ge=0, le=100)
    revoked: bool = False
    x_mitre_deprecated: bool = False
    x_mitre_version: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be blank")
        return cleaned

    @field_validator("description", "x_mitre_version")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Aliases cannot be blank")
        return normalized

    @field_validator("created", "modified", "first_seen", "last_seen")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_times(self) -> "ParsedAttackIntrusionSet":
        if self.modified < self.created:
            raise ValueError("modified cannot be earlier than created")
        if (
            self.first_seen is not None
            and self.last_seen is not None
            and self.first_seen > self.last_seen
        ):
            raise ValueError("first_seen cannot be later than last_seen")
        return self


class MitreAttackRecordParser:
    def parse(self, record: NormalizationRecord) -> ParsedAttackIntrusionSet:
        if record.object_type != "intrusion-set":
            raise UnsupportedSourceRecord(f"unsupported object type: {record.object_type}")
        try:
            parsed = ParsedAttackIntrusionSet.model_validate(record.payload)
        except ValidationError as error:
            fields = sorted(
                {
                    ".".join(str(part) for part in detail["loc"])
                    for detail in error.errors(include_url=False, include_input=False)
                }
            )
            field_list = ", ".join(fields[:8]) or "record"
            raise RejectedSourceRecord(
                f"invalid ATT&CK intrusion-set fields: {field_list}"
            ) from error
        if parsed.id != record.source_native_id:
            raise RejectedSourceRecord("payload STIX ID does not match source-native ID")
        return parsed


class MitreAttackObservationNormalizer:
    def normalize(
        self, parsed: ParsedAttackIntrusionSet, record: NormalizationRecord
    ) -> CanonicalObservation:
        metadata: dict[str, Any] = {
            "stix_type": parsed.type,
            "spec_version": parsed.spec_version,
            "created": parsed.created.isoformat(),
            "modified": parsed.modified.isoformat(),
            "aliases": parsed.aliases,
            "external_references": [
                reference.model_dump(mode="json", exclude_none=True)
                for reference in parsed.external_references
            ],
            "revoked": parsed.revoked,
            "x_mitre_deprecated": parsed.x_mitre_deprecated,
        }
        if parsed.x_mitre_version is not None:
            metadata["x_mitre_version"] = parsed.x_mitre_version
        try:
            return CanonicalObservation(
                source_id=record.source_id,
                raw_evidence_id=record.raw_evidence_id,
                source_native_id=parsed.id,
                title=parsed.name,
                summary=parsed.description or parsed.name,
                observed_at=parsed.modified,
                first_seen=parsed.first_seen,
                last_seen=parsed.last_seen,
                confidence=parsed.confidence,
                metadata=metadata,
            )
        except ValidationError as error:
            raise RejectedSourceRecord(
                "ATT&CK record cannot form a canonical observation"
            ) from error
