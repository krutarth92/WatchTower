# Task 31 — design system and typed public API client

Status: implementation verified; owner review pending.
Date started: 2026-10-22.
Branch: `codex/task-31-design-system-api-client`.
Jira: [`SCRUM-19`](https://kb-ai-projects.atlassian.net/browse/SCRUM-19).

## Prior-task verification

Task 30 was verified before this task began. The actual branch and completion
plan were inspected, the owner approved the corrected rendered shell and
dependency footprint, and the local production preview returned HTTP 200 with
all 11 referenced CSS and JavaScript assets available. The branch was clean and
synchronized at `b745f478f7fa244eb27ff83a140d374838142c48`.

Hosted GitHub Actions
[#90](https://github.com/krutarth92/WatchTower/actions/runs/39822733794)
passed frontend checks, backend checks, Python dependency audit and container
build/scan for that exact completion commit. `SCRUM-18` was then moved to Done,
satisfying the Task 30 to Task 31 transition gate.

## Goal

Build and test the shared visual, provenance, state and public-read transport
primitives needed by the search, actor and advisory screens without implementing
those complete product screens.

## Scope and decisions

- Continue using `src/lib/styles/tokens.css` as the only source of color
  literals and shared visual constants.
- Provide semantic panels, metadata, intelligence labels, provenance,
  confidence, UTC dates, safe locators, evidence disclosure and shared state
  components through owned Svelte source.
- Keep the component gallery honest: it uses explicitly labelled fixture data
  for component review and is not a product search or advisory screen.
- Mirror the implemented Pydantic public-read contracts in handwritten
  TypeScript and compile representative success, empty, truncated, partial and
  stable-error fixtures against them.
- Keep backend origin and API calls server-only. The client accepts only
  allowlisted public GET paths/query keys, uses a 10-second timeout, sends a new
  request ID for every attempt, retries one network failure and never retries an
  HTTP response.
- Use SvelteKit's nonce-aware CSP generation and add defensive response headers.
- Run axe through Playwright on the component gallery at 320, 768 and 1440 CSS
  pixels, alongside horizontal-overflow and browser asset checks.

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

- Shared components preserve intelligence type and provenance in text.
- Keyboard focus and retry/disclosure controls are deterministic.
- Hostile fixture strings remain inert text and unsafe locator schemes never
  become links.
- API errors retain status, code and request ID without exposing untrusted
  response internals.
- The component gallery has no automated accessibility violations or horizontal
  overflow at 320, 768 and 1440 CSS pixels.
- The owner reviews the component gallery before Task 32 begins.

## Local validation — 2026-10-22

- PASS: the frozen pnpm workspace install accepted the committed lockfile and
  exact `@axe-core/playwright` 4.14.0 dependency.
- PASS: Prettier, ESLint and Svelte/TypeScript checks completed with no errors
  or warnings.
- PASS: Vitest ran 30 tests across six files. Coverage includes every shared
  state, inert hostile evidence, safe locator schemes, API allowlists, fresh
  request IDs, bounded retry and stable error normalization.
- PASS: the adapter-node production build completed with nonce-aware CSP and
  defensive response headers.
- PASS: Playwright ran three production-browser tests. Axe reported no
  violations on the component gallery at 320, 768 or 1440 CSS pixels, and all
  three widths had no horizontal overflow.
- PASS: generated browser assets contain neither `WATCHTOWER_API_ORIGIN`, its
  private default origin nor the operator API route.
- PASS: `git diff --check` reported no whitespace errors.
- PASS: hosted GitHub Actions
  [#91](https://github.com/krutarth92/WatchTower/actions/runs/39824649301)
  passed frontend checks, backend checks, Python dependency audit and container
  build/scan on exact implementation commit
  `0032d4512b89a612992297e442aff55a0154fb56`.
- PENDING: owner review of the component gallery.
