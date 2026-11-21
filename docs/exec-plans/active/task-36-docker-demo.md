# Task 36 — deterministic demo data and Docker integration

Status: complete; implementation, hosted CI and owner review passed, updated
2026-11-21.

## Prior-task verification

Task 35 was reverified before this task started. The working tree was clean at
closeout commit `0426287`; the implementation, execution plan and final diff
were inspected; GitHub Actions run 44109110690 passed backend, frontend, Python
dependency-audit and container build/security-scan jobs; the owner accepted the
integration-administration flow; and Jira SCRUM-25 was moved to Done. No Task 35
issue remains open.

## Goal

Make the complete local/private V1 UI reproducible from a clean checkout with
one Docker Compose stack and deterministic intelligence that demonstrates the
approved researcher journey.

## Deliverables

- Add an explicitly development-only `watchtower-demo-data` command with
  `seed`, `cleanup` and `status` operations.
- Seed a published actor and aliases, indicator, CVE, behaviors, techniques,
  observed and assessed timeline events, evidence/source provenance, campaign,
  and a published advisory with two published revisions and an update.
- Use deterministic identities plus a versioned marker in every seeded
  entity's metadata or immutable advisory identity. A second seed run must not
  duplicate or mutate the graph.
- Refuse to seed or clean outside the development environment. Cleanup must
  verify marker ownership and remove only the exact demo graph; unrelated rows
  must survive.
- Add a multi-stage non-root `apps/web/Dockerfile` with a loopback health check
  and no development dependencies in the runtime image.
- Extend local `compose.yaml` with migration, API, worker and web services.
  Publish only loopback ports: web on 3000, API on 8000, PostgreSQL on 5432 and
  Redis on 6379. Keep the API origin and operator token server-side.
- Preserve the existing host-development workflow and the separate private
  staging Compose definition.
- Update `.env.example`, README and SETUP with exact full-container and
  host-development commands, seed/status/cleanup behavior, and safe teardown.
- Add focused backend tests plus Compose/image/smoke validation and verify that
  browser assets contain no private API origin or secret.

## Safety decisions

- The demo dataset marker is `watchtower_demo/v1`; it is not inferred from a
  broad name prefix alone.
- Cleanup locks and validates the deterministic root source/advisory identities
  before deleting their dependants in one database transaction. A missing or
  mismatched marker fails closed.
- `docker compose down` preserves the PostgreSQL volume. Volume deletion is not
  part of the documented workflow.
- No service binds an application or data port to a non-loopback interface.
- No AWS, TLS/public exposure, production OIDC, external fetch, real IOC or
  shared durable hosting is introduced.

## Validation

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked pytest
uv run --locked alembic check
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose run --rm api watchtower-demo-data seed
docker compose run --rm api watchtower-demo-data seed
docker compose run --rm api watchtower-demo-data status
Invoke-WebRequest http://127.0.0.1:3000/search
Invoke-RestMethod http://127.0.0.1:8000/ready
docker compose run --rm api watchtower-demo-data cleanup
docker compose run --rm api watchtower-demo-data status
docker compose down
git diff --check
```

Run the browser journey against the real Compose API and demo data. Confirm the
second seed is a no-op, status reports the expected exact graph before cleanup,
cleanup reports zero remaining demo rows, and an unrelated sentinel survives.
Scan rendered HTML and generated client assets for the database URL, private
API origin, operator token and operator header. Hosted CI must pass the final
commit.

## Acceptance gate

A new developer can follow the documented commands, browse meaningful
published intelligence at `http://127.0.0.1:3000`, complete the researcher
journey, and clean up only marked demo data. The owner accepts the containerized
browser startup flow before Task 37 begins.

## Verification record

Validation on 2026-11-18 used the current working tree:

- Ruff lint and formatting, Pyright and `alembic check` passed. The full backend
  suite passed with 121 tests and one intentionally skipped disposable-S3 test.
  An initial pytest run completed the tests but exited during cache persistence
  because Windows denied `.pytest_cache`; rerunning with the optional cache
  provider disabled passed and is the recorded result.
- Frontend formatting, ESLint and Svelte/TypeScript checks passed. All 69 unit
  tests and 13 Playwright browser tests passed, and the production build
  completed successfully.
- `docker compose config --quiet`, both image builds and
  `docker compose up -d --wait` passed. The standalone read-only web container
  also served `/search` as the non-root `watchtower` user without a reachable
  API.
- Cleanup reported the graph removed and status absent. The first seed then
  reported created, the second reported complete without duplication, and
  status returned the exact expected 25-record graph. Focused database tests
  confirmed an unrelated source survives cleanup and marker corruption fails
  closed.
- The live API returned three actor-search, two indicator-search and two
  CVE-search results. Seven real web routes returned 200: actor, indicator and
  CVE search; actor detail; advisory list and detail; and integration
  administration.
- Rendered HTML and generated client assets contained none of the operator
  token, internal API origin, operator header or database URL. Web, API,
  PostgreSQL and Redis published only four `127.0.0.1` bindings.
- Final Chromium inspection found and resolved CSP-blocked inline styles in the
  confidence meter, application wrapper and SvelteKit route announcer. The
  first two now use stylesheet rules; the announcer is limited to one explicit
  style hash. An end-to-end assertion now fails on browser-console errors. The
  eight-page real-data journey then rendered with zero console/page errors and
  no horizontal overflow at the desktop review width.

The stack was left running with the deterministic graph seeded for owner review
at `http://127.0.0.1:3000` on 2026-11-18. Its current process state must be
rechecked when Docker is available again. Hosted GitHub Actions must pass the
final pushed commit, and owner acceptance remains required before Task 37.

### Hosted-CI follow-up

GitHub Actions run 44227157250 passed the backend and frontend jobs. Its Python
dependency audit failed because the PyPI vulnerability service exceeded the
action's 15-second read timeout; the log contained no vulnerability result.
The web-image scan separately found six fixed HIGH findings in npm packages
bundled by the Node base image. npm is not used at runtime, so the remediation
removes npm and its CLI links only from the final web image, asserts their
absence in the container smoke test, and raises the audit network timeout to
60 seconds without weakening either security gate.

`git diff --check` and Prettier passed for the remediation. Docker is no longer
available on the current Windows PATH, so the remediated image could not be
rebuilt locally in this follow-up session. GitHub Actions run 44923042869 then
passed the backend, frontend, Python dependency-audit and container jobs at
commit `cea5fe9`. The container job rebuilt both images, confirmed the web
runtime is non-root and has no npm executable, served the read-only smoke
container, passed both HIGH/CRITICAL Trivy gates, and retained the backend
CycloneDX SBOM evidence. This left only the owner browser-flow checkpoint,
which is recorded below.

### Owner acceptance

PASS: on 2026-11-21, after the final validation results and the current local
Docker unavailability were reported, the owner directed work to continue to
the next task. This satisfies the Task 36 human-review checkpoint. The local
machine still requires Docker Desktop to be restored before the browser stack
can be reopened; that environment issue does not change the previously passed
Compose, real-browser and hosted container evidence.
