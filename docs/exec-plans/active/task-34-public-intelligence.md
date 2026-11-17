# Task 34 — public site structure and published intelligence

Status: in progress.
Date started: 2026-10-23.
Branch: `codex/task-34-public-intelligence`.
Jira: `SCRUM-22` (existing UI backlog item; synchronize after implementation evidence is available).

## Prior-task verification

Task 33 was verified from the actual repository before this task began. The
working tree was clean at exact commit
`072c90f3768667c863547d6efe591d257a9ddb34`; its final three commits and Task 33
execution record were inspected. GitHub Actions run
[#104](https://github.com/krutarth92/WatchTower/actions/runs/39984005975)
passed frontend, backend, dependency-audit and container jobs on that exact
commit. The recorded local validation passed 116 backend tests with one
configured S3 skip, 55 frontend tests and 10 production-browser journeys,
including accessibility and overflow checks at 320, 768 and 1440 CSS pixels.
Alembic drift and downgrade/re-upgrade validation also passed. No file changed
after that validation. The owner's 2026-10-23 direction to add the public site
structure and platform-update surface accepts Task 33 and advances Task 34.

## References and amendment

- The owner-supplied `https://cyber.netsecops.io/` page was inspected on
  2026-10-23. Its compact platform announcement rail is directional only.
- The owner-supplied composite concept image defines possible module coverage:
  home, intelligence, actor directory/dossier, evolution, research, technical,
  search, source/evidence and responsive views.
- [Public site structure](../../design/public-site-structure.md) maps those
  references to truthful V1 routes and records the deferred boundaries.
- The V2 enterprise/environment dashboard stays deferred, consistent with the
  accepted AWS and operational-proof decision.

## Goal

Turn the current research screens into a coherent public intelligence site and
complete the published advisory journey without weakening publication or
operator boundaries.

## Deliverables

- Replace the root redirect with an editorial home page backed by published
  advisory and actor discovery data, with independent partial-failure states.
- Add primary navigation for Home, Intelligence, Actors, Evolution, Research
  and Technical, plus a secondary Platform updates destination.
- Add one typed site-map source and one typed platform-update source so labels,
  URLs and release content are not repeated across components.
- Add a restrained latest-update rail on Home and a dated `/updates` archive.
- Add `/actors`, `/evolution` and `/technical` landing pages that use current
  public data or clearly explain current read-only boundaries; add no dead nav.
- Implement `/advisories`, current advisory detail and historic published
  revision routes, including typed sections, linked actors/campaigns/
  techniques, evidence, publication metadata and ordered update pagination.
- Preserve paragraphs as plain text, distinguish OBSERVED and ASSESSED in text
  as well as color, and keep every API string inert unless an existing safe-link
  component explicitly validates it.
- Remove the temporary `/components` route after its shared primitives have
  production coverage.
- Update unit, route and production-browser coverage for navigation, the update
  rail/archive, partial home data, empty modules, advisory history/updates,
  keyboard use, accessibility and responsive overflow.

## Explicit exclusions

- No live RAG/Ask WATCHTOWER execution, standalone source profile, complete
  timeline chart, public STIX/Sigma generation, operator UI or browser token.
- No enterprise environment dashboard, AWS deployment, operational metrics or
  unsupported aggregate counters.
- No copied reference-site branding, wording, imagery, metrics or page layout.

## Validation

```powershell
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
git diff --check
```

Also run affected backend advisory tests when the API contract is rechecked,
inspect the rendered home, updates, module pages and advisory journey at 320,
768 and 1440 CSS pixels, and verify client assets contain no backend origin,
operator route or secret.

## Acceptance gate

- Every primary navigation item resolves to a useful, truthful page.
- Home remains useful when either advisory or actor discovery fails.
- The platform update rail and archive use one source and describe only shipped
  capabilities.
- Published advisory list/current/history/update ordering matches the API;
  drafts and unavailable revisions use the same safe public 404 treatment.
- The site has no automated accessibility violations or horizontal page
  overflow at the required widths.
- The owner accepts the public structure and advisory journey before Task 35.

## Validation results

- PASS: Prettier, ESLint and `svelte-check` completed with no findings.
- PASS: Vitest completed 15 files and 63 tests.
- PASS: the production SvelteKit build completed successfully.
- PASS: Playwright completed 12 production-browser journeys covering all
  primary modules, update archive, advisory current/history/updates, search,
  actor discovery, keyboard use, automated accessibility scans and horizontal
  overflow checks at 320, 768 and 1440 CSS pixels.
- PASS: the generated client-asset scan found no backend origin, operator token
  header or operator API path; Task 34 page styles contain no color literals.
- PASS: `git diff --check` completed with no whitespace errors.
- PASS: rendered Home was reviewed from the production build and preserves the
  owner-directed open editorial hierarchy and reference-site qualities without
  copying its content or dashboard composition.
- NOT RUN: the PostgreSQL advisory integration tests require
  `WATCHTOWER_TEST_DATABASE_URL`; the current local PostgreSQL service is
  stopped and Docker is unavailable on this execution PATH. The command was
  run with cache disabled and reported three explicit skips. Task 34 changes no
  backend contract, and the frontend advisory journey is covered by typed unit
  fixtures and the production-browser suite. Hosted backend CI remains required
  on the committed revision.
- PASS: integration inventory rechecked and owner-corrected on 2026-11-17.
  MITRE ATT&CK remains the only implemented external intelligence connector.
  The approved source waves and enrichment sequence are recorded in
  `docs/data-sources/integration-status.md`; X/Twitter and AlienVault OTX are
  explicitly outside those approved priority waves.
- PASS: GitHub Actions CI run 118 completed on commit `aa27670` with frontend,
  backend, Python dependency audit, container scan and SBOM jobs successful.
  The dependency audit now selects Python 3.13 explicitly, matching the
  repository's supported `>=3.12,<3.14` range instead of runner-default 3.14.
- PENDING: owner review of the public structure and advisory journey. Do not
  start Task 35 until this checkpoint and hosted CI pass.
