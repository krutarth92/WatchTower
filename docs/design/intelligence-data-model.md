# WATCHTOWER V1 intelligence data model

Status: Task 02 design baseline, 2026-09-27.

## Purpose and boundaries

The model stores adversary-centered intelligence with explicit time, confidence
and provenance. It separates externally observed facts from WATCHTOWER analysis
and keeps raw source material distinct from normalized intelligence. This is a
relational PostgreSQL model; JSONB is limited to source-specific metadata.

The model does not copy the full STIX object model, resolve aliases automatically,
run AI, store raw binary bodies in PostgreSQL or define ingestion behavior. Task
03 will extend raw-evidence intake and object-storage rules without changing the
provenance relationships established here.

## Shared conventions

- Primary keys are application-generated UUIDs. They remain stable across API
  representations and do not reveal database sequence information.
- All timestamps are timezone-aware. `created_at` and `updated_at` describe the
  database record; domain dates use `observed_at`, `first_seen` and `last_seen`.
- Confidence is an optional integer from 0 through 100. Null means unscored,
  never zero confidence.
- `intelligence_type` is `observed` or `assessed`. Forecast is deliberately not
  accepted in V1. `origin` is `imported` or `watchtower`.
- Imported objects preserve a source and optional source-native identifier.
  WATCHTOWER assessments also use a registered internal source so provenance is
  never represented by a null source.
- JSONB metadata defaults to an empty object. It may retain source-native fields
  that do not deserve first-class columns, but cannot replace normalized names,
  dates, confidence, relationships or provenance.
- Database checks reject blank key text, invalid confidence, reversed time ranges,
  self-alias-like empty names and relationships without a meaningful predicate.

## Entities

### Source and raw evidence

`Source` describes a publisher, dataset or WATCHTOWER itself. Its stable name is
unique. `kind` and `base_url` support display and source policy work in Task 03.

`RawEvidence` is an immutable reference to an external object, not its body. It
belongs to one Source and records a storage URI, SHA-256 content hash, retrieval
time, optional publication time, MIME type and source-native identifier. The
source and content hash pair is unique, allowing the same bytes from distinct
sources without conflating provenance. Task 03 adds a source location, portable
object key, sanitized filename, size, retrieval status and replayable processing
state. Source records carry optional policy and licensing notes. Raw bodies stay
in the configured object store.

### Actor and alias

`Actor` is a WATCHTOWER canonical research entity with a unique normalized
canonical name. It is not a claim that every similar vendor name represents the
same group.

`Alias` stores exactly what a Source calls an actor. It belongs to a Source and
may link to an Actor. A null actor link means unresolved. The same normalized
name may occur under different sources or remain unresolved; no global alias
uniqueness or fuzzy auto-merge exists. An optional confidence records confidence
in the explicit link, not confidence in the source text.

### Observation and evidence

`Observation` is a time-bearing normalized statement. It must reference a Source
and may reference the RawEvidence object it was derived from. It stores a title,
summary, observed time, optional interval, confidence, intelligence type and
origin. Its source-native identifier is unique only within a source when present.

`Evidence` is a citable excerpt or locator. It must reference a Source and may
reference RawEvidence. It stores a citation label, optional excerpt and locator.
Observations connect to evidence through a many-to-many association because one
claim may rely on several citations and one citation may support several claims.
The mandatory Observation source ensures provenance even while evidence links
are assembled; application services should attach at least one Evidence item to
important published observations.

### Behavior, technique and campaign

`Behavior` is a normalized adversary behavior label and description. `Technique`
is a stable external technique reference, initially suited to ATT&CK IDs, with
the source that defines it. Observations associate independently with behaviors
and techniques through unique join tables.

`Campaign` is a named activity period with optional first/last seen dates and
confidence. It belongs to a Source and carries intelligence type/origin so a
source-described campaign is distinguishable from a WATCHTOWER assessment.

### Relationship

V1 `Relationship` records an Actor-to-Campaign relationship with a predicate,
source, optional Evidence, first/last seen, confidence, intelligence type and
origin. This deliberately narrow shape provides foreign-key integrity for the
first required campaign relationship. Actor-observation and observation-
behavior/technique links use dedicated association tables. Broader polymorphic
relationships require a later design change rather than unvalidated UUID pairs.

## Relationship map

```text
Source 1 ── * RawEvidence
Source 1 ── * Alias * ── 0..1 Actor
Source 1 ── * Observation * ── * Actor
RawEvidence 0..1 ── * Observation
Source 1 ── * Evidence * ── * Observation
RawEvidence 0..1 ── * Evidence
Observation * ── * Behavior
Observation * ── * Technique * ── 1 Source
Source 1 ── * Campaign
Actor 1 ── * Relationship * ── 1 Campaign
Source 1 ── * Relationship * ── 0..1 Evidence
```

Join-table primary keys prevent duplicate associations. Foreign keys use
`RESTRICT` for provenance and domain records so deleting a source cannot silently
orphan intelligence. Join rows cascade only when their owning domain record is
deliberately deleted. Task 02 does not expose deletion APIs.

## Query and index strategy

- Unique normalized actor/behavior names support exact lookup.
- Alias normalized names and source links support alias resolution candidates.
- Observation `observed_at`, `first_seen`, `last_seen`, source and raw-evidence
  indexes support timelines and provenance lookup.
- Campaign and Relationship time indexes support longitudinal actor/campaign
  queries. Relationship uniqueness prevents duplicate actor/predicate/campaign
  statements from the same source.
- Technique external ID and source are unique for deterministic lookup.
- Raw-evidence content hash and storage URI are indexed; content deduplication is
  scoped by source.

PostgreSQL full-text search is Task 09. This migration does not add speculative
GIN indexes, vector columns or Redis caching.

## Example object lifecycle

1. Register the MITRE ATT&CK Source.
2. Store a RawEvidence reference for a versioned STIX bundle and its SHA-256.
3. Create or locate an Actor. Store each vendor label as an Alias associated
   with its Source; link it only when identity is supported.
4. Normalize a source claim into an `observed`/`imported` Observation linked to
   the Source and RawEvidence. Attach an Evidence citation for the source object.
5. Associate the Observation with the Actor, Behavior and Technique it actually
   supports. Missing associations remain absent instead of being inferred.
6. Create a Campaign and an Actor-to-Campaign Relationship with its own source,
   evidence, confidence and time range.
7. A later WATCHTOWER interpretation is a separate `assessed`/`watchtower`
   Observation under the internal WATCHTOWER Source, citing existing Evidence.
   It never overwrites the imported Observation.

## Validation and migration expectations

Task 02 tests create the full lifecycle, query actor observations in chronological
order, preserve unresolved aliases, and exercise database checks for invalid
confidence, time ranges and blank identifiers. Alembic upgrades an empty database,
downgrades cleanly, and upgrades again. The downgrade removes only objects this
migration creates; it does not drop the database or external extensions.
