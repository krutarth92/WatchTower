# Durable data recovery

This runbook validates and restores WATCHTOWER's production PostgreSQL and raw
evidence as one data set. It applies to the AWS baseline in
`infra/aws/data-services.template.json`. The template does not create resources
until a deployment is separately authorized.

## Recovery objectives and ownership

- PostgreSQL point-in-time recovery target: RPO at most 5 minutes.
- Full raw-evidence backup target: RPO at most 24 hours.
- Complete application recovery target: RTO at most 4 hours.

These are rehearsal targets, not achieved service levels. The incident lead
chooses the restore point and owns traffic decisions. The database owner runs
RDS recovery and Alembic validation. The records/recovery owner restores S3 and
controls Object Lock or legal holds. A reviewer verifies the evidence before
traffic is enabled. The runtime role must never receive delete, retention, legal
hold, backup, restore, or KMS-administration permission.

## Routine evidence

At least daily, record the newest successful RDS automated backup and AWS Backup
recovery points for both RDS and S3, their completion times, retention expiry,
vault-lock state, and any failed jobs. Alert before either source exceeds its RPO
target. Retain CloudTrail data events and S3 inventory under the organization's
approved log policy.

Run the integrity command with the runtime database URL and object-store
settings from the deployment secret source:

```bash
uv run --locked watchtower-audit-evidence > integrity-report.json
```

Exit code zero means every referenced object matched its stored SHA-256 and byte
count and no unreferenced `raw/` objects were found. Missing, mismatched,
storage-error, and orphan findings produce exit code one. The command is
read-only and intentionally cannot repair or delete data.

## Coordinated restore rehearsal

1. Open a change/incident record. Record the incident time, selected restore
   time `T`, source DB identifier, source bucket, recovery-point IDs, approvers,
   and the UTC start time used to measure RTO.
2. Block ingestion and publication. Preserve the affected resources and logs;
   do not delete or overwrite them.
3. Restore RDS to a new private instance at `T`. Attach the approved parameter,
   subnet and security groups. Keep public access disabled.
4. Obtain the current AWS RDS CA bundle through the approved host build process.
   Create a temporary validation URL using `sslmode=verify-full` and
   `sslrootcert=<absolute CA path>`. Do not print the URL or password.
5. Confirm network isolation, KMS encryption, deletion protection, backup
   retention, engine version and `rds.force_ssl=1`. Connect with the migration
   identity and run:

   ```bash
   uv run --locked alembic heads
   uv run --locked alembic current
   uv run --locked alembic check
   ```

   `heads` and `current` must name the same revision and `check` must report no
   new upgrade operations.
6. For a database-only incident, validate against the existing immutable S3
   bucket. It may contain safe orphan objects written after `T`; record them and
   do not delete them during recovery.
7. For an S3 incident, restore the chosen AWS Backup recovery point into a new
   private, versioned, KMS-encrypted bucket with public access blocked. Apply the
   approved bucket policy and Object Lock controls before granting the validator
   read access. Do not reuse the affected bucket as the restore destination.
8. Configure the restored database and chosen bucket, then run
   `watchtower-audit-evidence`. The release gate requires zero missing,
   mismatched, or storage-error findings. Orphans require documented review;
   they must not be removed automatically.
9. Start the API and worker with the restored endpoints. Confirm `/health`,
   `/ready`, an authenticated operator read, a published public read, and a
   focused ingestion replay that reuses matching evidence without overwriting
   it. Verify the runtime role can read/write required rows and objects but
   cannot create roles/schemas/extensions or delete evidence.
10. Calculate measured RPO from `T` and the newest committed application event,
    and measured RTO from the recorded start to successful release validation.
    A target miss is a failed rehearsal even if the service eventually starts.
11. Have the independent reviewer sign the record containing recovery-point
    IDs, restored resource IDs, Alembic output, integrity JSON, security-control
    checks, application checks, measured RPO/RTO and unresolved findings.
12. Switch traffic only after sign-off. Keep the prior resources isolated until
    the rollback window ends. Cleanup needs a separate approved change and must
    respect Object Lock, legal holds, retention and deletion protection.

## Failure and rollback

Stop validation when TLS identity, schema revision, object integrity, private
networking, KMS encryption, IAM separation, or backup provenance cannot be
proved. Keep traffic on the last known safe environment, preserve all evidence,
and escalate to the incident and records owners. Never make a mismatched digest
pass by editing the database or replacing the object.

Redis is not restored. Durable job state remains in PostgreSQL, and the worker
requeues expired leases from the restored database after startup.

## Rehearsal record

Store each completed record in the approved operations evidence system with:

- change/incident ID, UTC start/end, participants and reviewer;
- source and restored DB/bucket identifiers and AWS recovery-point IDs;
- chosen `T`, newest recovered event, measured RPO and measured RTO;
- Alembic outputs, integrity JSON and application/security check results;
- every finding, owner and due date;
- traffic decision and separately approved cleanup decision.

G06 remains operationally incomplete until a real rehearsal record contains
this evidence and an independent reviewer accepts it.
