# Task 35 — operator integration management

Status: owner-directed and active, 2026-11-17.

## Prior-task verification

Task 34 was reverified before this task started. The working tree was clean at
`633be39`, the implementation and plan files were inspected, GitHub Actions run
119 passed all required jobs, and the owner directed the next implementation
task. No Task 34 issue remains open.

## Goal

Give a local/private WATCHTOWER operator one truthful place to inspect the
approved intelligence-source roadmap and operate connectors that actually
exist, without exposing credentials or implying planned sources are usable.

## Security and role decision

WATCHTOWER has no web admin pane or `admin` role. It already has backend
`operator` and `publisher` roles. Integration management uses the existing
`operator` authorization boundary.

The V1 web page is available only when `WATCHTOWER_ADMIN_ENABLED=true` and a
server-only static `WATCHTOWER_OPERATOR_TOKEN` is configured. The SvelteKit
server attaches that token to allowlisted operator API calls. It never enters
page data, form fields, browser storage, rendered HTML or client assets. The
page returns the same 404 treatment when disabled. Production OIDC web sign-in
and browser bearer-token handling remain outside this task; production must
keep this local static-token page disabled.

## Deliverables

- Add an operator-protected integration catalog endpoint containing the
  owner-approved source waves and enrichment roadmap from one backend source.
- Report implementation state, operational state, supported actions, required
  configuration names and the newest job for each implemented connector.
  Return configuration names and booleans only, never values.
- Keep MITRE ATT&CK as the only runnable connector. Planned sources appear as
  planned and expose no enable/run action.
- Reuse the existing bounded ingestion service for an operator-triggered MITRE
  refresh with a required idempotency key.
- Add a separate server-only operator API client with exact path/method
  allowlists, bounded timeout, stable error normalization and no network retry
  for mutations.
- Add `/admin/integrations` with an open editorial list rather than a dashboard
  card grid. Show source wave, implementation/configuration state, supported
  enrichment and recent run state; allow a manual MITRE refresh.
- Show an Admin destination only when the server-side admin feature is enabled.
- Document local enablement, secret handling, current limitations and exact
  validation commands.
- Add backend, frontend and production-browser tests for authorization,
  catalog truthfulness, secret non-disclosure, disabled 404 behavior, manual
  refresh, accessibility and responsive overflow.

## Explicit exclusions

- No connector is implemented beyond MITRE ATT&CK.
- No editable secrets, credential display, browser token, source URL entry,
  schedule editor, arbitrary fetch target, enable control for planned sources
  or deletion control.
- No new admin role, production OIDC login flow, AWS deployment, reputation API
  or connector-specific settings database.

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
git diff --check
```

Also scan generated client assets and rendered HTML for the operator token,
backend origin, operator header and operator endpoint paths. Inspect the page at
320, 768 and 1440 CSS pixels. Hosted CI must pass the final commit.

## Acceptance gate

- An authenticated operator can inspect the approved catalog and submit a
  replay-safe MITRE refresh.
- Unauthenticated API calls fail, and a disabled web admin route resolves as
  404.
- Planned connectors cannot be run and are never described as configured.
- No credential value or private operator configuration reaches browser state.
- The owner accepts the integration management flow before Task 36 begins.

## Validation results

- PASS: `uv run --locked ruff check .`; `ruff format --check .` reported all
  171 Python files formatted; `uv run --locked pyright` reported zero errors.
- PASS: all 119 backend tests were collected against an isolated migrated
  `watchtower_test` database; 118 passed. The existing disposable-S3 integration
  test was explicitly skipped because no disposable S3 environment is configured.
  Task 35 does not change S3 behavior.
- PASS: `uv run --locked alembic check` reported no new upgrade operations.
- PASS: frontend formatting, lint, Svelte type checks, 69 unit tests and the
  production adapter build completed successfully.
- PASS: all 13 production-browser tests passed. Coverage includes the disabled
  route's 404 response, authenticated catalog load, MITRE submission, 320/768/1440
  pixel overflow checks and axe accessibility scans.
- PASS: generated client assets contained no static operator token, operator
  header, private backend origin or operator integration API path. The rendered
  page check also found none of those server-only values.
- PASS: `git diff --check` reported no whitespace errors.
- PASS: GitHub Actions run 44103584749 passed backend, frontend, Python
  dependency-audit, and container build/security-scan jobs for implementation
  commit `e344a9e`.
- PASS: GitHub Actions run 44104089072 passed the same four required jobs for
  final documentation commit `69eb7e0`.
- FIXED DURING VALIDATION: the web `no-referrer` policy caused same-origin form
  posts to send `Origin: null`, which SvelteKit rejected through its CSRF check.
  `same-origin` now retains the required same-origin header while withholding
  referrers from cross-origin requests; the regression is covered by the browser
  test.
- NOTE: an initial full-suite run used the populated development database and
  correctly exposed baseline-data conflicts. The final run used the separate
  migrated `watchtower_test` database; setup guidance now requires this isolation.
- PASS: the owner accepted the integration administration flow on 2026-11-17
  by directing work to continue to Task 36. The Task 35 human-review checkpoint
  is satisfied.
