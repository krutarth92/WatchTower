# Task 33 — actor research workspace

Status: in review after owner review revisions.
Date started: 2026-10-23.
Branch: `codex/task-33-actor-research-workspace`.
Jira: [`SCRUM-21`](https://kb-ai-projects.atlassian.net/browse/SCRUM-21).

## Prior-task verification

Task 32 was verified from the actual branch before this task began. The working
tree was clean at closing commit
`a173f7cd2ddbe84fc1307799f2f382f9d38ee399`; the production `/search` preview
returned HTTP 200 with CSP and `X-Frame-Options: DENY`. The accepted
implementation has 40 passing unit tests and six passing production-browser
tests, including axe and overflow checks at 320, 768 and 1440 CSS pixels.

The owner approved the revised open search screen on 2026-10-23. Hosted GitHub
Actions [#98](https://github.com/krutarth92/WatchTower/actions/runs/39929017155)
passed frontend, backend, dependency-audit and container jobs on the exact
closing commit, and Jira `SCRUM-20` was moved to Done. No Task 32 check remained
skipped or blocked when Task 33 started.

## Goal

Implement the core adversary to behavior to evolution to evidence workflow at
`/actors/[actorId]` over the published actor-read API.

## Scope and decisions

- Validate the actor UUID and search-return URL before any backend call.
- Require published actor identity first, then load aliases, associations,
  timeline and references concurrently as independent panel results.
- Keep date and intelligence filters deterministic in the browser URL. Keep
  opaque timeline cursors in same-origin POST bodies only.
- Preserve successful panel data during retries and earlier-event pagination.
- Show origin, intelligence type, uncertainty, confidence, techniques,
  behaviors, source provenance, evidence and every truncation signal.
- Create external links only for validated HTTP/HTTPS locators; render every
  other locator as selectable inert text.
- Continue the approved open editorial research surface and centralized design
  tokens; avoid dashboard-card repetition and page-local color literals.
- Keep the component gallery as a temporary direct review route through Task
  34.
- Highlight the literal searched attribute without decorating the query with
  quotation marks.
- Add first-class indicator and CVE search results with bounded related-actor
  identity, description and activity context.
- Populate the empty search page from published database records with at most
  12 recent and active actors. Recency follows the latest published observation;
  activity is a deterministic score over published observations, aliases,
  indicators and vulnerabilities.

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

- Missing, internal and malformed actor IDs share one safe unavailable state.
- Secondary panel failures do not replace successful identity or panel data.
- Filters survive reload and clear the timeline cursor.
- Earlier events append in API order without placing the cursor in the URL.
- All nested truncation flags remain visible beside the affected collection.
- Hostile citation, excerpt and locator values stay inert unless the locator is
  validated as HTTP/HTTPS.
- Search back-navigation is restricted to a normalized `/search` URL.
- Evidence disclosure, retries and pagination work by keyboard.
- The populated and partial screens have no automated accessibility violations
  or horizontal overflow at 320, 768 and 1440 CSS pixels.
- The owner accepts the complete actor workspace before Task 34 begins.

## Validation results

- PASS: inspected the complete Task 33 file set and diff from verified Task 32
  closing commit `a173f7cd2ddbe84fc1307799f2f382f9d38ee399`.
- PASS: `pnpm --dir apps/web format:check`, ESLint and `svelte-check` completed
  with no formatting, lint, type or accessibility diagnostics.
- PASS: Vitest completed 12 files and 54 tests, including malformed actor state,
  identity-first loading, independent panel failure and hostile evidence cases.
- PASS: the production Vite build completed successfully.
- PASS: Playwright completed all nine production-browser tests. The actor
  journey, filter persistence, opaque pagination, partial failure and safe 404
  states passed; axe reported no violations and no horizontal overflow at 320,
  768 or 1440 CSS pixels.
- PASS: the production actor route returned HTTP 200 with CSP and
  `X-Frame-Options: DENY`, and visual review confirmed the open editorial
  layout at desktop and narrow widths.
- PASS (superseded by owner revision): real-stack browser smoke testing used healthy local PostgreSQL and Redis
  containers plus the FastAPI service, rather than the deterministic browser
  mock. A published, local-only record set marked `task-33-search-smoke-v1`
  returned the Sandworm Team actor and Voodoo Bear alias for `sandworm`, the
  PowerShell technique as an exact match for `T1059.001`, and the Credential
  phishing activity observation for `credential phishing`. Opening the actor
  result preserved the search return URL and displayed its alias, associations,
  timeline, provenance and evidence from PostgreSQL.
- PASS: owner review revisions removed quotation marks from search headings and
  highlight literal query matches in result titles, summaries and identifiers.
- PASS: migration `f6a1c2d3e4b5` adds published indicators, vulnerabilities and
  their actor associations. Its upgrade, downgrade and re-upgrade cycle passed
  in the isolated `watchtower_test` PostgreSQL database.
- PASS: indicator and CVE searches return bounded related actors with canonical
  name, description and latest published activity. The empty search page loads
  at most 12 actors from a deterministic recent/active discovery endpoint.
- PASS: Ruff and Pyright completed with no diagnostics. The full backend suite
  passed 116 tests; the configured disposable-S3 test remained the only skip.
- PASS: Prettier, ESLint and `svelte-check` passed. Vitest completed 12 files and
  55 tests. The production build completed successfully.
- PASS: Playwright completed all 10 production-browser journeys. Indicator and
  CVE actor context, discovery data, keyboard flow, axe checks and horizontal
  overflow checks at 320, 768 and 1440 CSS pixels passed.
- PASS: real-stack verification used the migrated development PostgreSQL
  database and live FastAPI/Svelte services. `malicious-update.example` returned
  a domain indicator with Sandworm Team context; `CVE-2026-45123` returned a
  critical vulnerability with CVSS 9.8 and Sandworm Team context; the discovery
  endpoint populated Sandworm Team from published records.
- PASS: Jira `SCRUM-21` comment `10017` records the revision and validation; the
  issue remains In Review pending owner acceptance.
- PASS: `git diff --check` reported no whitespace errors; the Task 33 sources
  contain no page-local color literals; the browser bundle contains no
  `WATCHTOWER_API_ORIGIN`, default backend origin or operator-route strings.
- NOTE: the local machine provides pnpm 11.25.0 while the repository pins pnpm
  12.14.0. Dependency files were unchanged; hosted CI remains the authoritative
  frozen-install validation with the pinned toolchain.
- PASS: hosted GitHub Actions
  [#99](https://github.com/krutarth92/WatchTower/actions/runs/39930806401)
  passed frontend, backend, Python dependency-audit and container build/scan
  jobs on implementation commit
  `7ff6e71752bdf1f3fbbffa39dc55ffde30fd8887`. The container job emitted two
  non-blocking cache-restore egress-quota warnings; its build, scan and SBOM
  artifact completed successfully.
- PENDING: owner review of the complete actor workspace.
