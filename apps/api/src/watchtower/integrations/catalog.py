"""Authoritative source roadmap exposed to authenticated operators."""

from dataclasses import dataclass
from typing import Literal

from watchtower.db.models import IngestionJobKind

IntegrationWave = Literal["implemented", "first_wave", "second_wave", "candidate"]
EnrichmentWave = Literal["implemented", "first_wave", "later"]


@dataclass(frozen=True, slots=True)
class IntegrationDefinition:
    key: str
    name: str
    wave: IntegrationWave
    description: str
    implemented: bool = False
    job_kind: IngestionJobKind | None = None
    required_settings: tuple[str, ...] = ()
    enrichments: tuple[str, ...] = ()

    @property
    def configured(self) -> bool:
        return self.implemented and not self.required_settings

    @property
    def can_sync(self) -> bool:
        return self.configured and self.job_kind is not None


@dataclass(frozen=True, slots=True)
class EnrichmentDefinition:
    key: str
    name: str
    wave: EnrichmentWave
    description: str
    implemented: bool = False


INTEGRATION_CATALOG: tuple[IntegrationDefinition, ...] = (
    IntegrationDefinition(
        key="mitre-attack",
        name="MITRE ATT&CK Enterprise",
        wave="implemented",
        description="Versioned ATT&CK STIX data for actors, techniques and mappings.",
        implemented=True,
        job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="misp-galaxy",
        name="MISP Galaxy",
        wave="first_wave",
        description="Versioned galaxy clusters, synonyms and source attribution.",
        enrichments=("alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="cisa",
        name="CISA",
        wave="first_wave",
        description=(
            "Authoritative CISA intelligence beginning with Known Exploited Vulnerabilities."
        ),
        enrichments=("historical correlation",),
    ),
    IntegrationDefinition(
        key="microsoft-threat-intelligence",
        name="Microsoft Threat Intelligence",
        wave="first_wave",
        description="Official Microsoft threat publications with actor and campaign attribution.",
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="google-tag",
        name="Google Threat Analysis Group",
        wave="first_wave",
        description="Official TAG reporting on state-backed and coordinated threat activity.",
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="unit-42",
        name="Unit 42",
        wave="first_wave",
        description="Unit 42 research with actor, campaign and technique context.",
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="malpedia",
        name="Malpedia",
        wave="second_wave",
        description="Malware-family and actor relationships after access and licensing review.",
        required_settings=("WATCHTOWER_MALPEDIA_API_KEY",),
        enrichments=("alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="securelist",
        name="Securelist",
        wave="second_wave",
        description="Kaspersky research publications with retained source attribution.",
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="eset-research",
        name="ESET Research",
        wave="second_wave",
        description="ESET research publications with retained source attribution.",
        enrichments=("ATT&CK mappings", "alias resolution", "historical correlation"),
    ),
    IntegrationDefinition(
        key="selected-news",
        name="Selected news sources",
        wave="second_wave",
        description="An editorially approved source list after reliability and licensing review.",
        enrichments=("historical correlation",),
    ),
)


ENRICHMENT_ROADMAP: tuple[EnrichmentDefinition, ...] = (
    EnrichmentDefinition(
        key="attack-mapping",
        name="ATT&CK mappings",
        wave="implemented",
        description="Connect source behaviors to versioned ATT&CK techniques.",
        implemented=True,
    ),
    EnrichmentDefinition(
        key="alias-resolution",
        name="Alias resolution",
        wave="implemented",
        description="Resolve source names to canonical actor identities with provenance.",
        implemented=True,
    ),
    EnrichmentDefinition(
        key="historical-correlation",
        name="Historical correlation",
        wave="implemented",
        description="Retain source observations so adversary change can be compared over time.",
        implemented=True,
    ),
    EnrichmentDefinition(
        key="geoip-asn",
        name="Basic GeoIP and ASN",
        wave="first_wave",
        description="Add network ownership and geography context with database provenance.",
    ),
    EnrichmentDefinition(
        key="external-reputation",
        name="External reputation APIs",
        wave="later",
        description="Add only when a defined use case justifies another external dependency.",
    ),
)


def get_integration(key: str) -> IntegrationDefinition | None:
    return next((item for item in INTEGRATION_CATALOG if item.key == key), None)
