# Task 32 — published intelligence search

Status: in progress.
Date started: 2026-10-22.
Branch: `codex/task-32-published-intelligence-search`.
Jira: [`SCRUM-20`](https://kb-ai-projects.atlassian.net/browse/SCRUM-20).

## Prior-task verification

Task 31 was verified from the actual branch before this task began. The branch
was clean and synchronized at
`b3d70e35a3c001cf371af4a8cecfc3d8236ca3ad`; the production component gallery
returned HTTP 200, all 11 referenced CSS and JavaScript assets returned HTTP
200, CSP remained present and `X-Frame-Options` remained `DENY`.

The owner approved the gallery. Hosted GitHub Actions
[#93](https://github.com/krutarth92/WatchTower/actions/runs/39827246944)
passed on the exact closing commit, and `SCRUM-19` was moved to Done. No Task 31
check remained skipped or blocked when Task 32 started.

## Goal

Replace the foundation placeholder at `/search` with the first complete,
reproducible researcher workflow over the published deterministic search API.

## Scope and decisions

- Parse and validate query, entity type, intelligence type, source UUID and UTC
  date filters on the SvelteKit server before calling FastAPI.
- Keep the public browser URL deterministic and free of backend cursor data.
- Preserve backend order, publication semantics and opaque cursor handling.
- Render entity-aware results with explicit match, provenance and intelligence
  labels; link only actor-backed records to the implemented actor route.
- Provide initial, loading, empty, invalid, unavailable, rate-limited and stale
  result states without exposing upstream response internals.
- Use the Task 31 components and centralized tokens; add no page-local color
  literals.
- Follow the supplied NetSecOps reference for atmosphere, signal color and
  typography while keeping WATCHTOWER distinct. Use an open editorial search
  surface with dividers and whitespace instead of repeated dashboard cards.
- Keep the Task 31 component gallery available only as a temporary review route
  through Tasks 32–34.

## Validation

```powershell
pnpm install --frozen-lockfile
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
git diff --check
```

## Acceptance gate

- A valid URL restores the same normalized query and filters.
- Invalid local filter shapes do not call the backend.
- Result cards retain API order and never invent unsupported detail routes.
- Actor-backed results preserve the originating search URL.
- Repeated load-more appends in API order, keeps cursors opaque and clears
  pagination after filter changes.
- Keyboard submission, progressive filter focus and all defined states are
  covered by tests.
- The screen has no automated accessibility violations or horizontal overflow
  at 320, 768 and 1440 CSS pixels.
- The owner reviews and accepts the complete search screen before Task 33.

## Validation results

- PASS: the existing frozen Task 31 dependency tree was reused; Task 32 changes
  no package manifest or lockfile. The locally bundled pnpm is 11.25.0, so the
  repository-pinned pnpm 12.14.0 frozen-install command was not reported as a
  local pass. Hosted CI must repeat that exact install.
- PASS: Prettier, ESLint and Svelte/TypeScript checks completed with zero errors
  or warnings.
- PASS: Vitest ran 40 tests across nine files. Search coverage includes
  deterministic URL normalization, malformed filter rejection before transport,
  UTC filter conversion, preserved backend ordering, opaque cursor handling,
  safe 422/429/500/network normalization, hostile text and actor-only links.
- PASS: the adapter-node production build completed with the Task 31 CSP and
  security headers intact.
- PASS: Playwright ran six production-browser tests against a deterministic
  mock public API. Keyboard submission, filter-dialog focus, URL restoration,
  repeated load-more ordering, cursor exclusion, invalid/no-result/rate-limit/
  server-error states and retained safe request IDs passed.
- PASS: axe found no violations on populated search results at 320, 768 or 1440
  CSS pixels; each width had no horizontal overflow. The component-gallery
  regression scan also remained clean at all three widths.
- PASS: generated browser assets contain neither `WATCHTOWER_API_ORIGIN`, its
  private default origin nor the operator API route.
- PASS: the refreshed production preview returns HTTP 200 at `/search`, renders
  the revised open research layout, and retains CSP plus `X-Frame-Options:
  DENY`. A 2026-10-23 browser inspection confirmed that the search, scope,
  behavior and initial-state regions read as one continuous surface rather than
  a set of dashboard cards. The offline-backend view also exposed only the safe
  unavailable message.
- PASS: `git diff --check` reported no whitespace errors, and the new search
  source contains no local color literals outside the centralized tokens.
- PENDING: hosted GitHub Actions on the implementation commit.
- PENDING: owner review of the complete search screen.
