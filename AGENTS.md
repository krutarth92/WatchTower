# WATCHTOWER project instructions

This file records the user's task-verification rule. It does not reconstruct
the original project instructions referenced by the supplied task bundle.

## Verify the completed task before starting another

Before starting any new task, verify the most recently completed task against
its deliverables, acceptance criteria and required validation commands.

- Inspect the actual files and relevant diff; do not rely only on a previous
  completion message.
- Confirm that required checks passed for the current file state. Run missing
  checks and rerun checks affected by changes since the last validation.
- For documentation-only tasks, verify required documents, their consistency
  and acceptance criteria; application tests may be marked not applicable.
- Record the verification outcome, commands/results and remaining issues in
  the active execution plan. Never report skipped or blocked checks as passed.
- If verification fails or required checks remain blocked, resolve the issue
  within the completed task's scope before beginning the next task. If resolution
  requires user input, report the blocker and wait rather than advancing.
- Start the next task only after verification passes and any human review
  checkpoint required by the task instructions has been satisfied.

Apply this rule to every task transition, including Task 00 to Task 01.
