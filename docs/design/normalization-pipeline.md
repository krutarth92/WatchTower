# Deterministic normalization pipeline

Status: Task 05 implementation contract, 2026-09-28.

## Boundary and stages

The pipeline consumes a `NormalizationRecord` emitted by a source connector. It
never fetches source data and never deletes or replaces raw evidence. Every
record retains `source_id`, `raw_evidence_id`, the source-native ID, source type,
object index and a hash of the exact source object.

Processing uses five explicit stages:

1. **parse** validates source-specific fields and timestamp syntax,
2. **normalize** maps supported source fields into a canonical contract,
3. **validate** enforces canonical text, timestamp and provenance rules,
4. **deduplicate** compares the source-scoped native ID with existing data,
5. **persist** inserts or updates the canonical observation.

The source parser and canonical normalizer are separate protocols. Task 05
implements one MITRE ATT&CK parser/normalizer and one PostgreSQL observation
persister rather than a universal plugin system.

## ATT&CK mapping

Task 05 maps STIX `intrusion-set` objects to imported, observed WATCHTOWER
Observations. The STIX ID becomes `source_native_id`; `name` becomes the title;
`description` becomes the summary, with the source name used when description is
absent; `modified` becomes `observed_at`; and optional `first_seen`/`last_seen`
remain optional. Every timestamp is required to carry an offset and is converted
to UTC. Source-native aliases, external references, STIX version, created and
modified values remain in JSON metadata.

Other valid STIX types are recorded as `rejected` with the deterministic reason
`unsupported object type`; this is an explicit boundary rather than a silent
drop. Technique, campaign, relationship and actor-identity mapping require their
own reviewed semantics in later work. This task does not infer that similarly
named intrusion sets are the same actor.

## State and failure semantics

Each raw bundle object has one `normalization_records` row keyed by raw evidence
and object index. It records the source-native identity, object hash, latest
stage, status, bounded reason, attempt count and optional resulting Observation.
Statuses are `succeeded`, `deduplicated`, `rejected` and `failed`.

Expected unsupported types are rejected without failing the whole raw bundle.
Malformed supported records and unexpected stage failures are recorded and
raised to the connector, which marks aggregate raw processing failed while
retaining the bytes. Retrying the same record increments its attempt count and
cannot create another Observation.

## Deduplication and replay

The canonical identity is `(source_id, source_native_id)`, matching the existing
Observation uniqueness contract. An identical replay is `deduplicated`. A newer
source `modified` timestamp deterministically updates the existing Observation
and its raw provenance. An older record is retained in the normalization ledger
as deduplicated while the newer canonical Observation remains unchanged. Equal
timestamps with different canonical content are rejected as a conflict so
arrival order cannot silently choose a value.

The pipeline flushes but does not commit. Its caller owns the transaction. A
nested transaction contains database write failures so the rejection/failure
ledger can still be recorded and the raw evidence remains replayable.

## Safety and scope

Source payloads are untrusted JSON values. They are validated, bounded where
stored in constrained columns, and never executed. Error records contain stage
and controlled reasons rather than payload bodies or database connection text.
No LLM, embedding, fuzzy identity match, public write API, worker or live source
dependency is part of this pipeline.
