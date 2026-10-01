# Task 22: retained container SBOM evidence

Status: complete, verified and approved; Task 23 started.
Date: 2026-10-01.
Source: remaining V1 readiness gap G08.

## Prior-task verification

Task 21 was reinspected before this task began. Local `main` and `origin/main`
matched `f4ddb69` with a clean tree. Alembic was at the single current head
`4c7d9e2a1b5f` with no drift, Ruff passed, and all 15 focused publication
privacy tests passed. Main CI run
[#18](https://github.com/krutarth92/WatchTower/actions/runs/36859784121)
passed all three required jobs. The user's request for the next task satisfied
Task 21's review checkpoint.

## Goal and boundary

Generate a machine-readable software bill of materials from the exact backend
image already built and vulnerability-scanned in CI. Verify that the document
is a nonempty CycloneDX inventory, record its SHA-256 checksum and the local
image content ID, and retain all three as a commit-specific GitHub artifact for
30 days.

Reuse the pinned Trivy action and add only GitHub's pinned upload-artifact
action. Keep the existing HIGH/CRITICAL vulnerability gate unchanged. The
artifact must not contain secrets, environment files, source evidence or image
layers.

This task does not publish a container image or claim image provenance. Signing
or attesting an ephemeral runner-local tag would not give deployers a durable
subject to verify. Registry selection, immutable image publication and its
attestation policy remain a later release decision.

## Acceptance criteria

- CI creates CycloneDX JSON from `watchtower:${{ github.sha }}` only after that
  exact image builds, imports and passes the vulnerability scan.
- The job fails if the SBOM is absent, malformed, not CycloneDX or has no
  components.
- The retained artifact name carries the full commit SHA and contains the SBOM,
  its checksum and the image ID only.
- Artifact retention is explicitly 30 days and upload fails when files are
  missing.
- External actions remain pinned to full commit SHAs.
- Existing required check names and branch-neutral triggers remain unchanged.
- The exact commit passes all three protected-branch checks and the artifact is
  visible and downloadable from its hosted run.

## Validation record

- PASS: PyYAML `BaseLoader` parse and structural assertions confirmed all
  triggers, unchanged required job name, full-SHA action pins, upload failure
  behavior and explicit 30-day retention.
- PASS: repository Ruff, formatting and Pyright checks; `git diff --check`.
- PASS: reviewed the artifact allowlist; it contains only SBOM JSON, its
  SHA-256 checksum and the Docker image content ID.
- PASS: hosted CI run
  [#19](https://github.com/krutarth92/WatchTower/actions/runs/36872704605)
  passed Backend checks, Python dependency audit and Container build and scan
  on implementation commit `97f9ed7`.
- PASS: GitHub retained artifact
  `watchtower-sbom-97f9ed7b0c94374789c300d39741349963d8e818` for 30 days.
  Its compressed size is 17,754 bytes and GitHub artifact digest is
  `sha256:8340e69f5c8b8790d08ed5bc6e4812599270ce0aa3d7ad9ebf1ddb754a8713f2`.
- PASS: authenticated download contained exactly the three allowed files. The
  checksum file matched the SBOM (`42219a786b4cc3a5d15c89fe7de498c095ad357d2b73a12786db744720f8fae9`),
  the JSON was CycloneDX 1.6 with 157 components, and the image ID was a valid
  SHA-256 identifier.

## Human review checkpoint

Stop after the protected-branch run passes and the retained artifact is
verified. Present the artifact contents, retention, remaining provenance limit
and exact hosted run before beginning another task.

The user's next-task request satisfied this checkpoint. Before Task 23 began,
local `main` and `origin/main` were both rechecked at full commit
`63b3e7490c8945bee7f6d173ff9b1bb4822a1103` with a clean tree. The final
workflow still had the three required jobs, the verified CycloneDX generation
and the 30-day commit-specific artifact upload, and `git diff --check` passed.
Hosted main run
[#21](https://github.com/krutarth92/WatchTower/actions/runs/36873669533)
passed Backend checks, Python dependency audit and Container build and scan on
that exact commit, with the expected SBOM artifact present. Task 22 therefore
passed transition verification.
