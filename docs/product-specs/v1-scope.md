# WATCHTOWER V1 scope

Status: baseline approved for Task 01 by the user's instruction to start the
next task on 2026-09-27. Later-task decisions below remain open.

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

The first usable milestone ends at Task 09: evidence-backed actor lookup,
timeline and search. It is not completion of the entire V1 scope above.
The initial release is proposed as backend/API first; no frontend implementation
task is present in the supplied sequence.

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

SvelteKit, TypeScript, shadcn-svelte, Tailwind and ECharts remain the specified
frontend stack if a separate frontend task is approved. Provider/model choices,
hosting and retention policy remain open as listed below.

## Explicitly out of scope

Forecasting, autonomous agents, multi-agent orchestration, AI actor merging,
automatic editorial or Sigma generation, a scraping fleet, arbitrary URL
ingestion, paid-source integration, full STIX schema replication, graph
databases, Kafka, Kubernetes, sharding, microservices and unmeasured caching.
Frontend implementation and production deployment are not authorized by this
planning task. A release must not claim these features implicitly.

## Human Decisions Required

| Decision | Proposed choice | Required before |
| --- | --- | --- |
| Missing authoritative documents | Supply AGENTS.md/workflow reference, or explicitly adopt this proposal as the baseline without them | Task 01 |
| Release boundary | Backend/API V1 covering Tasks 01–18; frontend separately scoped | Task 01 |
| Write access and publication | Local/operator-only ingestion initially; authenticated administration before remote access; public reads expose published material only | Task 08 and advisory contract |
| AI execution and data policy | Select embedding/LLM provider, permitted source data and budget; disabled until configured | Task 10 |
| Evidence retention and hosting | Choose retention/licensing policy and S3-compatible target; local adapter for development | Production evidence intake/deployment |
| Deployment exposure | Select hosting, authentication owner and operational resource limits | Task 16 |

Other choices such as internal module names and local development ports are
routine implementation decisions, not separate approval gates.

## V1 acceptance

A fixture-backed source can be ingested and replayed without duplicate
observations; actor queries expose timelines with evidence; ambiguous aliases
remain unresolved; deterministic search has evaluated relevance; RAG outputs
are evaluated and cited; artifacts retain originals; STIX exports validate;
advisory updates preserve history. Automated checks, migrations, performance
measurements and deployment/security documentation must support a truthful
Task 18 audit. Numerical performance and evaluation targets must be established
with representative workloads in their corresponding tasks, not invented here.
