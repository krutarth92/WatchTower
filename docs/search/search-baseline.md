# Deterministic search baseline

Status: Task 09 implementation contract, 2026-09-29.

## Boundary

`GET /api/v1/search` provides one bounded, read-only search across actors,
source-preserved aliases, campaigns, behaviors, techniques, observations and
sources. PostgreSQL remains the only search system. This baseline adds no
embedding, vector search, language-model call or external search service.

The query is passed to PostgreSQL `websearch_to_tsquery` with the `english`
configuration. Quoted text therefore requests phrase adjacency, ordinary words
use AND semantics, and PostgreSQL handles punctuation as search syntax rather
than application-built SQL. Queries are trimmed, control-free, 2–200 characters
and always bound as parameters.

## Indexed documents

Each searchable table has a GIN expression index over a weighted `tsvector`:

| Entity | Weight A | Weight B/C | Weight D |
| --- | --- | --- | --- |
| actor | canonical name | description | string metadata |
| alias | alias name | source-native ID | string metadata |
| campaign | name | description | string metadata |
| behavior | name | description | string metadata |
| technique | external ID and name | description | string metadata |
| observation | title | summary and source-native ID | string metadata |
| source | name | kind, policy and licence title | string metadata |

JSON is converted to text for deterministic baseline matching. This can match
metadata keys as well as values; the response never returns raw metadata.
English stemming is useful for prose but is less suitable for arbitrary hashes,
IOCs and punctuation-heavy identifiers. Technique external IDs receive a
separate exact-match boost.

## Ranking and response

Case-insensitive exact display-name matches, normalized actor/alias/campaign/
behavior names and exact technique IDs receive a `100` point boost. The bounded
`ts_rank_cd(..., 32)` score is then added. Results sort by score descending,
entity type, case-folded title and UUID, making equal-score ordering stable.
The response exposes the entity type and ID, display title, bounded summary,
source/actor references where applicable, observation time, intelligence type,
origin, match kind and numeric score. It does not synthesize snippets or claims.

The endpoint returns at most 100 results and defaults to 25. Repeated
`entity_type` parameters select entity categories. `source_id` applies directly
to source-owned rows and relationally to actors/behaviors through their linked
aliases or observations. `intelligence_type`, `date_from` and `date_to` narrow
results to observations and campaigns; campaign dates use interval overlap.

## Evaluation and limitations

`tests/evaluations/search-baseline.json` is a small curated set covering exact
actor lookup, source alias lookup, campaigns, behaviors, technique IDs,
observation keywords, quoted phrases, metadata, source filtering and
intelligence-type filtering. The integration test seeds known records and
requires each expected entity to rank first. This is a regression baseline, not
a claim of broad relevance quality.

The 2026-09-29 validation run passed all 11 curated cases at rank 1 and produced
identical result-ID ordering on a repeated execution of every case. An EXPLAIN
check with sequential scans disabled confirmed that PostgreSQL can use the actor
GIN expression index for the same full-text predicate.

The baseline has no typo tolerance, fuzzy matching, synonym expansion,
language detection, per-user visibility model, highlighting or cursor
pagination. English stemming may underperform for non-English intelligence and
technical tokens. Representative production-scale relevance and latency remain
future measurement work; Task 09 only establishes deterministic behavior.
