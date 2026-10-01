# Technical artifact handling

Task 11 stores STIX 2.1 objects/bundles, Sigma rules and ATT&CK technique
references as first-class records without replacing their source form. The
service is an internal ingestion boundary; the API added by this task is
read-only and operator-authenticated.

## Faithful storage and provenance

Each artifact stores the exact submitted UTF-8 text in `original_content` and
its SHA-256 digest. A separately parsed JSONB value supports structured reads
when parsing succeeds. JSONB is never treated as a byte-faithful replacement
for the original JSON or YAML. Invalid artifacts retain the same original text,
their partially parsed structure when available, and bounded validation errors.
The service never repairs source content.

Every artifact references a registered source. Imported artifacts must also
reference raw evidence from that same source. WATCHTOWER-generated artifacts
are explicitly marked `watchtower` and may omit raw evidence. The uniqueness key
is `(source_id, artifact_type, content_sha256)`, so replay is idempotent while a
changed artifact or the same content from another source remains a separate
provenance record.

## Validation rules

- Standard STIX input is parsed using the OASIS `stix2` Python library with
  custom objects/properties disabled and is restricted to STIX 2.1. A bundle is
  retained as one artifact and records its object count.
- Sigma input is parsed using SigmaHQ pySigma. Exactly one rule is accepted per
  atomic Sigma artifact; malformed YAML, invalid detection conditions and
  multi-rule documents are stored as invalid rather than silently repaired.
- ATT&CK technique input must parse as STIX 2.1 with ATT&CK custom properties,
  have type `attack-pattern`, provide a name, and contain a MITRE external
  reference matching `T####` or `T####.###`. The ATT&CK ID is its canonical ID.

Validation status is `valid` or `invalid`. Error text is normalized, bounded and
does not contain database errors or full source payloads.

## Atomicity and size

Small artifacts are never chunked. STIX bundles also remain whole in this
baseline so their object relationships and exact serialization are preserved.
Submissions are bounded to 10 MiB of UTF-8 text. There is no large-artifact
sectioning algorithm in V1; content above the limit must remain in raw object
storage until a format-specific, reviewed sectioning rule exists.

Task 11 does not automatically embed artifact content. The grounded research
path can retrieve typed artifact metadata through a later explicit integration,
but it must not split these artifacts into arbitrary semantic chunks.

## Retrieval

`GET /api/v1/operations/artifacts` provides bounded full-text search over title,
canonical ID and metadata, with artifact type, source, origin and validation
filters. Collection responses omit original content. The ID detail endpoint
returns the exact original, parsed structure, validation result and source/raw
provenance. Both routes require the operator token because artifacts can contain
unpublished source material.

No artifact write endpoint, automatic Sigma generation, source repair, STIX
export or publication behavior is included in this task.
