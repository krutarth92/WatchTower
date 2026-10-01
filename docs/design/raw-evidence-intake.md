# Raw evidence intake contract

Status: Task 03 implementation contract, 2026-09-27.

## Boundary

Connectors submit retrieved bytes and validated retrieval metadata to one service.
They do not write files, choose object keys, calculate hashes, create database
rows or call downstream parsers. The service stores immutable content and returns
the persisted RawEvidence reference. Normalization consumes that reference later.

```text
connector bytes + metadata
  -> validate and enforce size
  -> SHA-256 and deterministic object key
  -> immutable object store
  -> idempotent RawEvidence row
  -> pending processing state
```

The service flushes database changes but does not commit. Its caller owns the
transaction. A database rollback can leave a content-addressed object without a
row; repeating the same submission safely reuses that object. A later cleanup job
may remove unreferenced objects, but Task 03 does not create background workers.

## Source registry

`SourceRegistry.register` accepts a name, kind, optional HTTP(S) base URL,
licensing information, policy notes and JSON metadata. Repeating the same
registration returns the existing Source. Reusing a name with conflicting values
raises a conflict instead of silently modifying provenance policy. Source updates
require a future explicit administrative contract.

## Submission fields

`RawEvidenceSubmission` requires:

- registered `source_id`,
- non-empty content bytes,
- source URL or stable location string,
- timezone-aware fetch timestamp,
- a media type without parameters.

It optionally accepts publication time, source-native ID, filename hint and JSON
metadata. Publication time cannot be later than fetch time. Unknown fields,
control characters, naive timestamps, non-JSON metadata and invalid media types
are rejected before storage.

## Idempotency and versioning

SHA-256 is calculated over the exact submitted bytes. `(source_id, hash)` is the
database idempotency key and has a unique constraint. Repeated bytes from the same
source return the existing row with `duplicate=true`. Changed bytes create a new
row even when source-native IDs or locations match, preserving version history.
The same bytes from different sources remain separate provenance records.

Concurrent submissions use a nested database transaction and the unique
constraint as the final arbiter. Object keys are also content-addressed, so a
losing concurrent write cannot overwrite different content.

## Object storage

The `ObjectStore` protocol exposes put-if-absent, read and existence operations
using portable POSIX-style keys. This is the S3-compatible boundary: a future S3
adapter can implement the protocol without changing connector or intake code.

The development `LocalObjectStore` writes beneath a configured root. It rejects
absolute paths, traversal, backslashes, unsafe path segments and oversized data.
It writes a temporary file, flushes it, then creates the target atomically. An
existing key is reused only when its bytes match. The service builds keys as:

`raw/<source UUID>/<first two hash characters>/<full SHA-256>.<media extension>`

User filenames never control directories or object identity. A filename hint is
reduced to a safe basename for metadata only. Submitted bytes are never imported,
opened by a shell or executed.

## Size and state

`WATCHTOWER_MAX_RAW_EVIDENCE_BYTES` defaults to 10 MiB and is enforced by both
intake and local storage. It may be configured from 1 KiB through 100 MiB.

New successful records have retrieval status `succeeded` and processing state
`pending`. The service supports explicit transitions to `processing`, `succeeded`
or `failed`, records a bounded failure reason and attempt count, and can return a
completed/failed record to `pending` for replay. Invalid transitions fail without
changing the record. Task 08 will put these calls behind asynchronous jobs.

## Database additions

Source gains policy notes, license name and license URL. RawEvidence gains source
location, object key, safe filename, byte size, retrieval status, processing
state/error/attempts and last-processed time. New nullable reference columns keep
the migration safe for preexisting Task 02 rows; the Task 03 intake service always
populates them. Status fields receive non-null defaults.
