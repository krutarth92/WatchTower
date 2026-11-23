# WATCHTOWER V1 readiness audit

Status: local/private V1 accepted; local validation, hosted CI, owner review and
Task 37 Jira closure passed by 2026-11-23.

Scope: the V1 backend and local/private SvelteKit UI. Internet-facing AWS
deployment and operational proof are explicitly deferred to
`docs/product-specs/v2-productionization-scope.md`.

## Verdict

WATCHTOWER is implemented, validated and accepted as a **local/private V1**.
The deterministic Docker workflow serves the complete researcher journey over
real APIs and data. The owner accepted the rendered desktop/mobile/search flow,
and Jira `SCRUM-24` is Done.

This verdict is intentionally narrower than production readiness. There is no
AWS deployment proof, public service, production identity flow, shared durable
storage exercise, monitored staging environment, capacity SLO or live RAG
provider. Those remain V2 or separately approved product decisions.

## Release boundary

- **V1:** local/private Docker Compose product; read-only public intelligence
  and research surfaces; server-side local operator bridge for the integration
  register; deterministic demo data; verified backend/frontend/container
  workflow.
- **V2:** deploy and prove AWS identity, edge, durable data, backup/restore,
  staging, monitoring, capacity and immutable release contracts.

## Evidence-based requirement matrix

| Area                               | Status                             | Evidence and finding                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repository and CI                  | **Complete for V1**                | Tracked repository, protected `main`, branch-neutral required checks, locked dependencies, package/image builds, dependency audits, Trivy gates and commit-specific CycloneDX evidence. GitHub Actions run 45000024529 passed every required job on Task 37 evidence commit `5a5a3c9`.                                                                                |
| Data model and provenance          | **Complete**                       | Actors, aliases, sources, raw evidence, observations, behaviors, techniques, campaigns, relationships, resolution audit, jobs, embeddings, artifacts, advisories and publication visibility are migrated and tested. Evidence remains traceable through reads and exports.                                                                                            |
| Ingestion and integrations         | **Complete for approved V1 scope** | MITRE ATT&CK is the runnable fixed-source connector. MISP Galaxy, CISA, Microsoft Threat Intelligence, Google TAG and Unit 42 are accurately presented as the next source wave; Malpedia, Securelist, ESET and selected news remain later. Planned sources expose no false run control.                                                                               |
| Normalization and actor resolution | **Complete**                       | Deterministic parse/normalize/validate/deduplicate/persist behavior, alias resolution, ambiguity handling and immutable resolution audit are tested. Fuzzy similarity never auto-links actors.                                                                                                                                                                        |
| Search and actor research          | **Complete for local V1**          | Published actor, alias, indicator, CVE, campaign, behavior, technique, observation and source context is searchable with stable pagination. Actor dossiers include aliases, observed/assessed timeline evidence, techniques and evolution. Production-scale relevance and latency evidence remain V2.                                                                 |
| Living intelligence                | **Complete**                       | Current and historic published revisions, typed OBSERVED/ASSESSED sections, entity/evidence links and ordered updates are implemented in API and UI. Withdrawal/redaction policy remains a later editorial decision.                                                                                                                                                  |
| Technical views                    | **Complete**                       | ATT&CK, Sigma and STIX 2.1 surfaces preserve the approved narrow technical contracts and provenance. Unsupported semantics are omitted rather than inferred.                                                                                                                                                                                                          |
| Async jobs                         | **Complete**                       | PostgreSQL-backed durable state, UUID-only Redis messages, replay safety, leases, retry/backoff, recovery, backpressure and queue metrics are tested.                                                                                                                                                                                                                 |
| Frontend                           | **Complete and accepted**          | SvelteKit/TypeScript implements Home, Intelligence, Actors, Evolution, Research, Technical, Search, platform updates, actor/advisory detail and the local integration register. The real Docker journey passed at 320, 768 and 1440 px with no document overflow; the owner accepted the revised flow.                                                                |
| Accessibility                      | **Complete for V1**                | Automated axe checks, one-main/one-h1/contentinfo landmarks, skip link, visible keyboard focus, dialog focus management, keyboard evidence disclosure, reduced motion and responsive checks pass. Effective 200%-zoom reflow was reviewed at half the desktop CSS width without clipped controls.                                                                     |
| Visual contract                    | **Complete and accepted**          | Rendered review confirms the approved near-black research atmosphere, cyan interaction, incident-red threat signals, amber assessed/match state, evidence-first presentation and self-hosted editorial typography. No copied CyberNetSec.io logo, wording, illustration or page composition; no unsupported metrics, continuous glow or generic enterprise card grid. |
| UI security                        | **Complete for local V1**          | Web CSP denies framing and objects; frame denial, content-type protection and referrer policy are present. External evidence links use safe attributes. Built assets/rendered content expose no operator token, operator header, database URL or private API origin. No raw HTML injection or browser credential storage is used.                                     |
| Backend tests and migrations       | **Complete**                       | Ruff and formatting pass across 175 files; Pyright reports zero errors/warnings; Alembic is at sole head `f6a1c2d3e4b5` with no drift; 121 tests pass and one disposable-S3 test remains explicitly environment-gated.                                                                                                                                                |
| Frontend tests                     | **Complete**                       | Prettier, ESLint, Svelte/TypeScript and production build pass; 16 unit files/69 tests and 14 production-browser acceptance tests pass. Browser console review returned zero errors.                                                                                                                                                                                   |
| Local performance evidence         | **Complete for local V1**          | The deterministic-stack baseline records 20 sequential samples per principal route, including environment, response sizes and min/median/p95/max. It makes no production SLO or capacity claim. See `docs/performance/v1-ui-baseline.md`.                                                                                                                             |
| Local containers                   | **Complete**                       | Compose config/build/up pass. PostgreSQL, Redis, API and web are healthy; the worker runs; all four published ports bind to `127.0.0.1`. The idempotent demo graph reports the exact expected 25 records.                                                                                                                                                             |
| RAG execution                      | **Partial by design**              | Grounding, citations, filtering and insufficient-evidence behavior are tested with deterministic providers. No approved live model, embedding backfill or data-egress/budget decision exists, so the live endpoint correctly remains unavailable.                                                                                                                     |
| AWS deployment and operations      | **Deferred to V2**                 | Validation-only templates and private staging/recovery runbooks exist, but no AWS resources, public edge, production identity, backup recovery, monitoring or operational proof has been authorized or claimed.                                                                                                                                                       |
| Documentation                      | **Complete for V1**                | README, SETUP, product scopes, design/security contracts, local performance evidence and execution plans describe the proved local/private boundary. The originally referenced `docs/design/system-workflow-reference.md` was never supplied and has not been reconstructed.                                                                                          |

## Demonstrated V1 journey

The seeded `watchtower_demo/v1` graph supports this reproducible flow:

1. Open Home and the platform-update archive.
2. Search `Frost Lantern`, `telemetry-cdn.example` or `CVE-2026-45123`.
3. Open the related actor dossier, evolution, techniques and cited evidence.
4. Read the current living advisory, its archived first revision and ordered
   update.
5. Review Technical and the local/private integration roadmap.

The integration register is server rendered. The local operator token remains
on the server and is attached only to an exact allowlist of operator requests.
This static-token bridge is forbidden in production.

## Named V1 limitations

- Local/private use only; no internet-facing or AWS operational proof.
- Public/editorial intelligence is read-only in the browser; there is no
  publishing console or production browser sign-in.
- Actor evolution is an evidence-led timeline, not a complete-series chart.
- Live RAG is disabled pending a provider, privacy/egress and budget decision.
- Only MITRE ATT&CK is runnable; other approved sources are accurately marked
  as planned rather than simulated.
- The demo dataset is fictional and intentionally small. The local timing
  baseline cannot be extrapolated to production data or traffic.
- Advisory withdrawal/redaction, production monitoring and release-image
  attestation remain later decisions/work.

## Validation evidence

Local final-state evidence on 2026-11-21:

- Backend: Ruff lint/format passed; Pyright 0 errors/0 warnings; Alembic sole
  head/current `f6a1c2d3e4b5` and no drift; 121 passed, 1 environment-gated S3
  test skipped.
- Frontend: formatting, lint and Svelte checks passed; 69 unit tests and 14
  production-browser tests passed; production adapter build passed.
- Real stack: Compose configuration/build/start passed; API and web health
  passed; demo status returned `complete` with 25 exact records.
- Responsive/manual review: Home, Search, actor dossier, advisory, Technical
  and Integrations were inspected at 320, 768 and 1440 px. A root `min-width`
  defect found at 320 px was removed, regression assertions were strengthened,
  and the full build/browser suite passed afterward.
- Security: web CSP/frame/content-type/referrer headers passed; client asset
  and source scans returned zero credential/private-origin/raw-HTML/browser-
  storage matches; safe evidence-link attributes were confirmed.
- Local timing: every sampled route returned 200; see the separate baseline
  for methodology and exact measurements.

Skipped or unavailable checks are not counted as passed. The disposable S3
test is the only local suite skip. GitHub Actions run 45000024529 supplied the
locked package build, dependency audit, both image scans and CycloneDX evidence
on Task 37 evidence commit `5a5a3c9`; all four jobs passed.

## Acceptance outcome

1. Owner approval of the live desktop/mobile/search local/private flow was
   received on 2026-11-22.
2. The result is recorded in the Task 37 plan, and Jira `SCRUM-24` was moved to
   Done on 2026-11-23.

The local/private V1 UI program is accepted. V2 productionization remains the
next separately authorized program; this acceptance does not claim AWS or
internet-facing operational readiness.

## V2 and optional follow-up

V2 productionization remains separately gated:

1. Deploy and prove Cognito/OIDC plus ALB/ACM/WAF and target isolation.
2. Deploy and prove S3/RDS/backup/restore data operations.
3. Exercise private staging deployment and rollback.
4. Add operational monitoring and production-like capacity evidence.
5. Publish and attest immutable release images.

Optional product decisions remain separate: live RAG, advisory withdrawal,
additional ingestion connectors, richer evolution visualization and a future
authenticated editorial workflow.
