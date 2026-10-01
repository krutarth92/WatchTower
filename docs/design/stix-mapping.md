# STIX 2.1 export mapping

## Purpose and boundary

WATCHTOWER exports a conservative, actor-centered subset of its intelligence as
a standard STIX 2.1 bundle. The internal relational model remains authoritative
and independent from STIX. Export includes only facts whose meaning can be
preserved without custom STIX types, properties or extensions.

The first export surface is an operator-only bundle for one canonical actor.
The bundle contains the actor and supported entities explicitly linked to that
actor. Unlinked records and unsupported meanings are omitted.

## Entity mapping

| WATCHTOWER value | STIX 2.1 value | Mapping rule |
| --- | --- | --- |
| Canonical actor | `intrusion-set` | V1 actors represent named threat groups rather than individual people. Canonical name, description and linked alias names are preserved. |
| Campaign | `campaign` | Included only through an explicit internal `attributed-to` relationship with the requested actor. Description, first/last seen and confidence are preserved where present. |
| Technique | `attack-pattern` | Included only when explicitly linked to an observation of the requested actor. The source-native technique ID is retained as an external reference. |
| Observation, `observed` | `note` | The title and summary become note content. The note references the actor and any linked exported techniques and carries the label `watchtower:observed`. |
| Observation, `assessed` | `note` | The assessment remains a note and carries `watchtower:assessed`; it is never exported as STIX Observed Data. |
| Actor-to-technique association | `relationship` / `uses` | Derived only when an actor observation explicitly links that technique. Multiple supporting observations yield one stable relationship. |
| Campaign-to-actor attribution | `relationship` / `attributed-to` | Exported only for an internal relationship whose normalized type is exactly `attributed-to`. STIX direction is campaign to intrusion set. |
| Source and evidence | `external_references` | Safe HTTP(S) locators, source-native IDs and bounded citation/excerpt descriptions preserve provenance on the object they support. |

## Deliberate exclusions

- WATCHTOWER observations are not STIX `observed-data`. The internal records do
  not contain the required cyber-observable object references and may be
  analytic assessments. Mapping them to Observed Data would change their
  meaning.
- `indicator` is not emitted because V1 has no first-class indicator or STIX
  pattern model.
- Generic behaviors are omitted because their current meaning is too broad for
  a reliable STIX Domain Object mapping.
- Arbitrary internal relationship predicates are omitted. Only the exact
  `attributed-to` predicate has an approved semantic mapping.
- Raw evidence, embeddings, normalization records, ingestion jobs and technical
  artifact storage records are operational provenance or storage structures,
  not exportable intelligence objects in this subset.
- No custom objects, custom properties or extensions are emitted.

## Identifiers and determinism

Each exported object ID is a UUIDv5 derived from a fixed WATCHTOWER export
namespace, the STIX object type and the immutable internal UUID. A derived
actor-technique relationship uses the actor and technique UUIDs as its key. The
bundle ID is a UUIDv5 over the requested actor UUID and the sorted exported
object IDs. The same database state therefore produces the same IDs and object
order across exports.

Stable export IDs describe the same WATCHTOWER entity; they do not claim to be
the publisher's original STIX IDs. Original source identifiers remain in
external references.

## Time, confidence and provenance

- STIX `created` and `modified` use the internal record timestamps in UTC.
- A note records the observation's intelligence time and optional first/last
  seen values in clearly labelled content because Note has no equivalent
  machine fields and substituting its creation time would change the meaning.
- Campaign `first_seen` and `last_seen` are copied only when present.
- A derived `uses` relationship uses the earliest supporting observation
  creation time and latest supporting modification time.
- Attribution first/last seen values become the standard Relationship
  `start_time` and `stop_time` fields.
- Integer confidence values are copied directly because both models use the
  inclusive 0–100 scale. Missing confidence stays absent.
- External references use the source name as `source_name`. A source-native ID
  becomes `external_id`. Only locators with an HTTP or HTTPS scheme and a host
  become `url` values.
- Evidence citations and excerpts may be included as bounded descriptions.
  Export never repairs, guesses or fabricates provenance.

## Validation and API contract

The service serializes a bundle with `spec_version` 2.1 objects only. Tests parse
the complete output through the official OASIS `stix2` Python object model with
custom content disabled, then assert the semantic mapping and exclusions.

`GET /api/v1/operations/exports/stix/actors/{actor_id}` is operator-only and
returns the raw bundle with media type `application/stix+json`. Unknown actors
return a stable 404 application error. Export is read-only and does not mark
records as published.
