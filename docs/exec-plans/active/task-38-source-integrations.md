# Task 38 — approved source integration wave

Status: implementation complete; hosted CI and owner review pending.
Date started: 2026-11-23.
Branch: `codex/task-38-source-integrations`.
Tracking: Jira `SCRUM-26`.

## Prior-task verification

Task 37 was verified from the actual repository before this task began:

- the working tree was clean at `bc15d5efd39cbfc4cc87d4f2b90493aae4f765c3`;
- the Task 37 record, V1 readiness audit, README change and final
  documentation-only diff were inspected and are consistent;
- `git diff --check 5a5a3c9..HEAD` passed, and no uncommitted file existed;
- application checks were not rerun because only the recorded closure
  documentation changed after the accepted implementation and evidence commits;
- GitHub Actions run `45095002929` passed on the exact final Task 37 commit;
- the owner-acceptance and Jira `SCRUM-24` closure gates are recorded as passed.

Task 37 is therefore complete. No skipped or blocked check is represented as a
pass, and Task 38 may start.

## Owner decision

The owner approved the following six-source runtime scope:

1. MITRE ATT&CK Enterprise (existing connector, retained and regression tested);
2. MISP Galaxy threat-actor cluster;
3. CISA Known Exploited Vulnerabilities (KEV);
4. Microsoft Threat Intelligence publications;
5. Unit 42 publications; and
6. The Hacker News as the deliberately selected news source.

This replaces Google TAG in the immediate implementation wave; Google TAG
remains planned. “Hacker News” means The Hacker News cybersecurity publication,
not the Y Combinator Hacker News API.

## Verified upstream contracts

The public endpoints were fetched on 2026-11-23 with no credential:

| Source | Fixed retrieval boundary | Format | Retention/reuse boundary |
| --- | --- | --- | --- |
| MITRE ATT&CK | existing versioned ATT&CK URL | STIX 2.1 JSON | Existing ATT&CK license notice and provenance remain unchanged. |
| MISP Galaxy | tag `2026031300`, `clusters/threat-actor.json` | MISP Galaxy JSON | Store exact dataset bytes; retain cluster UUID, synonyms and source references under the repository's CC0/BSD choice. |
| CISA KEV | official CISA KEV JSON feed | JSON | Store exact catalog bytes and map only supplied KEV fields; retain CISA locator and catalog version. |
| Microsoft Threat Intelligence | official Microsoft threat-intelligence topic RSS feed | RSS 2.0 | Store the feed response and publication metadata only; do not republish full article bodies. The topic-specific endpoint excludes unrelated blog categories. |
| Unit 42 | official Unit 42 RSS feed | RSS 2.0 | Store the feed response and publication metadata only; do not republish full article bodies. |
| The Hacker News | publisher-linked FeedBurner RSS endpoint | RSS 2.0 | Store feed response and publication metadata only; treat it as a secondary news source, not authoritative actor attribution. |

The endpoints returned HTTP 200 with their expected JSON or RSS media types.
Redirects remain fail-closed. Fetches use bounded timeouts, maximum byte counts,
identity encoding, fixed URLs and no ambient proxy credentials.

## Product boundary

Task 38 implements ingestion, provenance and operator control. It does not
silently turn external claims into WATCHTOWER assessments.

- Dataset and feed bytes are immutable raw evidence with content-hash
  deduplication.
- Source-native objects receive durable normalization ledger outcomes.
- Imported records remain `OBSERVED · imported`.
- New source content remains internal by default. Public visibility still
  requires the existing explicit publication boundary; a connector success is
  not editorial approval.
- MISP actor names and synonyms may create source-preserved actor/alias
  candidates, but ambiguous aliases never auto-merge canonical actors.
- CISA maps supplied CVE and remediation fields without inventing CVSS or
  severity values the catalog does not supply.
- Publication feeds map title, canonical URL, summary, publication/update time,
  author and categories. HTML is reduced to inert plain text and article bodies
  are not fetched.
- The Hacker News is labelled secondary reporting. It cannot override an
  authoritative observation or become a sole high-confidence attribution.

## Deliverables

1. Add reusable strict HTTP retrieval and safe RSS parsing boundaries.
2. Add source-specific registration, parsing, normalization and persistence for
   MISP Galaxy, CISA KEV and the three publication feeds.
3. Add distinct durable ingestion job kinds, source registration dispatch and
   worker processing for every implemented source.
4. Add a forward/backward Alembic migration for the ingestion-job enum change.
5. Mark all six integrations accurately in the operator catalog and permit one
   replay-safe manual refresh per connector from the admin integration page.
6. Preserve credentials server-side; these six sources require no API keys.
7. Add fixtures and tests for successful ingestion, replay/deduplication,
   malformed input, oversized responses, hostile XML, unavailable sources,
   provenance, job routing and operator UI contracts.
8. Update integration, setup, security and operating documentation with exact
   source and publication boundaries.

## Explicit exclusions

- No full-page scraping or copyrighted article-body republication.
- No LLM extraction, automated attribution, sentiment classification or
  fabricated ATT&CK mapping from article prose.
- No automated public publication and no weakening of fail-closed visibility.
- No API keys for sources that do not require them.
- No schedule/cron service in this task; operators trigger refreshes through
  the existing durable queue. Scheduling is a later operational decision.
- No X/Twitter, AlienVault OTX, reputation API, Google TAG, Malpedia, Securelist
  or ESET connector in this task.

## Validation

```powershell
uv run ruff check apps/api/src tests alembic
uv run ruff format --check apps/api/src tests alembic
uv run pyright
uv run pytest
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade -1
uv run alembic upgrade head
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web check
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
docker compose config
docker compose build
docker compose up -d
git diff --check
```

Live-source smoke tests are run separately and reported honestly. Fixture tests
remain the deterministic CI gate; upstream availability is not required for CI.

## Acceptance gate

- Every catalog entry marked implemented has a runnable durable job and a
  tested connector; no planned source exposes a run action.
- A successful run stores exact source bytes, source locator, source-native
  identity, timestamps and bounded normalized records.
- Replaying identical content does not duplicate canonical records.
- Malformed, oversized, redirected or unavailable responses fail safely and
  leave truthful job/raw-evidence state.
- Microsoft, Unit 42 and The Hacker News retain only feed metadata and inert
  summaries; full article content is not stored or displayed.
- Imported content remains internal until explicit publication.
- The Docker operator UI can queue and report each source refresh without
  exposing the operator token or private API origin.
- Required backend, frontend, migration, container and hosted CI checks pass on
  the final state, followed by owner review before Task 39.

## Validation results

Validated on the 2026-11-23 working tree:

- `ruff format --check apps/api/src tests alembic`: passed, 112 files formatted;
- `ruff check apps/api/src tests alembic`: passed;
- `pyright apps/api/src`: passed with 0 errors, 0 warnings and 0 information
  messages;
- full pytest run with the ignored local configuration narrowed to the isolated
  `watchtower_test` database: 136 passed, 1 skipped. The only skip is the
  pre-existing disposable-S3 integration environment, which is not configured;
- Alembic downgrade/upgrade round-trip: passed; current is
  `1a2b3c4d5e6f (head)` and `alembic check` reports no new upgrade operations;
- frontend format, ESLint, Svelte check and unit suite: passed; Svelte reported
  0 errors/0 warnings and Vitest passed 69 tests;
- production frontend build and Playwright suite: passed, 14/14 browser tests;
- `git diff --check`: passed; `.env` remains ignored and untracked, and the
  patch contains no credential-bearing URL;
- `docker compose config --quiet`: passed with the container database URL
  derived in-process from the ignored local database URL. The local `.env`
  still needs its documented `WATCHTOWER_CONTAINER_DATABASE_URL` entry for
  future Compose invocations without that temporary derivation;
- `docker compose build`: passed for API, migration, worker and web images;
- `docker compose up -d --wait --wait-timeout 120`: passed. PostgreSQL, Redis,
  API and web were healthy; the worker was running and the migration container
  exited successfully;
- live Docker verification: `/ready` returned `ready`, the admin integration
  page returned HTTP 200 and rendered all six source names; and
- five new live jobs completed successfully through the authenticated durable
  queue. Persisted results were MISP Galaxy 953 observations, CISA KEV 1,790,
  Microsoft Threat Intelligence 10, Unit 42 15 and The Hacker News 50. Each
  source has one immutable raw capture. The first MISP run exposed shared
  upstream aliases; the connector was corrected and regression tested so 14
  actually ambiguous alias keys are now retained as unresolved candidates
  rather than auto-merged. The corrected live retry succeeded.

Fixture/parser live smokes also returned 953 MISP objects, 1,790 CISA entries,
10 Microsoft items, 15 Unit 42 items and 50 The Hacker News items. These counts
are observations from the validation date, not stable acceptance constants.

Hosted GitHub Actions and owner review remain pending. No pending or skipped
check is represented as passed.
