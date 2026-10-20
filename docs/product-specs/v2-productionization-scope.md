# WATCHTOWER V2 productionization scope

Status: direction approved on 2026-10-21. Implementation begins only after the
V1 user interface is accepted and an AWS deployment is separately authorized.

## Purpose

V2 turns the locally usable WATCHTOWER product into a proven, internet-facing
AWS service. It deploys and exercises the infrastructure contracts already in
the repository; it does not discard or repeat the completed backend work.

No AWS resource, DNS record, public endpoint or billable service is authorized
by this scope document.

## Entry criteria

- The V1 researcher interface is implemented and accepted against the versioned
  backend APIs.
- The owner approves an AWS account, Region, budget, deployment window and
  named identity, network, data, monitoring and incident owners.
- The target hostname, DNS ownership, representative dataset, expected traffic
  and retention requirements are recorded.
- Every deployment uses a reviewed change set and preserves a rollback path.

## Workstreams

1. **Identity and HTTPS edge:** deploy Cognito, MFA and group lifecycle; ALB,
   ACM, WAF, DNS, private-target isolation, measured rate limits, sanitized logs
   and alert delivery. Execute the Task 27 acceptance and rollback runbook.
2. **Durable evidence and database operations:** deploy private S3/KMS and
   Multi-AZ RDS PostgreSQL controls, least-privilege roles, PITR and governed
   backups. Execute the Task 26 integrity and coordinated restore rehearsal with
   measured RPO/RTO.
3. **Deployment proof:** exercise the private staging deployment and rollback
   workflow using an immutable reviewed commit or image digest.
4. **Monitoring and capacity:** establish dashboards, actionable alerts, log
   access/retention, backup-age monitoring, incident ownership and representative
   performance/SLO evidence.
5. **Release provenance:** publish the production container by immutable digest
   and retain verifiable provenance and SBOM evidence for that subject.

These workstreams correspond to remaining production-readiness gaps G03 through
G10. Repository-side templates and application controls already completed in
Tasks 25–27 remain the starting baseline.

## Separate product decisions

Live RAG execution, advisory withdrawal/redaction policy and any additional data
connectors remain separate product decisions. They are not silently approved by
moving AWS productionization to V2.

## V2 acceptance

V2 is complete only when the target AWS environment has reviewed evidence for:

- identity lifecycle, MFA, role separation, revocation and attributable actions;
- TLS, private targets, trusted forwarding, shared rate controls and sanitized
  logs;
- immutable evidence storage, verified database TLS, backup recovery points and
  a successful coordinated restore rehearsal;
- staging and production-compatible deployment/rollback;
- dashboards, alerts, incident ownership and measured capacity/SLOs; and
- an immutable published image with provenance and SBOM evidence.

Passing repository tests or validating CloudFormation is necessary evidence,
but cannot replace these deployed checks.
