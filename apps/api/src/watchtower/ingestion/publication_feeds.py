"""Metadata-only RSS ingestion for approved threat-intelligence publications."""

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import Evidence, Observation, Origin, RawEvidence
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

XML_FORBIDDEN = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)", re.IGNORECASE)
CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in {"script", "style"}:
            self._ignored_depth += 1
        elif tag.casefold() in {"br", "p", "div", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag.casefold() in {"p", "div", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _plain_text(value: str, *, maximum: int) -> str:
    extractor = _PlainTextExtractor()
    try:
        extractor.feed(value)
        extractor.close()
    except Exception as error:
        raise InvalidSourcePayloadError("RSS description contains invalid markup") from error
    cleaned = CONTROL_CHARACTER.sub(" ", "".join(extractor.parts))
    return " ".join(cleaned.split())[:maximum]


def _element_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


@dataclass(frozen=True, slots=True)
class PublicationFeedDefinition:
    source: FixedSourceDefinition
    channel_title: str
    article_hosts: frozenset[str]
    required_categories: frozenset[str] = frozenset()
    secondary_reporting: bool = False


MICROSOFT_FEED = PublicationFeedDefinition(
    source=FixedSourceDefinition(
        key="microsoft-threat-intelligence",
        url="https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/feed/",
        filename="microsoft-threat-intelligence.xml",
        accepted_media_types=frozenset({"application/rss+xml", "application/xml", "text/xml"}),
        registration=SourceRegistration.model_validate(
            {
                "name": "Microsoft Threat Intelligence",
                "kind": "publication_feed",
                "base_url": (
                    "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/"
                ),
                "policy_notes": (
                    "Metadata-only ingestion from the official Microsoft Security Blog RSS "
                    "feed. Retain title, link, supplied summary, author, categories and "
                    "timestamps; do not republish article bodies."
                ),
                "metadata": {"format": "RSS 2.0", "content_policy": "metadata-only"},
            }
        ),
    ),
    channel_title="Threat intelligence | Microsoft Security Blog",
    article_hosts=frozenset({"microsoft.com", "www.microsoft.com"}),
)

UNIT42_FEED = PublicationFeedDefinition(
    source=FixedSourceDefinition(
        key="unit-42",
        url="https://unit42.paloaltonetworks.com/feed/",
        filename="unit-42.xml",
        accepted_media_types=frozenset({"application/rss+xml", "application/xml", "text/xml"}),
        registration=SourceRegistration.model_validate(
            {
                "name": "Unit 42",
                "kind": "publication_feed",
                "base_url": "https://unit42.paloaltonetworks.com/",
                "policy_notes": (
                    "Metadata-only ingestion from the official Unit 42 RSS feed. Retain "
                    "title, link, supplied summary, author, categories and timestamps; do "
                    "not republish article bodies."
                ),
                "metadata": {"format": "RSS 2.0", "content_policy": "metadata-only"},
            }
        ),
    ),
    channel_title="Unit 42",
    article_hosts=frozenset({"unit42.paloaltonetworks.com"}),
)

THE_HACKER_NEWS_FEED = PublicationFeedDefinition(
    source=FixedSourceDefinition(
        key="the-hacker-news",
        url="https://feeds.feedburner.com/TheHackersNews",
        filename="the-hacker-news.xml",
        accepted_media_types=frozenset({"application/rss+xml", "application/xml", "text/xml"}),
        registration=SourceRegistration.model_validate(
            {
                "name": "The Hacker News",
                "kind": "news_feed",
                "base_url": "https://thehackernews.com/",
                "policy_notes": (
                    "Metadata-only ingestion from the publisher's RSS feed. Treat as "
                    "secondary reporting, preserve the publisher link and do not use it "
                    "alone for high-confidence actor attribution or republish article bodies."
                ),
                "metadata": {
                    "format": "RSS 2.0",
                    "content_policy": "metadata-only",
                    "source_tier": "secondary-reporting",
                },
            }
        ),
    ),
    channel_title="The Hacker News",
    article_hosts=frozenset({"thehackernews.com", "www.thehackernews.com"}),
    secondary_reporting=True,
)

PUBLICATION_FEEDS = {
    item.source.key: item for item in (MICROSOFT_FEED, UNIT42_FEED, THE_HACKER_NEWS_FEED)
}


class PublicationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    native_id: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=4000)
    article_url: str = Field(min_length=1, max_length=2048)
    published_at: datetime
    author: str | None = Field(default=None, max_length=255)
    categories: list[str] = Field(default_factory=list, max_length=100)
    secondary_reporting: bool = False

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Publication timestamp must include a timezone")
        return value.astimezone(UTC)


class RssPublicationPayloadParser:
    def __init__(self, definition: PublicationFeedDefinition) -> None:
        self._definition = definition

    def parse(self, content: bytes, *, fetched_at: datetime) -> ParsedSourcePayload:
        if XML_FORBIDDEN.search(content):
            raise InvalidSourcePayloadError("RSS DTD and entity declarations are forbidden")
        try:
            root = ET.fromstring(content)
        except ET.ParseError as error:
            raise InvalidSourcePayloadError("Payload is not well-formed RSS XML") from error
        if root.tag.casefold() != "rss":
            raise InvalidSourcePayloadError("Payload root must be RSS")
        channel = root.find("channel")
        if channel is None:
            raise InvalidSourcePayloadError("RSS channel is missing")
        channel_title = _element_text(channel.find("title"))
        if channel_title != self._definition.channel_title:
            raise InvalidSourcePayloadError("RSS channel title does not match the approved source")

        objects: list[SourceObject] = []
        for index, item in enumerate(channel.findall("item")):
            record = self._parse_item(item, index)
            if record is None:
                continue
            objects.append(
                SourceObject(
                    source_native_id=record.native_id,
                    object_type="publication",
                    payload=record.model_dump(mode="json"),
                )
            )
        latest = max((item.published_at for item in self._records(objects)), default=None)
        return ParsedSourcePayload(
            source_native_id=(
                f"rss:{self._definition.source.key}:{hashlib.sha256(content).hexdigest()[:16]}"
            ),
            published_at=latest,
            metadata={
                "channel_title": channel_title,
                "item_count": len(objects),
                "fetched_at": fetched_at.astimezone(UTC).isoformat(),
                "content_policy": "metadata-only",
            },
            objects=tuple(objects),
        )

    def _parse_item(self, item: ET.Element, index: int) -> PublicationRecord | None:
        title = " ".join(_element_text(item.find("title")).split())[:500]
        link = _element_text(item.find("link"))
        guid = _element_text(item.find("guid")) or link
        published_text = _element_text(item.find("pubDate"))
        description = _element_text(item.find("description"))
        categories = sorted(
            {
                " ".join(_element_text(element).split())[:255]
                for element in item.findall("category")
                if _element_text(element).strip()
            },
            key=str.casefold,
        )
        if self._definition.required_categories and not (
            {category.casefold() for category in categories} & self._definition.required_categories
        ):
            return None
        if not title or not link or not published_text:
            raise InvalidSourcePayloadError(f"RSS item {index} is missing required metadata")
        self._validate_article_url(link)
        try:
            published_at = parsedate_to_datetime(published_text)
        except (TypeError, ValueError) as error:
            raise InvalidSourcePayloadError(
                f"RSS item {index} has an invalid publication timestamp"
            ) from error
        if published_at is None or published_at.tzinfo is None:
            raise InvalidSourcePayloadError(
                f"RSS item {index} publication timestamp has no timezone"
            )
        summary = _plain_text(description, maximum=4000) or title
        author = self._author(item)
        native_id = (
            guid if len(guid) <= 512 else f"sha256:{hashlib.sha256(guid.encode()).hexdigest()}"
        )
        try:
            return PublicationRecord(
                native_id=native_id,
                title=title,
                summary=summary,
                article_url=link,
                published_at=published_at,
                author=author,
                categories=categories,
                secondary_reporting=self._definition.secondary_reporting,
            )
        except ValidationError as error:
            raise InvalidSourcePayloadError(f"RSS item {index} is invalid") from error

    def _validate_article_url(self, value: str) -> None:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in self._definition.article_hosts
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise InvalidSourcePayloadError("RSS article URL is outside the approved host")

    @staticmethod
    def _author(item: ET.Element) -> str | None:
        for tag in ("{http://purl.org/dc/elements/1.1/}creator", "author"):
            value = " ".join(_element_text(item.find(tag)).split())
            if value:
                return value[:255]
        return None

    @staticmethod
    def _records(objects: list[SourceObject]) -> list[PublicationRecord]:
        return [PublicationRecord.model_validate(item.payload) for item in objects]


class PublicationRecordParser:
    def parse(self, record: NormalizationRecord) -> PublicationRecord:
        if record.object_type != "publication":
            raise RejectedSourceRecord("unsupported publication object type")
        try:
            publication = PublicationRecord.model_validate(record.payload)
        except ValidationError as error:
            raise RejectedSourceRecord("invalid publication fields") from error
        if publication.native_id != record.source_native_id:
            raise RejectedSourceRecord("publication ID does not match source-native ID")
        return publication


class PublicationNormalizer:
    def normalize(
        self, parsed: PublicationRecord, record: NormalizationRecord
    ) -> CanonicalObservation:
        metadata: dict[str, Any] = {
            "article_url": parsed.article_url,
            "author": parsed.author,
            "categories": parsed.categories,
            "content_policy": "metadata-only",
            "secondary_reporting": parsed.secondary_reporting,
        }
        return CanonicalObservation(
            source_id=record.source_id,
            raw_evidence_id=record.raw_evidence_id,
            source_native_id=parsed.native_id,
            title=parsed.title,
            summary=parsed.summary,
            observed_at=parsed.published_at,
            first_seen=parsed.published_at,
            metadata=metadata,
        )


class PublicationObservationRepository(SqlAlchemyObservationRepository):
    """Persist metadata corrections while retaining each captured citation."""

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
                DeduplicationAction.KEEP,
                existing,
                "publication metadata already exists",
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
        raw = session.get(RawEvidence, canonical.raw_evidence_id)
        if raw is None:
            raise RejectedSourceRecord("publication raw evidence is unavailable")
        article_url = canonical.metadata.get("article_url")
        if not isinstance(article_url, str):
            raise RejectedSourceRecord("publication URL is missing from canonical metadata")
        evidence = Evidence(
            source_id=canonical.source_id,
            raw_evidence_id=canonical.raw_evidence_id,
            citation=canonical.title[:500],
            excerpt=canonical.summary,
            locator=article_url[:1000],
            captured_at=raw.retrieved_at,
            confidence=None,
            origin=Origin.IMPORTED,
            evidence_metadata={
                "content_policy": "metadata-only",
                "secondary_reporting": canonical.metadata.get("secondary_reporting", False),
            },
        )
        observation.evidence.append(evidence)
        session.flush()
        return observation
