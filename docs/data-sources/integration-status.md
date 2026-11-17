# WATCHTOWER integration status

Status: audited 2026-11-17.

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
- Docker Compose defines PostgreSQL/pgvector and Redis for local development.
  Full API, worker and web composition is scheduled for Task 35.
- AWS infrastructure templates and staging runbooks exist, but deployment and
  operational proof remain V2 work.
- Jira tracks project work. Jira credentials belong to the connected project
  management boundary and are not consumed by the WATCHTOWER runtime.

## Not integrated

| Candidate source | Status | Main decision before implementation |
| --- | --- | --- |
| AlienVault OTX | No client, API-key setting, pulse cursor or normalization adapter | Define allowed pulse/indicator scope, attribution and polling limits |
| X/Twitter | No API client, credentials, collection job or normalization adapter | Confirm API access, licensing, retention and permitted content before design |
| CISA Known Exploited Vulnerabilities | No connector | Define CVE update/checkpoint behavior and source-version retention |
| abuse.ch feeds | No connector | Select feeds and document redistribution, confidence and expiry semantics |
| MISP or OpenCTI | No connector | Choose push/pull ownership and map source identity and marking rules |
| VirusTotal | No connector | Approve account tier, quotas, data handling and indicator lookup policy |
| Generic STIX/TAXII | No inbound connector | Define collection allowlists, trust markings, cursors and schema limits |

Live RAG is also not integrated with a model provider. The retrieval boundary is
disabled by default and no LangChain, Semantic Kernel or AutoGen dependency is
present.

## Recommended connector sequence

After V1 UI acceptance, plan connectors separately from Task 35's Docker/demo
work. Start with CISA KEV, AlienVault OTX and selected abuse.ch feeds because
they directly improve CVE and indicator discovery without depending on social
media access. Add X only after its access, cost, licensing and retention policy
are approved.

Every connector should reuse the existing raw-evidence, normalization and job
boundaries while owning its fixed source allowlist, credentials, rate limits,
cursor/checkpoint, provenance mapping, retry classification and replay tests.
