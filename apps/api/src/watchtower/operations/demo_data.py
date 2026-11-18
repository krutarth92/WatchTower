"""Deterministic, development-only data for the local WATCHTOWER browser journey."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import (
    Actor,
    Advisory,
    AdvisoryRevision,
    AdvisorySection,
    AdvisorySectionType,
    AdvisoryStatus,
    AdvisoryUpdate,
    Alias,
    Behavior,
    Campaign,
    Evidence,
    Indicator,
    IndicatorType,
    IntelligenceType,
    Observation,
    Origin,
    PublicationState,
    Relationship,
    Source,
    Technique,
    Vulnerability,
)
from watchtower.db.session import build_engine

DEMO_DATASET = "watchtower_demo/v1"
DEMO_CREATED_BY = DEMO_DATASET
DEMO_ADVISORY_SLUG = "watchtower-demo-frost-lantern"
DEMO_NAMESPACE = UUID("c361ac2e-b9f0-4af5-98ae-f0ab01f5246b")


def _id(name: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, name)


IDS = {
    "source_registry": _id("source/registry"),
    "source_analysis": _id("source/analysis"),
    "actor": _id("actor/frost-lantern"),
    "alias_northstar": _id("alias/northstar-lynx"),
    "alias_glacier": _id("alias/glacier-041"),
    "behavior_token": _id("behavior/cloud-token-replay"),
    "behavior_powershell": _id("behavior/powershell-staging"),
    "technique_powershell": _id("technique/t1059-001"),
    "technique_token": _id("technique/t1528"),
    "campaign": _id("campaign/northern-beacon"),
    "evidence_registry": _id("evidence/registry"),
    "evidence_analysis": _id("evidence/analysis"),
    "indicator": _id("indicator/telemetry-cdn-example"),
    "vulnerability": _id("vulnerability/cve-2026-45123"),
    "observation_initial": _id("observation/initial-access"),
    "observation_expansion": _id("observation/cloud-expansion"),
    "observation_assessment": _id("observation/assessment"),
    "relationship": _id("relationship/actor-campaign"),
    "advisory": _id("advisory/frost-lantern"),
    "revision_1": _id("advisory/frost-lantern/revision/1"),
    "revision_2": _id("advisory/frost-lantern/revision/2"),
    "revision_1_what": _id("advisory/frost-lantern/revision/1/what"),
    "revision_1_assessment": _id("advisory/frost-lantern/revision/1/assessment"),
    "revision_2_what": _id("advisory/frost-lantern/revision/2/what"),
    "revision_2_technical": _id("advisory/frost-lantern/revision/2/technical"),
    "revision_2_assessment": _id("advisory/frost-lantern/revision/2/assessment"),
    "advisory_update": _id("advisory/frost-lantern/update/1"),
}

EXPECTED_COUNTS = {
    "sources": 2,
    "actors": 1,
    "aliases": 2,
    "behaviors": 2,
    "techniques": 2,
    "campaigns": 1,
    "evidence": 2,
    "indicators": 1,
    "vulnerabilities": 1,
    "observations": 3,
    "relationships": 1,
    "advisories": 1,
    "advisory_revisions": 2,
    "advisory_sections": 5,
    "advisory_updates": 1,
}


def _marker() -> dict[str, Any]:
    return {"watchtower_demo": {"dataset": DEMO_DATASET, "version": 1}}


class DemoDataError(RuntimeError):
    """The demo graph is unsafe to create or remove."""


@dataclass(frozen=True, slots=True)
class DemoDataStatus:
    dataset: str
    state: str
    records: dict[str, int]


MARKED_RECORDS: tuple[tuple[type[Any], UUID, str], ...] = (
    (Source, IDS["source_registry"], "source_metadata"),
    (Source, IDS["source_analysis"], "source_metadata"),
    (Actor, IDS["actor"], "actor_metadata"),
    (Alias, IDS["alias_northstar"], "alias_metadata"),
    (Alias, IDS["alias_glacier"], "alias_metadata"),
    (Behavior, IDS["behavior_token"], "behavior_metadata"),
    (Behavior, IDS["behavior_powershell"], "behavior_metadata"),
    (Technique, IDS["technique_powershell"], "technique_metadata"),
    (Technique, IDS["technique_token"], "technique_metadata"),
    (Campaign, IDS["campaign"], "campaign_metadata"),
    (Evidence, IDS["evidence_registry"], "evidence_metadata"),
    (Evidence, IDS["evidence_analysis"], "evidence_metadata"),
    (Indicator, IDS["indicator"], "indicator_metadata"),
    (Vulnerability, IDS["vulnerability"], "vulnerability_metadata"),
    (Observation, IDS["observation_initial"], "observation_metadata"),
    (Observation, IDS["observation_expansion"], "observation_metadata"),
    (Observation, IDS["observation_assessment"], "observation_metadata"),
    (Relationship, IDS["relationship"], "relationship_metadata"),
)

ALL_DEMO_IDENTITIES: tuple[tuple[type[Any], UUID], ...] = tuple(
    (model, record_id) for model, record_id, _ in MARKED_RECORDS
) + (
    (Advisory, IDS["advisory"]),
    (AdvisoryRevision, IDS["revision_1"]),
    (AdvisoryRevision, IDS["revision_2"]),
    (AdvisorySection, IDS["revision_1_what"]),
    (AdvisorySection, IDS["revision_1_assessment"]),
    (AdvisorySection, IDS["revision_2_what"]),
    (AdvisorySection, IDS["revision_2_technical"]),
    (AdvisorySection, IDS["revision_2_assessment"]),
    (AdvisoryUpdate, IDS["advisory_update"]),
)


def _published(record: Any) -> Any:
    record.publication_state = PublicationState.PUBLISHED
    return record


class DemoDataService:
    def seed(self, session: Session, *, environment: str) -> DemoDataStatus:
        self._require_development(environment)
        existing = self._existing_count(session)
        if existing:
            self._validate_complete(session)
            return DemoDataStatus(DEMO_DATASET, "complete", EXPECTED_COUNTS.copy())

        self._insert(session)
        session.flush()
        self._validate_complete(session)
        return DemoDataStatus(DEMO_DATASET, "created", EXPECTED_COUNTS.copy())

    def cleanup(self, session: Session, *, environment: str) -> DemoDataStatus:
        self._require_development(environment)
        if self._existing_count(session) == 0:
            return DemoDataStatus(DEMO_DATASET, "absent", self._zero_counts())
        self._lock_roots(session)
        self._validate_complete(session)

        delete_order = (
            (Advisory, IDS["advisory"]),
            (Relationship, IDS["relationship"]),
            (Alias, IDS["alias_northstar"]),
            (Alias, IDS["alias_glacier"]),
            (Observation, IDS["observation_initial"]),
            (Observation, IDS["observation_expansion"]),
            (Observation, IDS["observation_assessment"]),
            (Indicator, IDS["indicator"]),
            (Vulnerability, IDS["vulnerability"]),
            (Campaign, IDS["campaign"]),
            (Technique, IDS["technique_powershell"]),
            (Technique, IDS["technique_token"]),
            (Behavior, IDS["behavior_token"]),
            (Behavior, IDS["behavior_powershell"]),
            (Evidence, IDS["evidence_registry"]),
            (Evidence, IDS["evidence_analysis"]),
            (Actor, IDS["actor"]),
            (Source, IDS["source_registry"]),
            (Source, IDS["source_analysis"]),
        )
        for model, record_id in delete_order:
            record = session.get(model, record_id)
            if record is not None:
                session.delete(record)
                session.flush()
        session.expire_all()
        if self._existing_count(session) != 0:
            raise DemoDataError("Demo cleanup did not remove the complete marked graph.")
        return DemoDataStatus(DEMO_DATASET, "removed", self._zero_counts())

    def status(self, session: Session, *, environment: str) -> DemoDataStatus:
        self._require_development(environment)
        if self._existing_count(session) == 0:
            return DemoDataStatus(DEMO_DATASET, "absent", self._zero_counts())
        self._validate_complete(session)
        return DemoDataStatus(DEMO_DATASET, "complete", EXPECTED_COUNTS.copy())

    @staticmethod
    def _require_development(environment: str) -> None:
        if environment != "development":
            raise DemoDataError("Demo data commands are allowed only in development.")

    @staticmethod
    def _zero_counts() -> dict[str, int]:
        return {key: 0 for key in EXPECTED_COUNTS}

    @staticmethod
    def _existing_count(session: Session) -> int:
        return sum(
            session.get(model, record_id) is not None for model, record_id in ALL_DEMO_IDENTITIES
        )

    @staticmethod
    def _lock_roots(session: Session) -> None:
        for model, record_id in (
            (Source, IDS["source_registry"]),
            (Source, IDS["source_analysis"]),
            (Advisory, IDS["advisory"]),
        ):
            session.get(model, record_id, with_for_update=True)

    def _validate_complete(self, session: Session) -> None:
        for model, record_id, metadata_attribute in MARKED_RECORDS:
            record = session.get(model, record_id)
            if record is None:
                raise DemoDataError("The demo graph is partial; no changes were made.")
            metadata = getattr(record, metadata_attribute)
            if metadata.get("watchtower_demo") != _marker()["watchtower_demo"]:
                raise DemoDataError("A deterministic demo identity is not owned by this dataset.")

        actor = session.get(Actor, IDS["actor"])
        initial = session.get(Observation, IDS["observation_initial"])
        expansion = session.get(Observation, IDS["observation_expansion"])
        assessment = session.get(Observation, IDS["observation_assessment"])
        relationship = session.get(Relationship, IDS["relationship"])
        assert actor is not None and initial is not None and expansion is not None
        assert assessment is not None and relationship is not None
        if (
            {item.id for item in actor.aliases} != {IDS["alias_northstar"], IDS["alias_glacier"]}
            or {item.id for item in actor.observations}
            != {
                IDS["observation_initial"],
                IDS["observation_expansion"],
                IDS["observation_assessment"],
            }
            or {item.id for item in actor.indicators} != {IDS["indicator"]}
            or {item.id for item in actor.vulnerabilities} != {IDS["vulnerability"]}
            or {item.id for item in initial.behaviors} != {IDS["behavior_powershell"]}
            or {item.id for item in initial.techniques} != {IDS["technique_powershell"]}
            or {item.id for item in initial.evidence} != {IDS["evidence_registry"]}
            or {item.id for item in expansion.behaviors} != {IDS["behavior_token"]}
            or {item.id for item in expansion.techniques} != {IDS["technique_token"]}
            or {item.id for item in expansion.evidence} != {IDS["evidence_registry"]}
            or {item.id for item in assessment.behaviors} != {IDS["behavior_token"]}
            or {item.id for item in assessment.techniques}
            != {IDS["technique_powershell"], IDS["technique_token"]}
            or {item.id for item in assessment.evidence}
            != {IDS["evidence_registry"], IDS["evidence_analysis"]}
            or relationship.actor_id != IDS["actor"]
            or relationship.campaign_id != IDS["campaign"]
            or relationship.evidence_id != IDS["evidence_analysis"]
        ):
            raise DemoDataError("The demo intelligence graph is incomplete or unowned.")

        advisory = session.get(Advisory, IDS["advisory"])
        if advisory is None or advisory.slug != DEMO_ADVISORY_SLUG:
            raise DemoDataError(
                "The deterministic demo advisory identity is not owned by this dataset."
            )
        revisions = list(
            session.scalars(
                select(AdvisoryRevision).where(AdvisoryRevision.advisory_id == advisory.id)
            ).all()
        )
        if {item.id for item in revisions} != {IDS["revision_1"], IDS["revision_2"]} or any(
            item.created_by != DEMO_CREATED_BY or item.published_by != DEMO_CREATED_BY
            for item in revisions
        ):
            raise DemoDataError("The demo advisory revisions are incomplete or unowned.")
        section_ids = set(
            session.scalars(
                select(AdvisorySection.id).where(
                    AdvisorySection.revision_id.in_([item.id for item in revisions])
                )
            ).all()
        )
        expected_sections = {
            IDS["revision_1_what"],
            IDS["revision_1_assessment"],
            IDS["revision_2_what"],
            IDS["revision_2_technical"],
            IDS["revision_2_assessment"],
        }
        update = session.get(AdvisoryUpdate, IDS["advisory_update"])
        if (
            section_ids != expected_sections
            or update is None
            or update.created_by != DEMO_CREATED_BY
        ):
            raise DemoDataError("The demo advisory history is incomplete or unowned.")
        revision_by_version = {item.version: item for item in revisions}
        first = revision_by_version.get(1)
        second = revision_by_version.get(2)
        if (
            first is None
            or second is None
            or {item.id for item in first.evidence} != {IDS["evidence_registry"]}
            or {item.id for item in first.actors} != {IDS["actor"]}
            or {item.id for item in first.campaigns} != {IDS["campaign"]}
            or {item.id for item in first.techniques} != {IDS["technique_powershell"]}
            or {item.id for item in second.evidence}
            != {IDS["evidence_registry"], IDS["evidence_analysis"]}
            or {item.id for item in second.actors} != {IDS["actor"]}
            or {item.id for item in second.campaigns} != {IDS["campaign"]}
            or {item.id for item in second.techniques}
            != {IDS["technique_powershell"], IDS["technique_token"]}
            or {item.id for item in update.evidence}
            != {IDS["evidence_registry"], IDS["evidence_analysis"]}
        ):
            raise DemoDataError("The demo advisory links are incomplete or unowned.")

    @staticmethod
    def _insert(session: Session) -> None:
        observed_at = datetime(2026, 6, 12, 9, 30, tzinfo=UTC)
        expanded_at = datetime(2026, 8, 19, 14, 15, tzinfo=UTC)
        assessed_at = datetime(2026, 9, 8, 11, 0, tzinfo=UTC)
        published_v1 = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
        published_v2 = datetime(2026, 9, 10, 10, 0, tzinfo=UTC)

        registry = _published(
            Source(
                id=IDS["source_registry"],
                name="WATCHTOWER Demo Registry",
                kind="demo_dataset",
                policy_notes="Fictional local-only data for the WATCHTOWER V1 browser journey.",
                license_name="Local demonstration only",
                source_metadata=_marker(),
            )
        )
        analysis = _published(
            Source(
                id=IDS["source_analysis"],
                name="WATCHTOWER Demo Analysis",
                kind="demo_reporting",
                policy_notes="Fictional analyst context generated only for local evaluation.",
                license_name="Local demonstration only",
                source_metadata=_marker(),
            )
        )
        actor = _published(
            Actor(
                id=IDS["actor"],
                canonical_name="Frost Lantern",
                normalized_name="frost lantern",
                description=(
                    "Fictional adversary used to demonstrate how WATCHTOWER connects identity, "
                    "behavior, evidence and change over time."
                ),
                actor_metadata={**_marker(), "demo_notice": "Fictional local-only actor"},
            )
        )
        alias_northstar = _published(
            Alias(
                id=IDS["alias_northstar"],
                source=registry,
                actor=actor,
                name="Northstar Lynx",
                normalized_name="northstar lynx",
                source_native_id="watchtower-demo-alias-northstar-lynx",
                confidence=88,
                alias_metadata=_marker(),
            )
        )
        alias_glacier = _published(
            Alias(
                id=IDS["alias_glacier"],
                source=analysis,
                actor=actor,
                name="GLACIER-041",
                normalized_name="glacier-041",
                source_native_id="watchtower-demo-alias-glacier-041",
                confidence=72,
                alias_metadata=_marker(),
            )
        )
        token_behavior = _published(
            Behavior(
                id=IDS["behavior_token"],
                name="Cloud token replay",
                normalized_name="cloud token replay",
                description="Reuses a captured access token to enter a cloud service.",
                behavior_metadata=_marker(),
            )
        )
        powershell_behavior = _published(
            Behavior(
                id=IDS["behavior_powershell"],
                name="PowerShell staging",
                normalized_name="powershell staging",
                description="Stages follow-on tooling with a signed scripting interpreter.",
                behavior_metadata=_marker(),
            )
        )
        powershell = _published(
            Technique(
                id=IDS["technique_powershell"],
                source=registry,
                external_id="T1059.001",
                name="PowerShell",
                description="Command and Scripting Interpreter: PowerShell.",
                technique_metadata=_marker(),
            )
        )
        token_theft = _published(
            Technique(
                id=IDS["technique_token"],
                source=registry,
                external_id="T1528",
                name="Steal Application Access Token",
                description="Obtains an application access token for later replay.",
                technique_metadata=_marker(),
            )
        )
        campaign = _published(
            Campaign(
                id=IDS["campaign"],
                source=analysis,
                source_native_id="watchtower-demo-campaign-northern-beacon",
                name="Northern Beacon",
                normalized_name="northern beacon",
                description=(
                    "Fictional campaign showing an adversary expanding from endpoint to cloud."
                ),
                first_seen=observed_at,
                last_seen=assessed_at,
                confidence=82,
                intelligence_type=IntelligenceType.ASSESSED,
                origin=Origin.WATCHTOWER,
                campaign_metadata=_marker(),
            )
        )
        registry_evidence = _published(
            Evidence(
                id=IDS["evidence_registry"],
                source=registry,
                citation="WATCHTOWER demo registry observation 2026-06",
                excerpt=(
                    "A reserved example domain and PowerShell execution were observed in the "
                    "fictional Northern Beacon dataset."
                ),
                locator="https://example.invalid/watchtower-demo/registry/2026-06",
                captured_at=observed_at,
                confidence=94,
                origin=Origin.IMPORTED,
                evidence_metadata=_marker(),
            )
        )
        analysis_evidence = _published(
            Evidence(
                id=IDS["evidence_analysis"],
                source=analysis,
                citation="WATCHTOWER demo analyst note 2026-09",
                excerpt=(
                    "Analysts assess that token replay represents a deliberate expansion into "
                    "cloud identity rather than isolated endpoint activity."
                ),
                locator="https://example.invalid/watchtower-demo/analysis/2026-09",
                captured_at=assessed_at,
                confidence=80,
                origin=Origin.WATCHTOWER,
                evidence_metadata=_marker(),
            )
        )
        indicator = _published(
            Indicator(
                id=IDS["indicator"],
                source=registry,
                indicator_type=IndicatorType.DOMAIN,
                value="telemetry-cdn.example",
                normalized_value="telemetry-cdn.example",
                description="Reserved example domain in the fictional Northern Beacon dataset.",
                first_seen=observed_at,
                last_seen=expanded_at,
                confidence=96,
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
                indicator_metadata=_marker(),
            )
        )
        vulnerability = _published(
            Vulnerability(
                id=IDS["vulnerability"],
                source=registry,
                cve_id="CVE-2026-45123",
                title="Synthetic remote access demonstration vulnerability",
                description=(
                    "Fictional CVE-shaped record used only to demonstrate vulnerability search."
                ),
                severity="critical",
                cvss_score=9.1,
                published_at=datetime(2026, 5, 20, tzinfo=UTC),
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
                vulnerability_metadata=_marker(),
            )
        )
        initial = _published(
            Observation(
                id=IDS["observation_initial"],
                source=registry,
                source_native_id="watchtower-demo-observation-initial-access",
                title="Frost Lantern stages PowerShell tooling",
                summary=(
                    "Observed PowerShell staging contacted telemetry-cdn.example in the "
                    "fictional Northern Beacon dataset."
                ),
                observed_at=observed_at,
                first_seen=observed_at,
                last_seen=observed_at,
                confidence=94,
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
                observation_metadata=_marker(),
            )
        )
        expansion = _published(
            Observation(
                id=IDS["observation_expansion"],
                source=registry,
                source_native_id="watchtower-demo-observation-cloud-expansion",
                title="Cloud access token replay observed",
                summary=(
                    "A captured application token was replayed against a demonstration cloud "
                    "tenant, expanding the campaign beyond endpoint execution."
                ),
                observed_at=expanded_at,
                first_seen=expanded_at,
                last_seen=expanded_at,
                confidence=90,
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
                observation_metadata=_marker(),
            )
        )
        assessment = _published(
            Observation(
                id=IDS["observation_assessment"],
                source=analysis,
                source_native_id="watchtower-demo-observation-assessment",
                title="WATCHTOWER assesses deliberate cloud expansion",
                summary=(
                    "WATCHTOWER assesses with moderate confidence that Frost Lantern evolved "
                    "from endpoint staging toward reusable cloud identity access."
                ),
                observed_at=assessed_at,
                first_seen=observed_at,
                last_seen=assessed_at,
                confidence=80,
                intelligence_type=IntelligenceType.ASSESSED,
                origin=Origin.WATCHTOWER,
                observation_metadata=_marker(),
            )
        )

        actor.observations.extend([initial, expansion, assessment])
        actor.indicators.append(indicator)
        actor.vulnerabilities.append(vulnerability)
        initial.behaviors.append(powershell_behavior)
        initial.techniques.append(powershell)
        initial.evidence.append(registry_evidence)
        expansion.behaviors.append(token_behavior)
        expansion.techniques.append(token_theft)
        expansion.evidence.append(registry_evidence)
        assessment.behaviors.append(token_behavior)
        assessment.techniques.extend([powershell, token_theft])
        assessment.evidence.extend([registry_evidence, analysis_evidence])

        relationship = Relationship(
            id=IDS["relationship"],
            actor=actor,
            campaign=campaign,
            source=analysis,
            evidence_id=analysis_evidence.id,
            relationship_type="attributed-to",
            first_seen=observed_at,
            last_seen=assessed_at,
            confidence=82,
            intelligence_type=IntelligenceType.ASSESSED,
            origin=Origin.WATCHTOWER,
            relationship_metadata=_marker(),
        )

        revision_1 = AdvisoryRevision(
            id=IDS["revision_1"],
            version=1,
            title="Frost Lantern expands from endpoint staging",
            summary=(
                "A fictional WATCHTOWER advisory connecting PowerShell staging to the "
                "Northern Beacon campaign."
            ),
            created_by=DEMO_CREATED_BY,
            created_at=published_v1,
            published_at=published_v1,
            published_by=DEMO_CREATED_BY,
            evidence=[registry_evidence],
            actors=[actor],
            campaigns=[campaign],
            techniques=[powershell],
            sections=[
                AdvisorySection(
                    id=IDS["revision_1_what"],
                    section_type=AdvisorySectionType.WHAT_HAPPENED,
                    position=0,
                    intelligence_type=IntelligenceType.OBSERVED,
                    content=(
                        "The local demonstration dataset records PowerShell staging and a "
                        "connection to a reserved example domain."
                    ),
                    created_at=published_v1,
                ),
                AdvisorySection(
                    id=IDS["revision_1_assessment"],
                    section_type=AdvisorySectionType.WATCHTOWER_ASSESSMENT,
                    position=1,
                    intelligence_type=IntelligenceType.ASSESSED,
                    content=(
                        "This fictional activity is assessed as the opening phase of Northern "
                        "Beacon; it is not real-world threat reporting."
                    ),
                    created_at=published_v1,
                ),
            ],
        )
        revision_2 = AdvisoryRevision(
            id=IDS["revision_2"],
            version=2,
            title="Frost Lantern evolves toward cloud identity access",
            summary=(
                "The revised fictional advisory adds observed token replay and explains the "
                "change from endpoint execution to cloud access."
            ),
            created_by=DEMO_CREATED_BY,
            created_at=published_v2,
            published_at=published_v2,
            published_by=DEMO_CREATED_BY,
            evidence=[registry_evidence, analysis_evidence],
            actors=[actor],
            campaigns=[campaign],
            techniques=[powershell, token_theft],
            sections=[
                AdvisorySection(
                    id=IDS["revision_2_what"],
                    section_type=AdvisorySectionType.WHAT_HAPPENED,
                    position=0,
                    intelligence_type=IntelligenceType.OBSERVED,
                    content=(
                        "The later observation records application-token replay against a "
                        "demonstration tenant after the earlier PowerShell staging."
                    ),
                    created_at=published_v2,
                ),
                AdvisorySection(
                    id=IDS["revision_2_technical"],
                    section_type=AdvisorySectionType.TECHNICAL_ANALYSIS,
                    position=1,
                    intelligence_type=IntelligenceType.OBSERVED,
                    content=(
                        "The demonstration maps the sequence to ATT&CK T1059.001 and T1528 "
                        "while retaining the evidence source for each observation."
                    ),
                    created_at=published_v2,
                ),
                AdvisorySection(
                    id=IDS["revision_2_assessment"],
                    section_type=AdvisorySectionType.WATCHTOWER_ASSESSMENT,
                    position=2,
                    intelligence_type=IntelligenceType.ASSESSED,
                    content=(
                        "WATCHTOWER assesses that the fictional adversary deliberately expanded "
                        "its access model; this conclusion remains distinct from observed facts."
                    ),
                    created_at=published_v2,
                ),
            ],
        )
        advisory = Advisory(
            id=IDS["advisory"],
            slug=DEMO_ADVISORY_SLUG,
            status=AdvisoryStatus.PUBLISHED,
            published_revision=2,
            published_at=published_v2,
            created_at=published_v1,
            updated_at=published_v2,
            revisions=[revision_1, revision_2],
        )
        update = AdvisoryUpdate(
            id=IDS["advisory_update"],
            advisory=advisory,
            revision=revision_2,
            sequence=1,
            occurred_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
            title="Detection context added",
            summary=(
                "The fictional advisory now links the reserved example domain and token-replay "
                "observation to their source evidence."
            ),
            intelligence_type=IntelligenceType.OBSERVED,
            created_by=DEMO_CREATED_BY,
            created_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
            evidence=[registry_evidence, analysis_evidence],
        )

        session.add_all(
            [
                registry,
                analysis,
                actor,
                alias_northstar,
                alias_glacier,
                token_behavior,
                powershell_behavior,
                powershell,
                token_theft,
                campaign,
                registry_evidence,
                analysis_evidence,
                indicator,
                vulnerability,
                initial,
                expansion,
                assessment,
                relationship,
                advisory,
                update,
            ]
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watchtower-demo-data",
        description="Manage deterministic WATCHTOWER V1 local demonstration data.",
    )
    parser.add_argument("command", choices=("seed", "cleanup", "status"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue]
        service = DemoDataService()
        engine = build_engine(settings)
        try:
            with Session(engine) as session:
                operation = getattr(service, args.command)
                result: DemoDataStatus = operation(session, environment=settings.environment)
                if args.command != "status":
                    session.commit()
        finally:
            engine.dispose()
        print(json.dumps(asdict(result), sort_keys=True))
    except DemoDataError as error:
        print(json.dumps({"dataset": DEMO_DATASET, "error": str(error)}), file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
