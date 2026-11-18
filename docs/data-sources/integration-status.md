# WATCHTOWER integration status

Status: audited 2026-11-18.

This inventory distinguishes working application integrations from repository
infrastructure and possible future data sources. A source is not described as
integrated until its connector, credentials, checkpointing, provenance,
normalization, retries and tests exist in the repository.

## Implemented runtime integrations

| Integration | Current use | Boundary |
| --- | --- | --- |
| MITRE ATT&CK Enterprise | Fixed-source STIX connector and deterministic normalization | The only implemented external intelligence feed |
| PostgreSQL with pgvector | Intelligence records, search and optional retrieval storage | Required application database; retrieval execution remains disabled |
| Redis with Dramatiq | Durable bounded ingestion jobs | Required when the worker processes queued jobs |
| Local object storage | Immutable raw-evidence objects in local/private development | Default V1 evidence adapter |
| Amazon S3 adapter | Optional raw-evidence object storage | Code and configuration exist; no deployed AWS environment is claimed |
| OIDC/Cognito | Optional operator authentication | Static local operator authentication remains available; Cognito is not deployed |
| STIX 2.1 | Validated export of the documented subset | Export only; this is not a general inbound TAXII feed |
| Sigma | Parsing and preservation of technical artifacts | No automatic rule generation |

## Delivery and operations integrations

- GitHub stores the repository and GitHub Actions runs frontend, backend,
  dependency, container, Trivy and SBOM checks.
- Docker Compose runs PostgreSQL/pgvector, Redis, migrations, the API, worker
  and production web build for a loopback-only local demonstration. A
  deterministic development-only seed command supplies the fictional V1
  researcher journey and can safely remove only its marked graph.
- AWS infrastructure templates and staging runbooks exist, but deployment and
  operational proof remain V2 work.
- Jira tracks project work. Jira credentials belong to the connected project
  management boundary and are not consumed by the WATCHTOWER runtime.

## Not integrated

| Candidate source | Status | Main decision before implementation |
| --- | --- | --- |
| MISP Galaxy | Approved first wave; no connector | Select versioned galaxy collections and preserve cluster, synonym and source metadata |
| CISA | Approved first wave; no connector | Start with KEV and define source-version, CVE update and checkpoint behavior |
| Microsoft Threat Intelligence | Approved first wave; no connector | Select official feeds/publications and define stable retrieval and attribution boundaries |
| Google Threat Analysis Group | Approved first wave; no connector | Define publication discovery, article versioning and actor/alias evidence mapping |
| Unit 42 | Approved first wave; no connector | Define publication discovery, attribution and campaign/technique extraction rules |
| Malpedia | Approved second wave; no connector | Confirm access, license, attribution and family/actor relationship mapping |
| Securelist | Approved second wave; no connector | Define publication discovery, versioning and source attribution |
| ESET Research | Approved second wave; no connector | Define publication discovery, versioning and source attribution |
| Selected news sources | Approved second wave; source list not yet selected | Establish editorial selection, licensing, deduplication and reliability criteria |
| AlienVault OTX | No client, API-key setting, pulse cursor or normalization adapter | Define allowed pulse/indicator scope, attribution and polling limits |
| X/Twitter | No API client, credentials, collection job or normalization adapter | Confirm API access, licensing, retention and permitted content before design |
| abuse.ch feeds | No connector | Select feeds and document redistribution, confidence and expiry semantics |
| MISP/OpenCTI platform exchange | No connector | Choose push/pull ownership and map source identity and marking rules; distinct from MISP Galaxy content |
| VirusTotal | No connector | Approve account tier, quotas, data handling and indicator lookup policy |
| Generic STIX/TAXII | No inbound connector | Define collection allowlists, trust markings, cursors and schema limits |

Live RAG is also not integrated with a model provider. The retrieval boundary is
disabled by default and no LangChain, Semantic Kernel or AutoGen dependency is
present.

## Approved source sequence

The owner-approved source scope is centered on understanding how an adversary
changes over time. It does not optimize for collecting the largest possible IOC
volume.

After V1 UI acceptance, plan these connectors separately from the integration
administration and Docker/demo work:

1. MITRE ATT&CK, MISP Galaxy, CISA, Microsoft Threat Intelligence, Google TAG
   and Unit 42 form the first source wave. MITRE ATT&CK is already implemented;
   the other five sources still require source-specific contracts.
2. Malpedia, Securelist, ESET and a deliberately selected set of news sources
   follow as the pipeline and editorial controls mature.

X/Twitter, AlienVault OTX, abuse.ch, VirusTotal and generic MISP/OpenCTI or
STIX/TAXII exchange remain unimplemented candidates. They are not part of the
approved first or second source wave and must not displace it without a later
product decision.

## Approved enrichment sequence

Start with ATT&CK mappings, conservative alias resolution, historical
correlation and basic GeoIP/ASN context. These enrichments directly support the
adversary-evolution workflow while preserving provenance and uncertainty.

External reputation APIs are deferred until a concrete research or detection
use case requires them. Any later reputation provider needs a separate review
of quotas, licensing, permitted retention, confidence semantics and how its
result affects the evidence trail.

Every connector should reuse the existing raw-evidence, normalization and job
boundaries while owning its fixed source allowlist, credentials, rate limits,
cursor/checkpoint, provenance mapping, retry classification and replay tests.
