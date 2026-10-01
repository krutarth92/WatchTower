import re
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    StrictBytes,
    field_validator,
    model_validator,
)

MEDIA_TYPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")
CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class SourceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=255)
    kind: str = Field(min_length=1, max_length=50)
    base_url: HttpUrl | None = None
    policy_notes: str | None = Field(default=None, max_length=4000)
    license_name: str | None = Field(default=None, max_length=255)
    license_url: HttpUrl | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("name", "kind", "policy_notes", "license_name")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class RawEvidenceSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: UUID
    content: StrictBytes = Field(min_length=1, repr=False)
    source_locator: str = Field(min_length=1, max_length=2048)
    fetched_at: datetime
    published_at: datetime | None = None
    mime_type: str = Field(min_length=3, max_length=255)
    filename_hint: str | None = Field(default=None, max_length=512)
    source_native_id: str | None = Field(default=None, max_length=512)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("source_locator", "filename_hint", "source_native_id")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Value must be non-blank and contain no control characters")
        return cleaned

    @field_validator("mime_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not MEDIA_TYPE.fullmatch(cleaned):
            raise ValueError("Use a media type without parameters, for example application/json")
        return cleaned

    @field_validator("fetched_at", "published_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_publication_order(self) -> Self:
        if self.published_at is not None and self.published_at > self.fetched_at:
            raise ValueError("Publication time cannot be later than fetch time")
        return self
