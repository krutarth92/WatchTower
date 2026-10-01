# Task 15: security threat model and hardening

Status: complete; stopped for human review.
Date: 2026-09-29.

## Prior-task verification

Task 14 was approved and reverified before this task began. Its database-backed
focused suite passed 20 tests, static checks passed, benchmark artifacts parsed,
Alembic reported no drift, and the live OpenAPI contract contained queue metrics
and backlog rejection. The exact record is in the Task 14 execution plan.

## Plan

1. Inventory public, operator, ingestion, parser, storage, queue, logging,
   dependency and outbound-network trust boundaries against the implemented code.
2. Document threats, existing controls, residual risk, ownership and deployment
   controls in `docs/security/threat-model.md`.
3. Implement only high-confidence fixes supported by reachable code paths, with
   regression tests for each changed behavior.
4. Run the focused and full security-relevant validation, confirm migrations and
   the live API, then stop for human review.

`docs/design/system-workflow-reference.md` remains absent. Its contents will not
be inferred.

## Acceptance record

### Review outcome

The implemented API, fixed-source connector, raw/object storage, artifact
parsers, RAG boundary, database access, logging and durable queue were inspected
against every threat named by Task 15. `docs/security/threat-model.md` records
assets, actors, trust boundaries, current controls, residual risks, deployment
ownership, release gates and future invariants. The missing workflow-reference
document is explicitly recorded without inferred contents.

### High-confidence fixes

- The ATT&CK fetcher asks for identity encoding, rejects encoded responses before
  body iteration, and ignores ambient proxy configuration.
- A configurable 64 KiB application request-body limit rejects declared and
  streamed overflow with a stable HTTP 413 response.
- All responses send `nosniff` and `no-referrer`; operator paths also send
  `Cache-Control: no-store`.
- Structured JSON log fields recursively redact common secret-bearing keys.

Regression tests exercise compressed-response rejection, request headers and
proxy isolation configuration, declared and chunked body overflow, response
headers, and nested logging redaction.

### Validation

- Focused security suite: 18 passed after the compressed-response fixture was
  corrected; body-limit suite then passed 10 tests.
- Full database-backed suite: 82 passed with the existing Starlette TestClient
  deprecation warning.
- `ruff check .`: passed.
- `ruff format --check .`: 114 files formatted.
- `pyright`: 0 errors, 0 warnings, 0 information messages.
- Alembic remained at `a1c3e5f7b9d2 (head)` and reported no new upgrade
  operations.
- The refreshed local API returned readiness/docs 200, security headers on the
  live response, and a stable 413 `request_too_large` response with `no-store`
  and request-ID propagation. OpenAPI documents the 413 response.

An online package-outdated query could not access the package index from the
restricted environment. It is not reported as passed and no assertion about
current vulnerability status is made. The lockfile and hash-pinned exports were
reviewed; automated advisory scanning remains an explicit CI/release gate.

### Acceptance criteria

- Threat model created at the required path: pass.
- SSRF, URLs/redirects, parser/PDF/archive risks, payload size, prompt injection,
  files, SQL, API abuse/rate limits, authentication/authorization, secrets,
  dependencies, logging, object storage, egress and queue abuse reviewed: pass.
- Only high-confidence, reachable fixes implemented: pass.
- Regression tests for each fix: pass.
- Deployment/operations risks clearly marked: pass.
- Destructive penetration tests and arbitrary external contact avoided: pass.

Concrete release blockers remain: public reads lack publication-state filtering;
shared rate limiting and identity-aware operator authentication are absent;
production storage/network/egress controls and automated advisory scanning are
not configured. These are documented and were not replaced with misleading
single-process approximations. No migration or new dependency was introduced.
Task 15 stops here pending human approval.

## Transition verification before Task 16

The user approved moving forward on 2026-09-29. The threat model and implemented
controls were re-inspected. The database-backed foundation/connector suite
passed 18 tests, focused Ruff and Pyright passed, Alembic remained at
`a1c3e5f7b9d2 (head)` without drift, and the live API returned readiness 200,
`nosniff`, and the expected 413/no-store response for a 65,537-byte request.
Task 15 therefore passed transition verification before Task 16 began.
