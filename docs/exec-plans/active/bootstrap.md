# Task 00: repository discovery and bootstrap plan

Date: 2026-10-01. Status: Tasks 00–18 verified and approved; G01 Git and
hosted-CI baseline remediation complete and awaiting human review.
See [Task 01 results](task-01-backend-foundation.md).
Scope reference: [V1 proposal](../../product-specs/v1-scope.md).

## Repository inventory

| Area | Evidence at task start | State |
| --- | --- | --- |
| Application, models, workers, migrations | No source directories or application files | Not implemented |
| Tests, CI and infrastructure | No tests, workflows, Dockerfiles or Compose files | Not implemented |
| Repository hygiene | .gitignore, .editorconfig, .python-version | Implemented files; not committed |
| Dependency/tool setup | requirements.txt, requirements-dev.txt, tool-only pyproject.toml | Partial: uninstalled, unlocked and unvalidated |
| Local instructions | Instructions/ contains Tasks 00–18; README.md and HOW_TO_USE_WITH_CODEX.md | Documented only; intentionally ignored |
| Setup guide | SETUP.md | Implemented documentation |
| Authoritative context | AGENTS.md and docs/design/system-workflow-reference.md absent | AGENTS.md was supplied later; workflow reference remains missing |
| Product/design/execution docs | No docs directory at task start | Missing; this task creates scope and plan |
| Generated artifacts and placeholders | No runtime artifacts, stub application or fake data found | None |
| Architecture and release policy | Prompt baseline exists but no approved specification | Proposed; decisions listed in scope |

Read all supplied task-specific instructions and both local guides, plus the
existing setup/configuration files. Git is available at
`C:/Program Files/Git/cmd/git.exe`, though not on this shell's PATH.
The user reports Docker is installed. `Get-Command docker` returned no executable,
and `C:/Program Files/Docker/Docker/resources/bin/docker.exe` was absent.
Docker installation location, Compose availability and engine readiness are
therefore unverified; this does not block documentation work. Locate the actual
installation or refresh PATH at Task 01 before running service checks.

## Conflicts, gaps and proposed resolutions

- The guides expect prompts in docs/codex-prompts; actual prompts are in
  Instructions/. Keep their current local location, as requested.
- Task 01 requests developer README commands, but the supplied README is an
  ignored instruction guide. Use tracked SETUP.md for developer commands.
- Task 01 specifies a uv project; existing pyproject.toml contains only tool
  settings. Introduce project metadata and a lock there, then generate the
  requested requirements files from the same dependency source.
- A frontend stack is listed, but no task implements it and Task 17 excludes
  frontend work. Propose a backend-first V1 and make the scope decision explicit.
- Task 07 disallows public writes while Task 08 describes submission endpoints.
  Keep submissions private/operator-only, with access control before exposure.
- Task 04 emits into normalization before Task 05 implements the pipeline.
  Define and test the boundary in Task 04; complete normalization in Task 05.
- Task 10 precedes artifact handling. Initially retrieve existing text/entities;
  integrate structured artifacts after Task 11 without arbitrary chunking.
- AGENTS.md was supplied later and its transition-verification rule is active.
  The workflow reference remains missing, so this proposal is not presented as
  a reconstruction of that document.
- No direct disagreement in the supplied baseline stacks was found. Preserve
  all original guidance; the resolutions above remain proposals for review.

## Proposed repository tree

```text
WATCHTOWER/
  pyproject.toml           # canonical project metadata/dependencies in Task 01
  uv.lock                 # resolved dependency lock
  requirements*.txt       # generated compatibility exports
  .env.example
  compose.yaml            # local PostgreSQL and Redis
  SETUP.md
  apps/
    api/
      src/watchtower/
        api/              # versioned routes and response contracts
        core/             # configuration/logging
        db/               # base, sessions and domain models
        services/         # domain behavior, added only when needed
        ingestion/        # intake, connector and normalization boundaries
        workers/          # Dramatiq entry point sharing application code
        retrieval/        # search and later evidence RAG
    web/                  # reserved for separately approved frontend
  alembic/
    versions/
  tests/
    unit/
    integration/
    fixtures/
    evaluations/
  docs/
    product-specs/
    design/
    data-sources/
    search/
    performance/
    security/
    exec-plans/active/
  .github/workflows/
  Instructions/           # existing ignored local reference bundle
```

This is a proposed tree, not a set of empty directories to generate now.

## Implementation sequence and validation gates

Execute one task at a time, review its diff/results, then commit approved work.

Before every task transition, follow the verification gate in root AGENTS.md:
inspect the completed task's actual deliverables, confirm its acceptance criteria
and required checks against the current state, and record results in this plan.
Resolve failures or blocked required checks before advancing. Verification does
not replace the task's human review checkpoint. This applies to Task 00 as well.
AGENTS.md was added after Task 00 to record this user-requested rule; the inventory
above describes the earlier repository state, not the current presence of that file.

| Task | Deliverable | Validation gate |
| --- | --- | --- |
| 00 | Inventory, scope, proposed architecture and plan | Four planning criteria below |
| 01 | uv backend, settings, health/readiness, sessions, Alembic, Compose and tooling | Clean install; health; database up/down readiness; pytest/Ruff/Pyright |
| 02 | Intelligence model design, models and migrations | Entity/provenance lifecycle, constraints and migration checks |
| 03 | Source registry and raw evidence storage | Duplicate handling, metadata validation and bounded safe object keys |
| 04 | MITRE ATT&CK reference connector | Local fixtures, malformed data, unavailable source and replay |
| 05 | Deterministic normalization | Replay, deduplication, rejection reasons and provenance continuity |
| 06 | Conservative actor resolution | Ambiguity, conflicting aliases and auditable corrections |
| 07 | Actor/timeline read APIs | Filtering, pagination, not-found, evidence and query counts |
| 08 | Dramatiq jobs and private submission | Retries, idempotency, state transitions and worker restart |
| 09 | PostgreSQL search | Curated lookup/ranking evaluation; first usable milestone |
| 10 | Grounded evidence RAG | Recall, citation accuracy, unsupported claims and insufficient evidence |
| 11 | Structured artifacts | Syntax validation, faithful originals, retrieval and duplicate handling |
| 12 | STIX mapping and export | Validator-backed tests for approved semantics |
| 13 | API performance | Reproducible measured workload before/after changes |
| 14 | Pipeline performance | Stage measurements, bounded concurrency and backpressure |
| 15 | Threat model and hardening | Regression tests for concrete fixes and documented residual risks |
| 16 | CI and deployment baseline | Checks, migration/build verification and documented rollback |
| 17 | Advisory backend contract | Update history, evidence links and publication visibility |
| 18 | V1 readiness audit | Evidence-backed complete/partial/missing/blocked matrix |

Security requirements apply throughout implementation, not only at Task 15.
Task 17 changes must pass the CI/security baseline established earlier.

## Task 01 execution outline after approval

1. Resolve the missing-document and release-boundary decisions in the scope.
2. Locate Docker/Compose and Python/uv; verify the engine and supported tooling.
3. Define the package, lock dependencies and generate requirements exports.
4. Implement only foundation endpoints, settings, logging and DB infrastructure.
5. Add PostgreSQL/Redis Compose services with local bindings, health checks and
   persistent database storage; do not add object storage or worker code yet.
6. Exercise actual PostgreSQL readiness and migrations plus automated checks.
7. Update SETUP.md with reproducible commands, report results, and stop for review.

## Planning validation and acceptance

- PASS: V1 is self-contained in docs/product-specs/v1-scope.md.
- PASS: V2/R&D exclusions are explicit; early milestone is distinct from full V1.
- PASS: Proposed tree supports backend, frontend, docs, workers, tests and migrations.
- PASS: Missing context and unresolved scope/security/provider/hosting decisions
  are visible in the scope's Human Decisions Required table.

Validation uses repository inventory, document cross-checks and literal
documentation checks. No application tests, lint or type checks apply to this
documentation-only task. Docker runtime verification remains unavailable.

## Human review checkpoint

Task 00 transition verification (2026-09-27): read AGENTS.md, both planning
documents and Task 01 in full using Get-Content; inspected Get-ChildItem -Force
and git status --short; git diff --check passed. The four planning acceptance
criteria above still pass against the current documents. No application checks
apply to Task 00. The user's request to start the next task approves the proposed
backend-first baseline despite the unavailable original workflow reference.
Docker location/readiness is a Task 01 environment check, not a failed planning
criterion. No remaining planning issue blocks the foundation implementation.

The following records the original checkpoint, now satisfied:

Review the proposed scope and decisions before starting Task 01. This checkpoint
comes from Instructions/TASK_00_REPOSITORY_DISCOVERY_AND_PLANNING.md:
"Stop after planning artifacts are complete. Do not begin implementation."
Task 01 also explicitly requires human approval of Task 00.

No production code, schemas, dependencies or infrastructure were created or
installed in Task 00. No subsequent tasks were executed. Existing uncommitted
setup files are preserved; no commit is made on the user's behalf.
