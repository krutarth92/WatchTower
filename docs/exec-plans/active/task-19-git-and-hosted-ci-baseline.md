# Task 19: Git and hosted-CI baseline

Status: publication explicitly authorized; README amendment and push active.
Date: 2026-10-01.
Source: V1 readiness gaps G01 and the hosted-run portion of G08.

## Prior-task verification

Task 18 was approved by the user. Its documentation-only deliverable was
reinspected and passed its structural and consistency checks. The numbered
instruction bundle ends at Task 18, so this task follows the first remediation
item in the approved readiness report rather than inventing another bundled
requirement.

## Goal and boundaries

Establish a reproducible Git baseline without overwriting the repository's
existing history, publish it to the configured GitHub remote, and obtain hosted
CI evidence when access permits.

The remote default branch is `main` with one existing commit containing
`LICENSE`. The previously unborn local `master` branch has been replaced by a
local `main` tracking `origin/main`; all project files remain untracked.

This task will:

1. preserve the remote `LICENSE` commit and work from `origin/main`,
2. verify ignore rules exclude local instructions, secrets, environments,
   caches, build output and runtime data,
3. scan candidate tracked text for secret-like values and inspect the complete
   staged file set,
4. rerun the project validation required for the exact staged baseline,
5. create one initial project commit and push it normally to `main`,
6. inspect the resulting GitHub Actions run through available Git/GitHub access.

This task will not force-push, rewrite remote history, commit `.env`, expose a
credential, change application behavior, configure production deployment or
enable staging deployment.

## Stop conditions

- Stop before publication if a real secret or unintended large/runtime file is
  staged.
- Stop if remote history diverges; never resolve by force.
- If GitHub CLI/API authentication is unavailable after a successful push,
  report hosted-run verification as blocked rather than passed.

## Local validation record

- Fetched `origin/main` and preserved commit `4c65889` containing `LICENSE`.
  Local `main` tracks that branch; no history was rewritten.
- Ignore inspection confirmed `.env`, local instructions/guides, virtual
  environments, caches, build output, storage and runtime data stay untracked.
- Reviewed 158 candidate files. No file exceeded 1 MiB, used a sensitive key
  extension or matched private-key, AWS-key or GitHub-token patterns. The two
  environment templates contain explicit replacement placeholders only.
- `git diff --cached --check` passed.
- `.tools\bin\uv.exe lock --check` passed.
- Ruff passed; 127 files were formatted.
- Pyright passed with 0 errors and 0 warnings.
- Alembic heads/current/check passed at `0218f83cad8e` with no drift.
- The first elevated test invocation could not access the Windows user temp
  directory and produced 19 fixture-setup errors after 66 passes. Repeating the
  same suite with pytest temporary data under ignored `storage/` passed all 85
  tests; the existing Starlette TestClient deprecation warning remains.
- `uv build` produced the source and wheel distributions.
- Docker image `watchtower:task19-baseline` built successfully and its
  installed-package smoke test printed `watchtower create_app`.

## Publication checkpoint

The baseline commit was created on local `main` as a normal child of the remote
`LICENSE` commit. The
automatic approval reviewer rejected `git push origin main` because publishing
the complete project is sensitive external egress and the user's general
"next task" instruction did not explicitly name this payload and GitHub
destination. No workaround was attempted. Hosted CI cannot start until the user
explicitly authorizes pushing this commit to
`https://github.com/krutarth92/WatchTower`.

The user then explicitly authorized that exact destination and payload and
requested a clean project README. The baseline commit will be amended to include
that README while retaining the commit message
`feat: establish WATCHTOWER backend baseline`, then pushed normally.
