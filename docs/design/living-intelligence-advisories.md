# Living intelligence advisory backend contract

## Boundary

An advisory is a stable public identity with an explicitly selected published
revision. Editorial changes append complete numbered `AdvisoryRevision`
snapshots; they do not update earlier snapshots. Timestamped `AdvisoryUpdate`
records form a separately sequenced, machine-readable timeline. This task adds
backend storage and APIs only. It does not generate editorial text or add a
frontend.

The original `docs/design/system-workflow-reference.md` is unavailable. This
contract therefore follows the approved V1 scope and existing Evidence, Actor,
Campaign, Technique and intelligence-type contracts without inferring content
from that missing reference.

## Data and history

`Advisory.slug` is stable and unique. Its `status`, `published_revision` and
`published_at` fields are changed together. A draft has no publication pointer;
a published advisory points to a positive revision number.

Each revision stores a title, summary, author, creation time, optional immutable
publication attribution and ordered typed sections:

1. `what_happened`
2. `actor_context`
3. `technical_analysis`
4. `detection`
5. `response`
6. `mitigation`
7. `watchtower_assessment`

Requests choose the section order and may omit sections that are not yet
applicable. A section type and position can occur only once in a revision. Each
section is explicitly `observed` or `assessed`; the API never blends the two.
Evidence and Actor/Campaign/Technique associations belong to the revision so a
historic public revision remains reproducible after later editorial changes.

Updates are append-only within an advisory, use a positive monotonic `sequence`,
include both `occurred_at` and storage `created_at`, identify the published
revision current when appended, carry `observed` or `assessed`, and may link
Evidence. A row lock on the advisory serializes revision and update number
allocation. No update or delete route exists for revisions or timeline entries.

## Publication and API

All writes require `X-WATCHTOWER-Operator-Token`:

- `POST /api/v1/operations/advisories`
- `POST /api/v1/operations/advisories/{id}/revisions`
- `POST /api/v1/operations/advisories/{id}/revisions/{version}/publish`
- `POST /api/v1/operations/advisories/{id}/updates`

Creation always produces draft revision 1. Adding a revision leaves the current
public revision unchanged. Publication records who published the revision and
moves the stable advisory pointer. Updates require an already published
revision. All linked IDs are validated before a write commits.

Public reads are bounded and filter publication state in SQL:

- `GET /api/v1/advisories?limit=25`
- `GET /api/v1/advisories/{slug}`
- `GET /api/v1/advisories/{slug}/revisions/{version}`
- `GET /api/v1/advisories/{slug}/updates?after_sequence=0&limit=50`

Draft advisories and unpublished revisions return the same 404 contract as
missing records. Detail includes at most the latest 50 updates in ascending
sequence. The updates endpoint provides forward pagination using
`after_sequence`; clients persist the last returned sequence. Limits are 1–100.

Publishing a later revision does not retract an earlier published revision.
Historic revision reads remain public once published. Publication is therefore
an editorially durable action; a future withdrawal requirement needs its own
explicit state and audit contract.

## Operational properties

Indexes support published listing, revision lookup and ordered update reads.
PostgreSQL constraints enforce publication shape, safe slugs, positive
version/sequence values, nonblank content and unique revision associations.
The migration is additive and reversible. Publishing and update creation are
ordinary database transactions; there is no cache or asynchronous publication
step in this baseline.
