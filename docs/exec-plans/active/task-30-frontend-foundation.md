# Task 30 — frontend foundation and CI

Status: verified and ready for owner review.
Date started: 2026-10-21.
Branch: `codex/task-30-frontend-foundation`.
Jira: [`SCRUM-18`](https://kb-ai-projects.atlassian.net/browse/SCRUM-18).

## Prior-task verification

Task 29 was verified before Task 30 began. The UI experience contract, complete
Tasks 30-36 master plan, CyberNetSec.io visual-reference amendment, owner
approval and single-source design-token constraint were inspected from the
actual files. Local relative-link, task-structure, token-contrast and
`git diff --check` validations passed.

Hosted CI
[#84](https://github.com/krutarth92/WatchTower/actions/runs/39542781888)
passed backend checks, Python dependency audit and container build/scan for exact
approval commit `0590d99e8232b6bd35fc52c13256cfec980dcaa8`; its commit-bound
SBOM artifact was retained. The branch was clean and synchronized with its
remote. The owner approved the plan on 2026-10-21, all seven child Jira issues
were created under `SCRUM-16`, and `SCRUM-17` was moved to Done before this task
started.

## Goal

Create the reproducible SvelteKit foundation, centralized visual-token source,
private backend-origin configuration and frontend CI gate defined in the
[master plan](v1-ui-development-plan.md), without implementing product screens.

## Implementation decisions

- All color, typography, spacing, radius, shadow, motion and layout constants
  live in one versioned token stylesheet. Components consume semantic CSS
  custom properties and do not repeat critical visual literals.
- The initial shell demonstrates the approved dark navy and cyan/violet
  direction while remaining a foundation, not a finished search screen.
- `WATCHTOWER_API_ORIGIN` is parsed only by a server module, accepts only safe
  HTTP(S) origins without credentials or path/query/fragment, and defaults to
  loopback for local development.
- The committed pnpm lockfile is the transitive dependency source of truth.
- Frontend CI is additive and leaves all existing backend jobs intact.

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

Local validation on 2026-10-21:

- PASS: frozen root workspace install used the committed lockfile and pnpm
  12.14.0 reported that it was current.
- PASS: Prettier, ESLint and Svelte/TypeScript checks completed with no errors
  or warnings.
- PASS: Vitest ran 13 tests across three files.
- PASS: the adapter-node production build completed.
- PASS: Playwright built and served the production application on a reserved
  loopback port, verified the root redirect, heading and private-environment
  label, and reported one passing browser test.
- PASS: generated browser assets contain neither `WATCHTOWER_API_ORIGIN` nor
  its default loopback value.
- PASS: production output was inspected at 1265 x 712 and 320 x 720 CSS pixels;
  the header, navigation, intro and status panel remained legible without
  clipping or horizontal overflow.
- PASS: the token architecture test rejects color literals outside
  `src/lib/styles/tokens.css`; all shared visual decisions are centralized.
- PASS: `git diff --check` reported no whitespace errors.

Hosted GitHub Actions
[#85](https://github.com/krutarth92/WatchTower/actions/runs/39547370739)
passed on implementation commit `ec4d9307694eb65e340cbf963ad557aaef48aa39`:
frontend checks, backend checks, Python dependency audit, and container
build/scan all completed successfully. The owner review gate remains open;
Task 31 cannot start until the shell and dependency footprint are accepted.

## Acceptance criteria

- PASS: the empty SvelteKit shell loads from the production Node build.
- PASS: dependency versions and the root pnpm lockfile are reproducible.
- PASS: private backend origin parsing is server-only, rejects unsafe origin
  forms, and is absent from generated browser assets.
- PASS: the existing backend, dependency-audit and container CI jobs remain in
  the workflow without weaker commands or permissions.
- PASS: all four hosted CI jobs passed on the exact implementation commit.
- PENDING: owner reviews the rendered shell and dependency footprint.

## Risks and remaining issues

- Product search, actor and advisory modules are intentionally deferred to
  Tasks 32-34. This task exposes no incomplete data controls.
- The standalone pnpm executable and Playwright browser are local ignored tools;
  they are not repository artifacts. CI provisions its pinned pnpm runtime.
