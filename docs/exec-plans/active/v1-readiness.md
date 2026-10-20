# WATCHTOWER V1 readiness audit

Status: complete, verified and approved; remediation status updated through the
locally verified Task 25 application boundary.
Date: 2026-10-19.
Scope: approved backend/API V1 in `docs/product-specs/v1-scope.md`.

## Verdict

WATCHTOWER is **ready for local development and private staging evaluation**.
It is **not ready for an internet-facing production release**.

The core backend contracts are implemented and pass the complete local
PostgreSQL-backed suite. Repository, public-read visibility and the
identity-aware application boundary are in place. The remaining release
blockers include deployed Cognito/ALB/WAF controls, shared object storage and
retention, backup/restore operations, and monitored production infrastructure.

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
| Repository structure | **Complete** | The Python package, migrations, tests, scripts, Docker, workflows and documentation are tracked on protected `main`, with branch-neutral hosted CI and a clean local/remote baseline. |
| Data model | **Complete** | `db/models.py` and eleven Alembic revisions cover actors, aliases, sources, raw evidence, observations, behaviors, techniques, campaigns, relationships, normalization, resolution audit, jobs, embeddings, artifacts, advisories and publication visibility. Database constraint tests pass. |
| Provenance | **Complete** | Source, RawEvidence and Evidence references persist across normalization, actor timelines, artifacts, RAG citations and STIX export. Tests cover end-to-end provenance and separate imported observations from WATCHTOWER assessments. |
| Ingestion | **Complete** | The fixed, versioned MITRE ATT&CK STIX connector validates destination, HTTPS response, redirects, encoding, media type, timeouts and size. Fixture tests cover success, failure, replay and partial record rejection without requiring internet access. |
| Raw evidence | **Partial** | Immutable hashing, source-scoped deduplication, replay state, local storage and a private KMS-encrypted S3 adapter are implemented. The AWS template defines versioning, governance Object Lock, blocked public access and a no-delete runtime role. Deployment, source-policy review for future connectors and recovery evidence remain open. |
| Normalization | **Complete** | The parse → normalize → validate → deduplicate → persist ledger is deterministic and replay-safe. Conflict, older-version, malformed and unsupported-record behavior is tested. The deliberate intrusion-set-only mapping matches the approved narrow reference connector. |
| Actor resolution | **Complete** | Exact/known rules, unresolved ambiguity, review-only similarity candidates, manual correction and immutable decision audit are implemented and tested. Fuzzy similarity never auto-links an actor. |
| Actor timeline | **Complete** | Stable actor lookup, aliases, observations, evidence, techniques, date/type filtering and opaque cursor pagination are implemented with bounded eager loading. Public reads fail closed and include only explicitly published records with published provenance. |
| API quality | **Partial** | Versioned routes, strict validation, stable error envelopes, request IDs, body limits, gzip, bounded queries, publication filtering, cursor-paginated search, OpenAPI, trusted-host enforcement and explicit proxy trust are present. Production rate limits and TLS still require the approved AWS edge deployment. |
| Search | **Partial** | PostgreSQL full-text search has stable ranking, publication filters, GIN/generated-vector support, 11 rank-1 evaluation cases and scoped keyset pagination. It lacks a production-scale relevance corpus and production-like latency result. |
| RAG grounding | **Partial** | pgvector storage, actor/time filtering, deterministic reranking, context budgets, citations, OBSERVED/ASSESSED enforcement and insufficient-evidence behavior are evaluated with deterministic providers. No approved live provider, automatic embedding ingestion/backfill or measured vector index exists; the endpoint correctly returns unavailable by default. |
| Technical artifacts | **Complete** | STIX 2.1, Sigma and ATT&CK technique records preserve exact original content, hashes, parsed structure, validation failures and provenance. Reads are operator-only and tests cover valid, invalid, duplicate and provenance behavior. |
| STIX export | **Complete** | The documented actor-centered STIX 2.1 subset is deterministic, conservative, operator-only and validates with the official library. Unsupported semantics are deliberately omitted rather than guessed. |
| Async jobs | **Complete** | Durable PostgreSQL state, UUID-only Redis messages, idempotent submission, leases, bounded retry/backoff, restart recovery, backpressure and queue metrics are implemented and tested. Redis is transport rather than the source of truth. |
| Living advisories | **Complete** | Draft privacy, immutable published revisions, typed sections, evidence/entity links and sequenced timestamped updates are implemented and tested. Earlier published revisions remain intentionally durable. |
| Tests | **Complete** | The current suite contains 102 passing tests covering the database, API, workers, OIDC/static authentication, roles, attribution, security boundaries, evaluations and migrations. The suite runs against PostgreSQL with every warning treated as an error; Ruff, formatting and Pyright pass. Starlette TestClient uses its supported `httpx2` backend. |
| Security | **Partial** | Application controls include strict input boundaries, stable errors, Cognito-compatible access-token verification, `operator`/`publisher` roles, authenticated advisory attribution, production host/proxy fail-closed settings, safe fixed-source fetching, publication filtering, log redaction and security headers. Deployed Cognito/MFA/account lifecycle, ALB/ACM/WAF, private production services, egress control and operational incident ownership remain release gates. |
| CI/CD | **Partial** | Protected `main` requires branch-neutral hosted backend, dependency-audit and container checks. Actions are commit-pinned; CI performs locked install, lint, type/migration/tests, package build, dependency audit, image build/smoke/Trivy scan, and retains a verified commit-specific CycloneDX SBOM for 30 days. Durable image publication/attestation and staging environment validation remain open. |
| Deployment | **Blocked** | A careful private Ubuntu EC2 staging runbook and SHA-based deployment/rollback script exist. No approved/available staging host, secrets, identity provider, production network/storage design, backup service or monitoring environment is evidenced. The runbook explicitly forbids public exposure. |
| Observability | **Partial** | JSON logs, request/correlation IDs, slow-request logs, health/readiness, durable job states and queue metrics exist. There is no production metrics exporter/dashboard, alert routing, log retention/access policy, backup-age alert or exercised incident response. |
| Documentation | **Partial** | Setup, model, ingestion, normalization, resolution, API, RAG, artifact, STIX, performance, security, deployment and advisory contracts are present and consistent with V1. The mandatory `docs/design/system-workflow-reference.md` remains absent and its contents were not invented. |

Result count: **12 complete, 8 partial, 0 missing, 1 blocked**.

## Gap and remediation register

| ID | Area | Exact gap | Risk | Smallest remediation task | Dependency | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | Repository | Remediated by Tasks 19–20: the reviewed repository is tracked on protected `main`, branch-neutral CI runs on every push/PR, and the three required checks are enforced without bypass. | Repository history and checks still require normal maintenance. | Keep action/dependency updates reviewed and preserve the protected workflow. | Repository ownership. | **Complete** |
| G02 | Publication | Remediated by Task 21: public actor and cross-entity search reads require explicit per-record publication and default all existing/new canonical records to internal. | A publication operation without identity or review could still make a wrong record public. | Implement an authenticated, attributable editorial workflow only after G03 identity and withdrawal policy are approved. | Operator identity and editorial/withdrawal policy. | **P0 read boundary complete; operations pending** |
| G03 | Operator identity | Task 25 implemented Cognito-compatible access-token verification, explicit `operator`/`publisher` roles, stable auth errors, structured subject audit fields and authenticated advisory attribution. Task 27 adds validation-only Cognito IaC with admin-only users, mandatory MFA, deletion protection, short access tokens and exact application outputs, plus a lifecycle/acceptance runbook. No user pool, user, group assignment or revocation exercise is deployed. | The repository prevents caller-forged attribution and encodes identity controls, but production identity assurance does not exist until the boundary and operational ownership are proven in the target account. | Review and execute the template change set, assign lifecycle/revocation owners, provision test operators and run the documented token, role, attribution and disablement acceptance checks. | Authorized AWS deployment, identity/security owner. | **P0 repository boundary complete; deployment proof pending** |
| G04 | Production edge | Task 25 implemented trusted-host/proxy handling. Task 27 adds validation-only ALB/ACM/WAF IaC with HTTPS redirect/listener, private-target SG reference, hardened header attributes, retained access logs, managed WAF protections, required measured public/operator limits and redacted WAF logs. No edge, DNS record, certificate association, target proof or alert is deployed. | Direct public exposure still permits abuse and transport-policy failures until target isolation, TLS, forwarding behavior, shared limits, logs and alerts are proven in the target environment. | Review and execute the template change set, create the approved DNS alias, then run and record all nine edge acceptance checks and rollback. | Authorized AWS deployment, network/DNS/certificate and monitoring owners. | **P0 repository boundary complete; deployment proof pending** |
| G05 | Raw storage | Task 26 implements the S3 adapter, fail-closed production selection, immutable writes, integrity audit, KMS/versioning/Object Lock template, 365-day governance retention and no-delete runtime role. No target bucket or disposable S3 endpoint has been exercised. | Repository controls do not prove the target account policy, credentials, audit trail or recovery path. A future connector can still violate an unreviewed source policy. | Deploy the approved template, run the opt-in S3 integration contract, inspect effective IAM/bucket controls, and require retention/licensing review before enabling each new connector. | Authorized AWS account, recovery/records owner and connector policy owner. | **P0 repository boundary complete; deployment proof pending** |
| G06 | Data operations | Task 26 defines private encrypted Multi-AZ RDS PostgreSQL 17, verified TLS, separate runtime/migration roles, 35-day PITR, daily 90-day governed backup, a read-only integrity audit and coordinated restore runbook. No AWS resources or recovery points were created and no external restore was rehearsed. | A host/database/storage failure can still cause an untested outage until the target services and measured recovery evidence exist. | Provision the reviewed services and roles, then execute the runbook with actual backup IDs, integrity output, measured RPO/RTO and reviewer sign-off. | Authorized AWS provisioning, operations owner and restore-test window. | **P0 repository boundary complete; restore evidence pending** |
| G07 | Deployment | The private staging workflow/runbook has not run against an approved EC2 environment. | Shell, Compose, migration and rollback assumptions remain locally validated only. | Provision private staging, configure protected environment secrets/reviewers, deploy one immutable SHA, verify API/worker/migration, then rehearse application rollback. | G01 plus approved AWS host and secrets. | **P1** |
| G08 | CI/release | Hosted CI, required checks and retained commit-specific SBOM evidence are active. No durable registry image or signed provenance attestation exists. | A deployer cannot yet verify that a registry image was produced by the reviewed workflow. | Select the release registry/policy, publish by immutable digest, and attest the durable image subject and SBOM. | Registry and release policy. | **P1 partially remediated** |
| G09 | Observability | No deployed service/database/host metrics, dashboards, actionable alerts, central log policy or incident exercise exists. | Failures, queue backlog, storage pressure and backup expiry may remain unnoticed. | Define a minimum signal/owner/runbook set and deploy alerts for readiness, error/slow rate, pool saturation, queue depth/age, disk and backup age. | Monitoring/log platform and on-call ownership. | **P1** |
| G10 | Performance | Measurements are local synthetic baselines without production hardware, network, representative corpus or release SLO. | Capacity and latency claims cannot support a public service. | Re-run API and pipeline benchmarks in staging with a licensed representative dataset; set initial SLOs and resource limits from results. | G07, representative data and expected traffic. | **P1** |
| G11 | RAG execution | No provider/data-egress/budget decision, live adapter, ingestion embedding hook or vector index is approved. | Advertising live research would yield 503; a rushed provider could leak source data or create unbounded cost. | Decide local versus external provider and permitted data/budget, then implement one adapter, controlled backfill and measured retrieval evaluation before enabling the endpoint. | Explicit AI provider, privacy and budget approval. | **P2** |
| G12 | Search/API | Remediated by Task 24: search uses an opaque scoped keyset cursor over score, entity-type priority, case-folded title and UUID, with no-gap/no-duplicate regression coverage. | Clients can enumerate matching published results without offset drift; live mutations can still change later pages, as expected without snapshot transactions. | Preserve sort-key and cursor compatibility when ranking changes; version any future cursor shape. | Stable visibility contract from G02. | **Complete** |
| G13 | Advisory policy | Published revisions have no withdrawal/redaction state and remain readable forever. | Later legal or source-policy removal cannot be represented without an unsafe destructive edit. | Approve and model an audited withdrawal state with explicit public behavior; preserve revision history for authorized review. | Editorial/legal policy. | **P2** |
| G14 | Authoritative docs | `docs/design/system-workflow-reference.md` is absent. | Future work may diverge from an unknown authoritative workflow. | Supply the document or record an explicit decision that the approved V1 scope and current design set replace it. | Project owner. | **P2** |
| G15 | Test tooling | Remediated by Task 23: `httpx2` is locked as a development dependency, Starlette TestClient selects it, and pytest makes all warnings fatal. Production connectors retain their separate `httpx` runtime dependency. | Future dependency incompatibilities now fail the suite rather than appearing as non-blocking warnings. | Keep the two client roles explicit and review dependency updates through the locked CI suite. | Upstream FastAPI/Starlette/httpx2 compatibility. | **Complete** |

## Recommended final task list

Do not combine these into one implementation task. Each item should retain a
separate review checkpoint.

1. **P0 — Deploy and prove the approved production security boundary**: remaining G03 and G04 operations work.
2. **P0 — Deploy and prove durable evidence/data operations**: remaining G05 and G06 operations work.
3. **P1 — Exercise private staging and rollback**: G07.
4. **P1 — Add operational monitoring and production-like capacity evidence**:
   G09 and G10.
5. **P1 — Publish and attest an immutable release image**: remaining G08 work.
6. **P2 — Decide optional product policies**: live RAG (G11), advisory
   withdrawal (G13), and the missing workflow authority (G14).

G12 and G15 are complete as of Tasks 24 and 23 and are no longer in the
remaining task list.

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

### Post-audit remediation update (2026-10-01)

G01 is complete: the reviewed repository is tracked on `main`, preserves the
pre-existing remote `LICENSE` history, and is published at
`https://github.com/krutarth92/WatchTower`. Hosted CI run
[#9](https://github.com/krutarth92/WatchTower/actions/runs/36821521653) passed
the backend, dependency-audit and container jobs. This resolves the hosted-run
portion of G08. Task 20 added enforced branch-neutral required checks. Task 21
added fail-closed canonical publication visibility. Task 22 added a verified,
checksum-bound CycloneDX SBOM retained for 30 days from the exact scanned image.
Durable image publication and provenance attestation remain open under G08, so
the audit's production-readiness verdict is unchanged.

The user approved the audit on 2026-10-01. Before remediation began, the report
was inspected in full and checked for all required sections, 21 classified audit
rows, 15 gap records and trailing whitespace. Every requested area was present,
the evidence paths existed, and the recorded Git finding was reconfirmed: zero
tracked paths and no local HEAD before fetching the remote. Task 18 changed only
documentation, so application checks were not repeated for this transition; its
recorded 85-test/static/Alembic validation remains applicable to the unchanged
application state.
