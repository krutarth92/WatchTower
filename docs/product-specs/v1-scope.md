# WATCHTOWER V1 scope

Status: backend baseline approved on 2026-09-27; release boundary amended on
2026-10-21 to include the first-party UI and defer AWS productionization to V2.

## Product and intended user

WATCHTOWER helps a threat intelligence researcher understand an adversary's
behavior over time and trace each important claim to its evidence. The core
flow is adversary, behavior, evolution, context, evidence, interpretation and
action. IOCs support the research; they are not the primary organizing model.

This proposal is derived from the supplied Tasks 00–18 and two local guides.
The referenced AGENTS.md and system workflow reference were not supplied.
It does not claim to reconstruct their contents.

## V1 deliverables

1. A Python backend with health/readiness checks, validated configuration,
   migrations, structured logs and automated checks.
2. Actors, source-specific aliases, sources, raw evidence references,
   observations, behaviors, techniques, campaigns, evidence and relationships.
   Important observations retain source provenance, explicit timestamps and
   confidence where applicable. Imported facts and generated assessments remain
   distinguishable. Schema and identifier details are designed in Task 02.
3. Immutable raw content and retrieval metadata, content hashes, source URLs,
   timestamps, processing state and replayable intake. Keep content objects
   separate from normalized database records.
4. One reference connector for a versioned MITRE ATT&CK STIX dataset, followed
   by deterministic parsing, validation, normalization and deduplication.
   Ordinary tests use local fixtures; source access policy is checked in Task 04.
5. Conservative actor resolution: preserve source labels, record reasons and
   evidence, leave ambiguity unresolved, and support auditable manual correction.
6. Read APIs under /api/v1 for actor lookup, aliases, observations, techniques,
   evidence and timelines, with stable errors, filtering and cursor pagination.
7. Replay-safe Dramatiq jobs backed by Redis, bounded retries and observable
   job states. Administrative submission must not become a public write API.
8. Deterministic PostgreSQL search with a curated relevance evaluation set.
9. An explicit research RAG path using pgvector, source citations, actor/time
   filtering, context budgets and insufficient-evidence responses. Ordinary
   reads and normalization do not invoke a model. Evaluate retrieval, citations
   and unsupported claims before enabling it for users.
10. Faithful STIX/Sigma/ATT&CK artifact storage and validation where supported;
    export only a documented, valid STIX 2.1 subset.
11. Measured API/pipeline performance, bounded ingestion, security hardening,
    CI checks, deployment/rollback documentation and a readiness audit.
12. A living advisory backend contract with evidence links, timestamped updates
    and preserved history. Proposed publication policy: drafts are private and
    only explicitly published advisories appear in public reads.
13. A first-party web interface for local/private use that presents the core
    researcher flow over the versioned API: search, actor context and timeline,
    evidence/provenance and published advisories. The UI must preserve
    OBSERVED/ASSESSED distinctions and must not expose drafts or administrative
    operations to unauthenticated users. Its exact screens and operator workflow
    are defined and accepted in a dedicated UI plan before implementation.

The backend milestone ends with the implemented and tested V1 APIs. Product V1
is complete only after the first-party UI is accepted for local/private use.
Internet-facing AWS deployment and operational proof are sequenced into
`docs/product-specs/v2-productionization-scope.md`.

## Non-negotiable behavior

- Keep OBSERVED and ASSESSED distinct; FORECAST generation is outside V1.
- Never overwrite sourced facts or raw artifacts with model interpretation.
- Provenance survives ingestion, normalization, resolution, retrieval and export.
- Retries and replay do not create uncontrolled duplicates or hide rejections.
- Treat fetched content as untrusted data; never execute it.
- No automatic identity merge based only on fuzzy similarity or an LLM.
- Public reads cannot expose draft material or administrative write operations.

## Architecture and dependencies

Use one Python codebase with API and worker entry points, one PostgreSQL
database, Redis for jobs and an object-storage boundary. Workers are processes
of the same application, not independently owned microservices. Start local
development with the API on the host and PostgreSQL/Redis in Docker Compose.
Use a local object-storage adapter in development; select S3-compatible hosting
before deployment. No new services are required for Task 01 beyond its database
and Redis baseline.

Use Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic and psycopg.
PostgreSQL supplies JSONB/full-text search; pgvector is added with retrieval.
Use uv, pytest, Ruff and Pyright. Move canonical dependency declarations into
pyproject.toml during Task 01, commit uv.lock, and generate requirements exports
to retain the requested pip-compatible files without duplicate manual editing.
Resolve versions and test compatibility at implementation time; existing ranges
are not a validated lock. Do not install future-task dependencies preemptively.

The approved frontend baseline is SvelteKit, TypeScript, shadcn-svelte,
Tailwind and ECharts. The dedicated UI plan must select compatible current
versions, define an API-client boundary and add appropriate frontend checks
without weakening the existing backend CI. Provider/model choices and live RAG
remain open as listed below.

## Explicitly out of scope

Forecasting, autonomous agents, multi-agent orchestration, AI actor merging,
automatic editorial or Sigma generation, a scraping fleet, arbitrary URL
ingestion, paid-source integration, full STIX schema replication, graph
databases, Kafka, Kubernetes, sharding, microservices and unmeasured caching.
AWS production deployment and its operational proof are outside V1 and belong
to the separately gated V2 productionization scope. A release must not claim
public production readiness or optional features implicitly.

## Human Decisions Required

| Decision | Proposed choice | Required before |
| --- | --- | --- |
| Missing authoritative documents | Supply AGENTS.md/workflow reference, or explicitly adopt this proposal as the baseline without them | Task 01 |
| Release boundary | Backend plus first-party local/private UI in V1; AWS productionization in V2 | Decided 2026-10-21 |
| Write access and publication | Local/operator-only ingestion initially; authenticated administration before remote access; public reads expose published material only | Task 08 and advisory contract |
| AI execution and data policy | Select embedding/LLM provider, permitted source data and budget; disabled until configured | Task 10 |
| Evidence retention and hosting | Keep local adapter for V1; choose retention/licensing policy and deploy the approved S3 boundary in V2 | V2 productionization |
| Deployment exposure | Keep V1 local/private; select hosting, authentication owner and operational resource limits before V2 deployment | V2 productionization |

Other choices such as internal module names and local development ports are
routine implementation decisions, not separate approval gates.

## V1 acceptance

A fixture-backed source can be ingested and replayed without duplicate
observations; actor queries expose timelines with evidence; ambiguous aliases
remain unresolved; deterministic search has evaluated relevance; RAG outputs
are evaluated and cited; artifacts retain originals; STIX exports validate;
advisory updates preserve history. Automated checks, migrations, performance
measurements and deployment/security documentation must support a truthful
backend audit. The UI must make the evidence-backed search, actor timeline,
provenance and published-advisory flow usable without bypassing API visibility
or authentication rules. Numerical production performance and operational
targets are established with representative V2 workloads, not invented in V1.
