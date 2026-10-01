# WATCHTOWER V1 readiness audit

Status: complete, verified and approved; Git/hosted-CI remediation started.
Date: 2026-10-01.
Scope: approved backend/API V1 in `docs/product-specs/v1-scope.md`.

## Verdict

WATCHTOWER is **ready for local development and private staging evaluation**.
It is **not ready for an internet-facing production release**.

The core backend contracts are implemented and pass the complete local
PostgreSQL-backed suite. The remaining release blockers are repository
publication, visibility controls for actor/search reads, identity-aware
administration, production edge controls, shared object storage and retention,
backup/restore operations, and monitored production infrastructure.

This audit does not treat the absent frontend as a defect. The approved V1 scope
is backend/API first and says frontend implementation requires separate
approval. It also does not count disabled live RAG as a security failure:
provider-neutral grounding is evaluated, while live execution correctly remains
off until its data/provider/budget decision is made.

## Status definitions

- **Complete:** the approved V1 requirement is implemented, documented and
  validated in the current workspace.
- **Partial:** a usable implementation exists, but a named V1 or release
  requirement remains.
- **Missing:** no implementation or usable contract exists.
- **Blocked:** completion depends on an unresolved human decision or external
  environment that is unavailable in this workspace.

## Evidence-based requirement matrix

| Area | Status | Evidence and finding |
| --- | --- | --- |
| Repository structure | **Partial** | The Python package, migrations, tests, scripts, Docker, workflows and documentation have coherent locations. However, `git ls-files` returns 0, there is no HEAD commit, and all 22 top-level entries are untracked. The repository cannot reproduce, review or run hosted CI from this state. |
| Data model | **Complete** | `db/models.py` and ten Alembic revisions cover actors, aliases, sources, raw evidence, observations, behaviors, techniques, campaigns, relationships, normalization, resolution audit, jobs, embeddings, artifacts and advisories. Database constraint tests pass. |
| Provenance | **Complete** | Source, RawEvidence and Evidence references persist across normalization, actor timelines, artifacts, RAG citations and STIX export. Tests cover end-to-end provenance and separate imported observations from WATCHTOWER assessments. |
| Ingestion | **Complete** | The fixed, versioned MITRE ATT&CK STIX connector validates destination, HTTPS response, redirects, encoding, media type, timeouts and size. Fixture tests cover success, failure, replay and partial record rejection without requiring internet access. |
| Raw evidence | **Partial** | Immutable hashing, source-scoped deduplication, replay state and a safe local `ObjectStore` are complete. Only the local filesystem adapter exists; production S3-compatible storage, retention/licensing rules, encryption, backup and access policy are undecided. |
| Normalization | **Complete** | The parse → normalize → validate → deduplicate → persist ledger is deterministic and replay-safe. Conflict, older-version, malformed and unsupported-record behavior is tested. The deliberate intrusion-set-only mapping matches the approved narrow reference connector. |
| Actor resolution | **Complete** | Exact/known rules, unresolved ambiguity, review-only similarity candidates, manual correction and immutable decision audit are implemented and tested. Fuzzy similarity never auto-links an actor. |
| Actor timeline | **Partial** | Stable actor lookup, aliases, observations, evidence, techniques, date/type filtering and opaque cursor pagination are implemented with bounded eager loading. Actor records have no publication state, so the public route cannot distinguish publishable from internal/draft canonical records. |
| API quality | **Partial** | Versioned routes, strict validation, stable error envelopes, request IDs, body limits, gzip, bounded queries and OpenAPI are present. Search has limit-only pagination, actor/search visibility is not publication-aware, and production trusted-host/rate-limit/TLS behavior belongs to an absent edge. |
| Search | **Partial** | PostgreSQL full-text search has stable ranking, filters, GIN/generated-vector support and 11 rank-1 evaluation cases. It has no publication/visibility predicate, cursor pagination, production-scale relevance corpus or production-like latency result. |
| RAG grounding | **Partial** | pgvector storage, actor/time filtering, deterministic reranking, context budgets, citations, OBSERVED/ASSESSED enforcement and insufficient-evidence behavior are evaluated with deterministic providers. No approved live provider, automatic embedding ingestion/backfill or measured vector index exists; the endpoint correctly returns unavailable by default. |
| Technical artifacts | **Complete** | STIX 2.1, Sigma and ATT&CK technique records preserve exact original content, hashes, parsed structure, validation failures and provenance. Reads are operator-only and tests cover valid, invalid, duplicate and provenance behavior. |
| STIX export | **Complete** | The documented actor-centered STIX 2.1 subset is deterministic, conservative, operator-only and validates with the official library. Unsupported semantics are deliberately omitted rather than guessed. |
| Async jobs | **Complete** | Durable PostgreSQL state, UUID-only Redis messages, idempotent submission, leases, bounded retry/backoff, restart recovery, backpressure and queue metrics are implemented and tested. Redis is transport rather than the source of truth. |
| Living advisories | **Complete** | Draft privacy, immutable published revisions, typed sections, evidence/entity links and sequenced timestamped updates are implemented and tested. Earlier published revisions remain intentionally durable. |
| Tests | **Complete** | The current suite contains 85 passing tests covering the database, API, workers, security boundaries, evaluations and migrations. The suite runs against PostgreSQL; Ruff, formatting and Pyright pass. One upstream Starlette TestClient deprecation warning remains. |
| Security | **Partial** | Application controls include strict input boundaries, stable errors, constant-time operator token comparison, safe fixed-source fetching, log redaction and security headers. Public actor/search visibility, identity-aware operator authorization, edge TLS/rate limits, private production services, egress control and operational incident ownership remain release gates. |
| CI/CD | **Partial** | Pinned GitHub Actions define locked install, lint, type check, migrations, tests, package build, dependency audit, container build/smoke/Trivy scan and manual protected staging deployment. Nothing is tracked or pushed, no hosted run is evidenced, no SBOM is produced, and staging environment protections cannot be verified locally. |
| Deployment | **Blocked** | A careful private Ubuntu EC2 staging runbook and SHA-based deployment/rollback script exist. No approved/available staging host, secrets, identity provider, production network/storage design, backup service or monitoring environment is evidenced. The runbook explicitly forbids public exposure. |
| Observability | **Partial** | JSON logs, request/correlation IDs, slow-request logs, health/readiness, durable job states and queue metrics exist. There is no production metrics exporter/dashboard, alert routing, log retention/access policy, backup-age alert or exercised incident response. |
| Documentation | **Partial** | Setup, model, ingestion, normalization, resolution, API, RAG, artifact, STIX, performance, security, deployment and advisory contracts are present and consistent with V1. The mandatory `docs/design/system-workflow-reference.md` remains absent and its contents were not invented. |

Result count: **10 complete, 10 partial, 0 missing, 1 blocked**.

## Gap and remediation register

| ID | Area | Exact gap | Risk | Smallest remediation task | Dependency | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | Repository | No tracked files, HEAD commit or remote/hosted validation exists. | Work cannot be reviewed, reproduced, deployed or recovered through Git; workflows are inert. | Review ignored files, create the initial tracked commit, push it to the approved remote and require the first green CI run. | Repository/remote ownership and user authorization to publish. | **P0** |
| G02 | Publication | Actor and cross-entity search routes query canonical rows without a visibility state. | A future public deployment can expose internal or unreviewed intelligence. | Define the smallest canonical publication/visibility field and apply it consistently to actor detail, timeline and search queries with privacy regression tests. | Editorial/publication policy for canonical intelligence. | **P0** |
| G03 | Operator identity | One shared static token authenticates operations but supplies no trusted user identity, role, MFA or rotation trail. Advisory author fields are caller-supplied strings. | Compromise grants all operator access and audit attribution can be forged. | Put operator routes behind the approved identity provider/API gateway, map authenticated subject and roles into audit records, and document rotation/revocation. | Identity provider and security owner. | **P0** |
| G04 | Production edge | No deployed TLS proxy/API gateway, shared rate limit, trusted-host policy or forwarding-header trust boundary exists. | Direct public exposure permits abuse, ambiguous client identity and transport-policy failures. | Deploy and test one approved edge configuration with TLS, host/header/body/connection limits, shared rate limits and explicit forwarding trust. | Hosting/network choice and DNS/certificate ownership. | **P0** |
| G05 | Raw storage | Only `LocalObjectStore` is implemented; retention, source licensing, encryption and deletion policy are undecided. | A multi-host deployment can lose or inconsistently access evidence and may violate source policy. | Select the S3-compatible target and retention policy, implement the existing `ObjectStore` protocol, and add integration tests for immutability, replay and access failure. | Hosting, legal/licensing and retention decisions. | **P0** |
| G06 | Data operations | Production PostgreSQL/object backups, point-in-time policy and restore rehearsal are not implemented. Runtime least privilege and in-transit encryption are not demonstrated. | A host/database/storage failure can cause unrecoverable intelligence or an untested outage. | Provision private encrypted services/roles, automate coordinated backups, and execute a documented restore drill with recovery evidence. | AWS/service selection and operations owner. | **P0** |
| G07 | Deployment | The private staging workflow/runbook has not run against an approved EC2 environment. | Shell, Compose, migration and rollback assumptions remain locally validated only. | Provision private staging, configure protected environment secrets/reviewers, deploy one immutable SHA, verify API/worker/migration, then rehearse application rollback. | G01 plus approved AWS host and secrets. | **P1** |
| G08 | CI/release | Hosted CI status and branch protection are unverified; release output has no SBOM or signed/provenance-attested image. | Local success may diverge from hosted Linux, and image contents are harder to audit. | After G01, require the existing checks, add SBOM generation/retention and record the first green protected-branch run. | GitHub repository settings and release policy. | **P1** |
| G09 | Observability | No deployed service/database/host metrics, dashboards, actionable alerts, central log policy or incident exercise exists. | Failures, queue backlog, storage pressure and backup expiry may remain unnoticed. | Define a minimum signal/owner/runbook set and deploy alerts for readiness, error/slow rate, pool saturation, queue depth/age, disk and backup age. | Monitoring/log platform and on-call ownership. | **P1** |
| G10 | Performance | Measurements are local synthetic baselines without production hardware, network, representative corpus or release SLO. | Capacity and latency claims cannot support a public service. | Re-run API and pipeline benchmarks in staging with a licensed representative dataset; set initial SLOs and resource limits from results. | G07, representative data and expected traffic. | **P1** |
| G11 | RAG execution | No provider/data-egress/budget decision, live adapter, ingestion embedding hook or vector index is approved. | Advertising live research would yield 503; a rushed provider could leak source data or create unbounded cost. | Decide local versus external provider and permitted data/budget, then implement one adapter, controlled backfill and measured retrieval evaluation before enabling the endpoint. | Explicit AI provider, privacy and budget approval. | **P2** |
| G12 | Search/API | Search is capped at 100 results without cursor pagination. | Broad queries cannot enumerate a stable complete result set. | Add a deterministic cursor over score/type/title/UUID and regression tests for no gaps/duplicates, without changing ranking. | Stable visibility contract from G02. | **P2** |
| G13 | Advisory policy | Published revisions have no withdrawal/redaction state and remain readable forever. | Later legal or source-policy removal cannot be represented without an unsafe destructive edit. | Approve and model an audited withdrawal state with explicit public behavior; preserve revision history for authorized review. | Editorial/legal policy. | **P2** |
| G14 | Authoritative docs | `docs/design/system-workflow-reference.md` is absent. | Future work may diverge from an unknown authoritative workflow. | Supply the document or record an explicit decision that the approved V1 scope and current design set replace it. | Project owner. | **P2** |
| G15 | Test tooling | Starlette emits a TestClient/httpx deprecation warning. | A future dependency update may break API tests. | Follow the upstream migration path or compatible version update and require a warning-free test run. | Upstream FastAPI/Starlette/httpx compatibility. | **P3** |

## Recommended final task list

Do not combine these into one implementation task. Each item should retain a
separate review checkpoint.

1. **P0 — Establish the Git and hosted-CI baseline**: G01, then the hosted-run
   portion of G08.
2. **P0 — Add canonical publication visibility**: G02, followed by G12 only if
   complete search enumeration is required for release clients.
3. **P0 — Approve and implement the production security boundary**: G03 and G04.
4. **P0 — Approve durable evidence/data operations**: G05 and G06.
5. **P1 — Exercise private staging and rollback**: G07.
6. **P1 — Add operational monitoring and production-like capacity evidence**:
   G09 and G10.
7. **P1 — Finish release supply-chain evidence**: remaining G08 work.
8. **P2 — Decide optional product policies**: live RAG (G11), advisory
   withdrawal (G13), and the missing workflow authority (G14).
9. **P3 — Remove the test-client deprecation**: G15.

## Validation evidence

Task 17 was verified before this audit started:

- `.venv\Scripts\pytest.exe -q` with the local PostgreSQL URL: **85 passed**;
  one existing Starlette TestClient deprecation warning.
- `.venv\Scripts\ruff.exe check .`: passed.
- `.venv\Scripts\ruff.exe format --check .`: 125 files formatted.
- `.venv\Scripts\pyright.exe`: 0 errors, 0 warnings.
- `.venv\Scripts\alembic.exe heads`: `0218f83cad8e (head)`.
- `.venv\Scripts\alembic.exe current`: `0218f83cad8e (head)`.
- `.venv\Scripts\alembic.exe check`: no new upgrade operations.
- Live `/health`: `ok`; live `/ready`: `ready`.

Audit-specific checks:

- Read `AGENTS.md`, the complete approved V1 scope, relevant design,
  security, performance and deployment documents, all active execution-plan
  acceptance records, workflow definitions, source/test inventory and API route
  inventory.
- Confirmed `docs/design/system-workflow-reference.md` is missing.
- `git ls-files`: 0 tracked paths; `git rev-parse --verify HEAD`: no HEAD;
  `git status --short`: 22 untracked top-level entries.

## Acceptance record

- Evidence-based status for every requested audit area: **pass**.
- Complete/partial/missing/blocked vocabulary used: **pass**.
- Exact gap, risk, smallest remediation, dependency and priority for every
  partial/blocked area: **pass**.
- Recommended final task list produced: **pass**.
- Approved V1 scope preserved without promoting V2/R&D ideas: **pass**.
- No missing feature implemented and no application contract changed: **pass**.
- Missing workflow reference stated explicitly rather than reconstructed:
  **pass**.

## Transition verification

The user approved the audit on 2026-10-01. Before remediation began, the report
was inspected in full and checked for all required sections, 21 classified audit
rows, 15 gap records and trailing whitespace. Every requested area was present,
the evidence paths existed, and the recorded Git finding was reconfirmed: zero
tracked paths and no local HEAD before fetching the remote. Task 18 changed only
documentation, so application checks were not repeated for this transition; its
recorded 85-test/static/Alembic validation remains applicable to the unchanged
application state.
