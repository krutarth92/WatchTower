# Actor timeline read API

Status: Task 07 implementation contract, 2026-09-28.

Task 21 adds the publication boundary defined in
[Canonical publication visibility](publication-visibility.md). Every route
requires a published Actor and filters nested records to explicitly published
material. Internal Actors use the same not-found response as absent Actors.

## Public boundary

The first public read surface is rooted at `/api/v1`. It contains read-only
actor routes and never invokes ingestion, resolution, an LLM, RAG or Redis.
Stable UUIDs identify actors and related records. Every response includes an
`X-Request-ID` header; clients may provide a printable request ID up to 128
characters, otherwise the API generates a UUID.

Routes:

- `GET /api/v1/actors/{actor_id}` returns the canonical Actor.
- `GET /api/v1/actors/search?q=...` searches canonical names and linked source
  aliases with a bounded result count.
- `GET /api/v1/actors/{actor_id}/aliases` returns source-preserved aliases.
- `GET /api/v1/actors/{actor_id}/observations` returns a newest-first page.
- `GET /api/v1/actors/{actor_id}/timeline` returns the same observation facts as
  timeline events with their behaviors, techniques, evidence and provenance.
- `GET /api/v1/actors/{actor_id}/associations` returns distinct behaviors and
  techniques observed for the Actor.
- `GET /api/v1/actors/{actor_id}/references` returns distinct Sources and
  Evidence connected through Actor observations.

## Response and error contract

Single resources use `{ "data": ... }`. Collections use `{ "data": [...],
"page": ... }` or a named bounded collection object where pagination is not
needed. Fields are represented by Pydantic response models, datetimes are UTC
ISO 8601 values and enums retain their stored values.

Errors always use `{ "error": { "code", "message", "request_id", "details" }
}`. Unknown actors use `actor_not_found`; invalid query parameters and malformed
cursors use `validation_error`. Internal exception details are never returned.

## Pagination and filtering

Observation and timeline pages use opaque URL-safe cursors over the descending
`(observed_at, id)` key. The default limit is 25 and the maximum is 100. A page
fetches `limit + 1` rows to derive `next_cursor`; there is no count query.
Optional inclusive `date_from`, `date_to` and `intelligence_type` filters are
part of the cursor fingerprint so a cursor cannot be reused with different
filters or Actor IDs. Invalid, altered or mismatched cursors fail safely.

Search accepts 2–100 visible characters and returns at most 20 distinct Actors.
Exact normalized canonical and alias matches rank before case-insensitive
contains matches. PostgreSQL full-text search remains Task 09.

## Query behavior and size limits

Published Actor existence is checked once per route. Observation pages eager-load their
source, evidence sources, behaviors and technique sources with a fixed number of
queries independent of page length. Association/reference routes use distinct
set-oriented queries. Aliases and all nested collections have deterministic
ordering. Actor search is capped at 20 results and five displayed matching names;
aliases at 100; page size at 100; per-event evidence, behaviors and techniques at
50 each; associations at 200 each; and references at 100 Sources and 200 Evidence
records. Every truncated collection exposes a corresponding flag.

The existing normalized-name, Actor/Alias foreign-key, observation time and join
table indexes are used before introducing caching. Task 07 adds no migration,
dependency, public write, RAG call or Redis cache.
