# Task 26: durable evidence and data operations

Status: architecture proposal ready for owner approval; implementation and AWS
provisioning have not started.
Date: 2026-10-19.
Source: V1 readiness gaps G05 and G06.

## Prior-task verification

Task 25 was verified before this proposal was created. Local and remote `main`
matched the clean commit `7490431147c86437c922142cfe91c569d8b47d56`.
The final Task 25 diff and acceptance record were inspected, and
`git diff --check 7e3bdcd..7490431` passed. Protected-main CI run
[#58](https://github.com/krutarth92/WatchTower/actions/runs/39200949263)
ran for that exact commit and passed backend checks, Python dependency audit,
and container build/Trivy scan. Its commit-specific SBOM artifact remains
available. The complete transition evidence is recorded in the Task 25 plan.

## Current boundary

- Raw evidence uses a portable synchronous `ObjectStore` protocol, but the only
  implementation is `LocalObjectStore` on one host.
- Object keys are deterministic and content-addressed. Intake writes the object
  before it flushes the database row, so a database rollback can leave a safe
  orphan object; retry reuses matching bytes.
- The worker constructs local storage directly. Production cannot select shared
  storage and does not reject the local adapter.
- Private staging runs PostgreSQL 17 with pgvector and raw storage in Docker
  volumes. These volumes provide persistence, not independent backups.
- PostgreSQL connections have bounded pools and statements, but production TLS,
  certificate verification, runtime/migration role separation and managed
  backup evidence are absent.
- Source records carry licensing and policy notes. They do not yet carry an
  approved retention class or deletion policy.

## Recommended decision

### Raw evidence: private Amazon S3

Use one private regional Amazon S3 general-purpose bucket for production raw
evidence. Keep `LocalObjectStore` for development and single-host private
staging. Production must fail closed unless the S3 adapter is selected.

The production bucket will have:

- all account- and bucket-level public access blocks enabled, ACLs disabled with
  bucket-owner-enforced ownership, versioning enabled and HTTPS-only access;
- default SSE-KMS encryption with one customer-managed key and bucket policy
  enforcement of that key;
- deterministic existing keys unchanged, so database references remain stable;
- S3 Object Lock in **governance** mode with a 365-day default retention period;
  compliance mode is deliberately excluded until a legal owner approves an
  irreversible policy;
- no application delete or lifecycle-expiration permission; the worker role can
  put an absent object, read and inspect only `raw/*` objects;
- CloudTrail data events and S3 inventory for access and integrity review;
- a separate recovery/records role for restore, legal hold and approved deletion.

The application will retain current MITRE ATT&CK raw evidence after the initial
365-day lock while that source remains approved. It will not automatically
expire current or noncurrent versions in Task 26. Every future connector must
declare a reviewed retention class and licensing policy before production
enablement. Legal holds override normal deletion. Any later permanent deletion
requires a recorded source-policy decision, an integrity-impact report and a
separate privileged runbook.

This is conservative for the only approved source and keeps deletion reversible
during the first production cycle. The annual review prevents the absence of an
expiry rule from silently becoming permanent policy.

### Database: private Amazon RDS for PostgreSQL 17

Use an encrypted Multi-AZ Amazon RDS for PostgreSQL 17 DB instance in private
subnets. RDS currently supports pgvector on PostgreSQL 17, so the existing schema
does not require an engine change.

The database baseline will have:

- KMS encryption, deletion protection, no public endpoint and ingress only from
  approved application/migration security groups;
- `rds.force_ssl=1`, `sslmode=verify-full` and the pinned AWS RDS CA bundle in
  every application, migration and restore-validation connection;
- separate owner/migration and runtime roles. The runtime role receives only
  the schema/table/sequence privileges the application uses and cannot create
  extensions, schemas or roles;
- 35 days of RDS automated-backup/PITR retention;
- daily AWS Backup recovery points retained for 90 days in a KMS-encrypted
  governance-locked vault;
- no compliance-mode Vault Lock, cross-account copy or cross-Region copy until
  an operations owner approves their cost and irreversible retention effects.

The recovery objectives for the first production rehearsal are **RPO at most
5 minutes** for PostgreSQL, **RPO at most 24 hours** for a full S3 backup when
versioning/Object Lock cannot repair an incident, and **RTO at most 4 hours** for
the complete application. These are targets to test, not claims of achieved
service levels.

## Coordinated recovery contract

Normal recovery restores PostgreSQL to a new RDS instance at time `T`. Because
raw evidence is content-addressed and the runtime cannot delete or overwrite
objects, the live S3 bucket may safely contain a superset of the objects known at
`T`. Before traffic is enabled, a validation job must:

1. confirm the restored schema is at the expected Alembic head;
2. enumerate every non-null raw-evidence storage key referenced by PostgreSQL;
3. read each referenced object within bounded concurrency, recalculate SHA-256
   and compare its byte count and digest to the database;
4. report missing, mismatched and unreferenced objects without deleting any;
5. run the application readiness and focused provenance/replay checks;
6. record backup IDs, restore point, measured RPO/RTO and reviewer approval.

If the S3 bucket itself is unavailable or corrupted, restore the chosen AWS
Backup recovery point to a new versioned private bucket, validate it against the
restored database, then switch configuration. Redis is rebuilt because durable
job state lives in PostgreSQL.

## Proposed repository implementation after approval

1. Add `S3ObjectStore` and one storage factory. Preserve key validation and the
   current put-if-absent/collision contract. Use conditional S3 writes, checksum
   verification and stable sanitized storage errors.
2. Add explicit storage settings for `local` or `s3`, bucket, region and KMS key.
   Reject local storage and incomplete S3 configuration in production. Use the
   AWS SDK default credential chain; do not add access keys to settings or files.
3. Change the worker to request the configured `ObjectStore` from the factory.
4. Add deterministic tests for success, same-content retry, conflicting bytes,
   missing object, oversized reads, unsafe keys, permissions/service failures
   and production fail-closed configuration. Add an opt-in S3 integration suite
   against a disposable compatible endpoint.
5. Enforce production PostgreSQL certificate verification in settings and add a
   documented least-privilege role/bootstrap contract.
6. Add infrastructure templates for the S3/KMS policies, private RDS baseline,
   backup plan and governance vault. Templates must be validation-only until a
   separately authorized deployment.
7. Add a read-only integrity command and a restore-drill runbook. It must never
   repair or delete data automatically.
8. Update setup, deployment, threat-model and readiness documents. Keep private
   Docker Compose staging usable with local PostgreSQL and local storage.

## Acceptance criteria

- Production cannot start with local raw storage, public S3 access, static AWS
  credentials or a PostgreSQL connection that does not verify the server CA.
- S3 preserves the current immutable, idempotent object contract across multiple
  workers and returns stable failures without leaking AWS details.
- Runtime and migration database privileges are separated and documented.
- Infrastructure templates encode encryption, private networking, versioning,
  governance retention, backup retention and deletion protection.
- The integrity command detects missing, altered and orphan objects without
  mutating either store.
- Unit, PostgreSQL and disposable S3 integration checks pass with Ruff,
  formatting, Pyright, Alembic, dependency audit and container scan.
- A restore rehearsal records actual backup IDs, a restored database and bucket,
  digest validation, measured RPO/RTO and cleanup approval. Until that external
  evidence exists, G06 remains operationally incomplete.

## Approval checkpoint

Owner approval is required before implementation because this proposal selects
AWS services, retention periods, recovery targets and privileged deletion rules.
Approval authorizes repository code, tests, templates and documentation only.
It does not authorize creating billable AWS resources, enabling an irreversible
compliance lock, deleting evidence or deploying production.

## Primary references checked

- [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
- [S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [RDS PostgreSQL SSL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html)
- [RDS PostgreSQL extensions](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html)
- [RDS backup and point-in-time restore](https://docs.aws.amazon.com/AmazonRDS/latest/gettingstartedguide/managing-backup-restore.html)
- [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)
- [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

