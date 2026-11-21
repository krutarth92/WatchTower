# Task 37 — V1 UI acceptance and readiness closure

Status: in progress; local implementation and acceptance evidence passed,
hosted CI and owner review pending, 2026-11-21.

Tracking: Jira `SCRUM-24`; branch `codex/task-37-v1-acceptance`.

## Prior-task verification

Task 36 was reverified before this task started. The implementation and
acceptance records were inspected on branch `codex/task-36-docker-demo`; the
working tree was clean at commit `fd3dad0`; GitHub Actions run 44924804779
passed backend, frontend, Python dependency-audit and container/SBOM jobs on
that exact commit; the owner directed work to continue; and Jira `SCRUM-23`
was moved to Done. Docker was initially absent from PATH and the local services
were stopped. Task 37 located the per-user Docker Desktop installation,
restored the existing Compose stack without deleting volumes and reran the
integrated journey before recording acceptance evidence.

## Goal

Prove the complete local/private V1 UI with reproducible evidence, correct the
readiness documentation to match the demonstrated state, and obtain owner
acceptance without introducing a new product feature or production claim.

## Fixed scope

1. Run the deterministic demo stack and complete the real-API journey: home,
   actor/indicator/CVE search, actor dossier and evolution, evidence/source,
   advisory current revision, historic revision, ordered update, technical
   views, platform updates and operator integration register.
2. Run automated accessibility scans and record manual keyboard order, visible
   focus, skip link, dialog focus, evidence disclosure, pagination, landmark,
   200% zoom and reduced-motion checks.
3. Inspect 320 px mobile, 768 px tablet and 1440 px desktop layouts, plus 200%
   browser zoom, for overflow, clipped content and unavailable controls.
4. Review the result against the approved CyberNetSec.io-derived qualities:
   dark research atmosphere, restrained cyan/violet accents, compact technical
   hierarchy and evidence-first presentation. Confirm there is no copied logo,
   wording, illustration, page composition, unsupported metric, oversized
   promotional hero or continuous glow.
5. Verify security headers, CSP, frame denial, content-type protection, safe
   external-link attributes, plain-text API content, server-only credentials,
   no browser credential storage and no private backend origin/secret in built
   client assets or rendered HTML.
6. Capture local navigation/resource timing for the documented deterministic
   dataset. Record environment and measurements as local evidence only; do not
   invent a production SLO or extrapolate capacity.
7. Run the complete backend, frontend, migration, dependency, image, Compose,
   security-scan and SBOM workflow on the exact final commit.
8. Update README, SETUP and the V1 readiness audit to describe only what the
   evidence proves. Preserve named limitations: local/private boundary,
   read-only public editorial flow, no complete-series chart, disabled live
   RAG, no AWS operational proof and deferred V2 productionization.

## Explicit exclusions

- No new route, product feature, backend semantic, connector or API contract.
- No AWS resource, public deployment, production SLO or production-readiness
  claim.
- No copied CyberNetSec.io branding, artwork, text or layout.
- No RAG enablement, complete-series chart, browser token entry, editorial
  console or production identity flow.
- A defect found during acceptance is fixed only in its owning implementation
  surface and the affected plus full acceptance checks are rerun.

## Evidence matrix

| Area                 | Required evidence                                                   | Current state                                      |
| -------------------- | ------------------------------------------------------------------- | -------------------------------------------------- |
| Real journey         | Deterministic Compose data and real API across every V1 module      | PASS                                               |
| Automated UI         | Production build, unit suite, Playwright journey and axe scans      | PASS: 69 unit and 14 browser tests                 |
| Manual accessibility | Keyboard, focus, zoom, landmarks and reduced motion                 | PASS                                               |
| Responsive           | 320/768/1440 and 200% zoom, no page overflow                        | PASS after 320 px root-overflow fix                |
| Visual contract      | Directional qualities present, prohibited copying absent            | PASS                                               |
| Security             | Headers, links, plain text, storage, HTML/assets and secret scan    | PASS                                               |
| Performance          | Documented local dataset/environment and navigation/resource timing | PASS: local-only baseline recorded                 |
| Backend              | Ruff, format, Pyright, Alembic, pytest and package build            | Local checks PASS; package build pending hosted CI |
| Supply chain         | Dependency audit, both image builds/scans and CycloneDX evidence    | Pending final commit CI                            |
| Documentation        | README, SETUP and readiness report match evidence and limitations   | PASS                                               |
| Owner review         | Desktop/mobile rendered flow accepted for local/private V1          | Pending                                            |

## Validation commands

```powershell
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked alembic upgrade head
uv run --locked alembic heads
uv run --locked alembic current
uv run --locked alembic check
uv run --locked pytest -p no:cacheprovider
uv build

pnpm install --frozen-lockfile
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e

docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose run --rm api watchtower-demo-data cleanup
docker compose run --rm api watchtower-demo-data seed
docker compose run --rm api watchtower-demo-data seed
docker compose run --rm api watchtower-demo-data status
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-WebRequest http://127.0.0.1:3000/search
# Complete browser, accessibility, responsive, security and timing review.
docker compose run --rm api watchtower-demo-data cleanup
docker compose run --rm api watchtower-demo-data status
git diff --check
```

The final GitHub Actions run must pass all required jobs on the exact final
commit. Skipped, unavailable and environment-blocked checks are recorded as
such and never reported as passed.

## Remaining gates

There is no local implementation blocker. The stack is healthy and remains
available at `http://127.0.0.1:3000` with deterministic data for owner review.
The final commit still requires hosted package/dependency/image/Trivy/SBOM
validation and owner acceptance before Task 37 can close.

## Acceptance gate

All required automated and manual evidence passes on the final state; README,
SETUP and the V1 readiness audit accurately describe local/private V1 and its
limitations; hosted CI passes the exact final commit; and the owner accepts the
rendered desktop and mobile flow. Only then may Tasks 29/30–37 and the V1 UI
program close and V2 productionization become the next program.

## Verification record

### 2026-11-21 static and automated baseline

- PASS: `.venv\Scripts\ruff.exe check .` and
  `.venv\Scripts\ruff.exe format --check .`; all checks passed and 175 Python
  files were formatted.
- PASS: `.venv\Scripts\pyright.exe`; zero errors and warnings. The sandboxed
  attempt was blocked by `EPERM` reading the existing editable-install `.pth`
  file, so the same command was rerun with filesystem approval and passed.
- PASS: frontend Prettier, ESLint and Svelte/TypeScript checks using the locked
  local executables; Svelte reported zero errors and warnings.
- PASS: `node node_modules/vitest/vitest.mjs run`; 16 files and all 69 unit
  tests passed.
- PASS: `node node_modules/vite/bin/vite.js build`; the SvelteKit production
  adapter build completed.
- PASS: `node scripts/run-e2e.mjs`; all 14 production-browser fixture tests
  passed. Existing coverage includes public module navigation, platform
  updates, integration administration, current/historic advisories, search and
  actor evolution, indicator/CVE context, safe error handling, axe scans,
  320/768/1440 px overflow checks, CSP/header assertions, safe external links,
  credential non-disclosure and zero browser console/page errors on the home
  route. Task 37 added explicit proof for one-main/one-h1/contentinfo landmarks,
  skip-link keyboard focus, focus transfer to main, filter-dialog focus,
  keyboard evidence disclosure and reduced-motion tokens. The first assertion
  expected source token text `0ms`; Chromium correctly normalized it to the
  equivalent computed value `0s`, the assertion was corrected, and the full
  14-test suite passed.
- PASS: generated client assets contained zero matches for the private API
  origin, API-origin setting, operator header/setting or PostgreSQL URL. Source
  contained zero raw-HTML, `innerHTML`, `localStorage` or `sessionStorage`
  constructs.
- BLOCKED LOCALLY: `.venv\Scripts\python.exe -m build`; this pre-existing environment
  lacks the `build` module. The locked dependency environment or hosted CI must
  run the package build; this check is not marked passed.
- PASS: `git diff --check` and Prettier for this execution plan.

### 2026-11-21 integrated acceptance

- PASS: Docker Desktop 4.92.0 / Engine 29.8.0 was located at its per-user
  installation. `docker compose config --quiet`, image builds and
  `docker compose up -d --wait` passed without deleting the existing volumes.
  PostgreSQL, Redis, API and web are healthy; the worker runs; every published
  port is bound to `127.0.0.1`.
- PASS: cleanup removed only the marked graph; first seed created it; the
  second seed was a no-op; final status reported `complete` with the exact
  expected 25 records.
- PASS: the real journey covered Home, actor/indicator/CVE search, related
  actor dossier and evolution, evidence link/provenance, current and historic
  advisory revisions, the ordered update, Technical, platform updates and the
  integration register. Search highlighting used unquoted text and indicator/
  CVE results returned the related actor context.
- PASS: keyboard skip/focus transfer, filter-dialog focus/Escape, keyboard
  evidence disclosure, landmarks and reduced-motion behavior passed. The live
  browser console contained zero errors.
- DEFECT FOUND AND RESOLVED: the first 320 px review exposed document overflow
  from `html { min-width: 20rem; }`. The root minimum was removed and all
  responsive assertions were tightened to compare document scroll width with
  document client width. The rebuilt Docker UI then passed all inspected routes
  at 320, 768 and 1440 px. A half-desktop effective CSS width was also reviewed
  as the 200%-zoom reflow equivalent with no clipping or root overflow.
- PASS: visual review found the approved dark research atmosphere, restrained
  accents, compact hierarchy and evidence-first treatment, without copied
  branding/artwork/text/composition, unsupported metrics, continuous glow or
  a generic enterprise card grid.
- PASS: web CSP, frame denial, content-type protection and referrer policy are
  present; API content-type/referrer protection is present; safe external-link
  attributes passed. Built client/source scans returned zero secret, private
  origin, database URL, raw HTML or browser-storage matches.
- PASS: Alembic upgrade/heads/current/check reached sole head
  `f6a1c2d3e4b5` with no drift. The isolated PostgreSQL suite passed 121 tests;
  the disposable-S3 test was explicitly skipped because that optional external
  environment is not configured. Two initial harness attempts are not counted
  as passes: the sandbox denied a compiled cryptography DLL, then exporting the
  development operator token correctly triggered three production fail-closed
  assertions. Exporting only the isolated test URL produced the recorded pass.
- PASS: `docs/performance/v1-ui-baseline.md` records one warm request plus 20
  sequential samples for each principal route, including response sizes and
  min/median/p95/max. It states the local-only method and forbids production
  capacity/SLO extrapolation.
- PASS: README, SETUP, the web README and the V1 readiness audit now match the
  proved local/private product and preserve all named V1 limitations.

Remaining work is final formatting/static validation, commit/push, the exact
commit hosted workflow and owner acceptance.
