# WATCHTOWER integration status

Status: Task 38 implementation candidate, 2026-11-23.

This inventory distinguishes working runtime integrations from infrastructure
and later source candidates. A source is called integrated only when its fixed
retrieval contract, source registration, immutable raw evidence, normalization,
deduplication, durable job routing, provenance and tests exist.

## Implemented intelligence sources

| Integration | Runtime mapping | Retrieval and content boundary |
| --- | --- | --- |
| MITRE ATT&CK Enterprise | Versioned STIX intrusion sets become imported observations through the existing deterministic pipeline. | Fixed ATT&CK 19.2 URL, exact raw bytes and ATT&CK license notice. |
| MISP Galaxy | Versioned threat-actor clusters become internal actor candidates, observations and source-preserved aliases. | Pinned `2026031300` threat-actor JSON; cluster UUIDs, synonyms, references and CC0/BSD provenance retained. Exact-name matching may link an existing actor; ambiguous aliases never auto-merge. |
| CISA KEV | Catalog entries become internal imported observations and searchable vulnerability records. | Official KEV JSON; CVE, vendor/product, description, date added, due date, remediation, ransomware-use, forensic and CWE fields retained. WATCHTOWER does not invent CVSS or severity. |
| Microsoft Threat Intelligence | Topic-feed items become internal imported observations with evidence citations. | Official threat-intelligence topic RSS; metadata and inert supplied summary only. Full article bodies are not fetched or republished. |
| Unit 42 | Feed items become internal imported observations with evidence citations. | Official RSS; metadata and inert supplied summary only. Full article bodies are not fetched or republished. |
| The Hacker News | Feed items become internal imported observations with evidence citations. | Publisher RSS through FeedBurner; metadata and inert supplied summary only. It is explicitly secondary reporting and cannot alone establish high-confidence attribution. |

All six have distinct `IngestionJobKind` values, durable asynchronous processing
and replay-safe operator actions in `/admin/integrations`. None requires an API
key. Retrieval uses a fixed HTTPS URL, no redirects, identity encoding, bounded
timeouts and byte limits, expected media types and no ambient proxy credentials.

Every connector stores exact response bytes in the configured raw-evidence
object store before normalization. Content-hash deduplication makes an identical
response a no-op. Source-native objects receive normalization-ledger outcomes,
and malformed, empty, oversized, redirected or unavailable responses fail
closed.

## Publication boundary

Connector success is not editorial approval. New source, actor, alias,
observation, vulnerability and evidence records remain `internal` by default.
The public search and actor routes continue to fail closed until each applicable
record is explicitly published through an approved editorial process.

Publication feeds never become WATCHTOWER assessments. Their records use
`OBSERVED · imported`, preserve the publisher URL and do not contain full
article HTML. Source strings are rendered as inert text by the existing UI.

## Supporting runtime integrations

| Integration | Current use | Boundary |
| --- | --- | --- |
| PostgreSQL with pgvector | Intelligence records, search and optional retrieval storage | Required application database; live retrieval execution remains disabled. |
| Redis with Dramatiq | Durable bounded ingestion jobs | Required when the worker processes queued jobs. Messages contain only job UUIDs. |
| Local object storage | Immutable raw-evidence objects in local/private development | Default local adapter. |
| Amazon S3 adapter | Optional raw-evidence storage | Code and configuration exist; no deployed AWS environment is claimed. |
| OIDC/Cognito | Optional operator authentication | Static local operator authentication remains available; Cognito is not deployed. |
| STIX 2.1 | Validated export of the documented subset | Export only; not a general inbound TAXII feed. |
| Sigma | Parsing and preservation of technical artifacts | No automatic rule generation. |

## Planned and excluded sources

| Candidate | Status | Required decision |
| --- | --- | --- |
| Google Threat Analysis Group | Approved next official publication source; no connector | Select a stable official discovery contract and metadata/version behavior. |
| Malpedia | Later wave; no connector | Confirm access, license, attribution and family/actor mapping. |
| Securelist | Later wave; no connector | Define publication discovery, versioning and source attribution. |
| ESET Research | Later wave; no connector | Define publication discovery, versioning and source attribution. |
| Additional selected news | Later wave; no connector | Approve each publisher's reliability, licensing and deduplication policy. |
| AlienVault OTX | Not approved for this wave | Define pulse/indicator scope, API credentials, attribution and polling limits. |
| X/Twitter | Not approved for this wave | Confirm API access, licensing, retention and permitted content. |
| abuse.ch feeds | Candidate only | Select feeds and document redistribution, confidence and expiry semantics. |
| MISP/OpenCTI exchange | Candidate only | Choose push/pull ownership and map markings; distinct from MISP Galaxy data. |
| VirusTotal | Candidate only | Approve account tier, quotas and indicator-handling policy. |
| Generic STIX/TAXII | Candidate only | Define collection allowlists, trust markings, cursors and schema limits. |

Live RAG also remains unintegrated with a model provider. No LangChain,
Semantic Kernel or AutoGen dependency is present; the provider-neutral retrieval
boundary remains disabled by default.

## Operations

The operator integration page can queue one idempotent refresh for every
implemented connector and show its latest durable job state. It cannot edit
upstream URLs, add credentials, publish imported data or schedule recurring
jobs. Scheduling and editorial publication remain separate product decisions.

GitHub stores the repository, and GitHub Actions runs backend/frontend checks,
dependency audits, container scans and SBOM generation. Jira tracks delivery
work but its token is not a WATCHTOWER runtime integration.
