# Canonical publication visibility

Status: Task 21 implementation contract, 2026-10-01.

## State and defaults

Records exposed by public actor or search APIs carry one shared
`publication_state`: `internal` or `published`. The state applies to Sources,
Actors, Aliases, Observations, Evidence, Behaviors, Techniques and Campaigns.
The ORM and database both default to `internal`. The migration preserves that
default for existing records, so deploying it does not publish current data.

Publication is explicit per record. Publishing an Actor does not publish its
aliases or future observations. Publishing an Observation does not publish its
Evidence, Behaviors, Techniques or Source. This prevents later ingestion from
silently expanding an already public record.

## Public read rules

- Actor UUID routes require a published Actor. Internal and absent Actors both
  return `actor_not_found` to avoid confirming a private record exists.
- Actor search considers published Actors and published Aliases backed by a
  published Source.
- Nested actor responses include only published records. Source-owned records
  additionally require a published Source.
- Cross-entity search requires the selected record to be published. Aliases
  also require a published Actor and Source; Campaigns, Techniques and
  Observations require a published Source.
- Publication state controls selection but is not exposed in public schemas.

Raw evidence, technical artifacts and operator-only resources keep their
existing private boundaries and do not gain a public visibility state here.

## Editorial boundary

This contract defines read behavior and secure defaults. It deliberately does
not create a mutation endpoint. A future editorial workflow must authenticate
an individual operator, authorize the record type, validate linked-record
states, record who changed the state and when, and support review or withdrawal
policy before remote administration is enabled.
