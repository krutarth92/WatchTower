import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import (
    Actor,
    Alias,
    Evidence,
    NormalizationLedger,
    Observation,
    ProcessingState,
    PublicationState,
    RawEvidence,
    Source,
    Vulnerability,
)
from watchtower.ingestion.cisa_kev import (
    CISA_KEV_DEFINITION,
    CisaKevNormalizer,
    CisaKevObservationRepository,
    CisaKevPayloadParser,
    CisaKevRecordParser,
)
from watchtower.ingestion.connector import ConnectorRunStatus
from watchtower.ingestion.fixed_source import FixedSourceConnector, InvalidSourcePayloadError
from watchtower.ingestion.misp_galaxy import (
    MISP_GALAXY_DEFINITION,
    MispActorNormalizer,
    MispActorObservationRepository,
    MispActorRecordParser,
    MispGalaxyPayloadParser,
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
from watchtower.storage.local import LocalObjectStore

FETCHED_AT = datetime(2026, 11, 23, 12, tzinfo=UTC)


def misp_fixture() -> bytes:
    return json.dumps(
        {
            "name": "Threat actors",
            "type": "threat-actor",
            "uuid": "7c92b7fb-4d10-4f31-8b8a-f49ac2eacc01",
            "version": 12,
            "values": [
                {
                    "uuid": "1cb7e1cc-d695-42b1-92f4-fd0112a3c9be",
                    "value": "APT Example",
                    "description": "A source-described actor used by this fixture.",
                    "meta": {
                        "synonyms": ["Example Crew", "APT Example"],
                        "refs": ["https://example.test/report"],
                        "attribution-confidence": "70",
                        "country": "EX",
                    },
                    "related": [],
                }
            ],
        }
    ).encode()


def cisa_fixture() -> bytes:
    return json.dumps(
        {
            "title": "CISA Catalog of Known Exploited Vulnerabilities",
            "catalogVersion": "2026.11.23",
            "dateReleased": "2026-11-23",
            "count": 1,
            "vulnerabilities": [
                {
                    "cveID": "CVE-2026-45123",
                    "vendorProject": "Example Vendor",
                    "product": "Example Product",
                    "vulnerabilityName": "Example Product Code Execution Vulnerability",
                    "dateAdded": "2026-11-20",
                    "shortDescription": "The product contains an exploited vulnerability.",
                    "requiredAction": "Apply vendor mitigations.",
                    "dueDate": "2026-12-01",
                    "knownRansomwareCampaignUse": "Unknown",
                    "notes": "https://example.test/advisory",
                    "cwes": ["CWE-78"],
                    "forensicTriage": "Yes",
                }
            ],
        }
    ).encode()


def rss_fixture(
    channel: str,
    article_url: str,
    *,
    category: str | None = None,
    description: str = "<p>Tracked <strong>threat activity</strong>.</p>",
) -> bytes:
    category_xml = f"<category><![CDATA[{category}]]></category>" if category else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{channel}</title>
    <item>
      <title>Example threat publication</title>
      <link>{article_url}</link>
      <guid>{article_url}</guid>
      <pubDate>Fri, 20 Nov 2026 17:00:00 +0000</pubDate>
      <dc:creator>Research Team</dc:creator>
      {category_xml}
      <description><![CDATA[{description}]]></description>
      <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
        <![CDATA[<p>Full article body must be ignored.</p>]]>
      </content:encoded>
    </item>
  </channel>
</rss>""".encode()


def test_source_payload_parsers_preserve_approved_fields_only() -> None:
    misp = MispGalaxyPayloadParser().parse(misp_fixture(), fetched_at=FETCHED_AT)
    cisa = CisaKevPayloadParser().parse(cisa_fixture(), fetched_at=FETCHED_AT)
    microsoft = RssPublicationPayloadParser(MICROSOFT_FEED).parse(
        rss_fixture(
            "Threat intelligence | Microsoft Security Blog",
            "https://www.microsoft.com/en-us/security/blog/example/",
            category="Threat intelligence",
        ),
        fetched_at=FETCHED_AT,
    )

    assert misp.objects[0].source_native_id == "1cb7e1cc-d695-42b1-92f4-fd0112a3c9be"
    assert cisa.objects[0].source_native_id == "CVE-2026-45123"
    assert microsoft.objects[0].payload["summary"] == "Tracked threat activity."
    assert "Full article body" not in str(microsoft.objects[0].payload)


def test_microsoft_topic_feed_does_not_depend_on_mutable_category_labels() -> None:
    parsed = RssPublicationPayloadParser(MICROSOFT_FEED).parse(
        rss_fixture(
            "Threat intelligence | Microsoft Security Blog",
            "https://www.microsoft.com/en-us/security/blog/example/",
            category="Product news",
        ),
        fetched_at=FETCHED_AT,
    )
    assert len(parsed.objects) == 1


@pytest.mark.parametrize(
    ("parser", "content", "message"),
    [
        (
            RssPublicationPayloadParser(UNIT42_FEED),
            b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss><channel/></rss>',
            "DTD",
        ),
        (
            RssPublicationPayloadParser(THE_HACKER_NEWS_FEED),
            rss_fixture("The Hacker News", "https://attacker.example/article"),
            "approved host",
        ),
        (CisaKevPayloadParser(), cisa_fixture().replace(b'"count": 1', b'"count": 2'), "count"),
    ],
)
def test_source_parsers_fail_closed(parser, content: bytes, message: str) -> None:
    with pytest.raises(InvalidSourcePayloadError, match=message):
        parser.parse(content, fetched_at=FETCHED_AT)


def _intake(tmp_path: Path) -> RawEvidenceIntake:
    maximum = 2 * 1024 * 1024
    return RawEvidenceIntake(LocalObjectStore(tmp_path / "objects", maximum), maximum)


def test_misp_connector_creates_internal_actor_alias_and_provenance(
    db_session: Session, tmp_path: Path
) -> None:
    pipeline = NormalizationPipeline(
        db_session,
        MispActorRecordParser(),
        MispActorNormalizer(),
        MispActorObservationRepository(),
    )
    connector = FixedSourceConnector(
        MISP_GALAXY_DEFINITION,
        MispGalaxyPayloadParser(),
        _intake(tmp_path),
        pipeline,
    )

    first = connector.run_fixture(db_session, misp_fixture(), fetched_at=FETCHED_AT)
    second = connector.run_fixture(db_session, misp_fixture(), fetched_at=FETCHED_AT)

    assert first.status is ConnectorRunStatus.SUCCEEDED
    assert second.status is ConnectorRunStatus.SKIPPED
    actor = db_session.scalar(select(Actor).where(Actor.canonical_name == "APT Example"))
    assert actor is not None
    assert actor.publication_state is PublicationState.INTERNAL
    assert [alias.name for alias in actor.aliases] == ["Example Crew"]
    assert db_session.scalar(select(func.count()).select_from(Observation)) == 1
    assert db_session.scalar(select(func.count()).select_from(NormalizationLedger)) == 1


def test_misp_connector_keeps_shared_alias_unresolved(db_session: Session, tmp_path: Path) -> None:
    payload = json.loads(misp_fixture())
    payload["values"].append(
        {
            "uuid": "e41a36a4-eac4-4f10-9627-b718920ac43b",
            "value": "Second Example Actor",
            "description": "A second source cluster sharing an ambiguous synonym.",
            "meta": {"synonyms": ["Example Crew"]},
            "related": [],
        }
    )
    pipeline = NormalizationPipeline(
        db_session,
        MispActorRecordParser(),
        MispActorNormalizer(),
        MispActorObservationRepository(),
    )
    connector = FixedSourceConnector(
        MISP_GALAXY_DEFINITION,
        MispGalaxyPayloadParser(),
        _intake(tmp_path),
        pipeline,
    )

    result = connector.run_fixture(db_session, json.dumps(payload).encode(), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.SUCCEEDED
    alias = db_session.scalar(select(Alias).where(Alias.normalized_name == "example crew"))
    assert alias is not None
    assert alias.actor_id is None
    assert alias.alias_metadata["resolution_status"] == "ambiguous"
    assert len(alias.alias_metadata["candidate_actor_ids"]) == 2
    assert len(alias.alias_metadata["cluster_uuids"]) == 2


def test_cisa_connector_creates_searchable_internal_vulnerability_without_invented_scores(
    db_session: Session, tmp_path: Path
) -> None:
    pipeline = NormalizationPipeline(
        db_session,
        CisaKevRecordParser(),
        CisaKevNormalizer(),
        CisaKevObservationRepository(),
    )
    connector = FixedSourceConnector(
        CISA_KEV_DEFINITION,
        CisaKevPayloadParser(),
        _intake(tmp_path),
        pipeline,
    )

    result = connector.run_fixture(db_session, cisa_fixture(), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.SUCCEEDED
    vulnerability = db_session.scalar(
        select(Vulnerability).where(Vulnerability.cve_id == "CVE-2026-45123")
    )
    assert vulnerability is not None
    assert vulnerability.severity is None
    assert vulnerability.cvss_score is None
    assert vulnerability.publication_state is PublicationState.INTERNAL
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.SUCCEEDED
    assert raw.evidence_metadata["catalog_version"] == "2026.11.23"


def test_publication_connector_stores_metadata_citation_not_article_body(
    db_session: Session, tmp_path: Path
) -> None:
    pipeline = NormalizationPipeline(
        db_session,
        PublicationRecordParser(),
        PublicationNormalizer(),
        PublicationObservationRepository(),
    )
    connector = FixedSourceConnector(
        UNIT42_FEED.source,
        RssPublicationPayloadParser(UNIT42_FEED),
        _intake(tmp_path),
        pipeline,
    )
    content = rss_fixture("Unit 42", "https://unit42.paloaltonetworks.com/example-threat-research/")

    result = connector.run_fixture(
        db_session, content, fetched_at=FETCHED_AT, media_type="text/xml"
    )

    assert result.status is ConnectorRunStatus.SUCCEEDED
    observation = db_session.scalar(select(Observation).where(Observation.title.like("Example%")))
    evidence = db_session.scalar(select(Evidence).where(Evidence.citation.like("Example%")))
    source = db_session.scalar(select(Source).where(Source.name == "Unit 42"))
    assert observation is not None and evidence is not None and source is not None
    assert observation.publication_state is PublicationState.INTERNAL
    assert evidence.excerpt == "Tracked threat activity."
    assert "Full article body" not in (evidence.excerpt or "")
    assert evidence.locator == "https://unit42.paloaltonetworks.com/example-threat-research/"
