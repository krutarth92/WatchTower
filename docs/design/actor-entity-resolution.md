# Conservative actor and alias resolution

Status: Task 06 implementation contract, 2026-09-28.

## Safety principle

False merges are more harmful than unresolved aliases. WATCHTOWER preserves the
exact source label in `Alias.name`; normalization is used only for deterministic
lookup. A source label is never rewritten to a canonical actor name.

## Exact and known rules

Names use Unicode NFKC normalization, case folding and whitespace collapse.
Punctuation, word order and tokens remain unchanged. An alias may auto-link only
when all exact evidence names one Actor and at least one of these rules applies:

1. its normalized label exactly equals an Actor's normalized canonical name, or
2. an active, manually curated known-alias rule exactly names that Actor.

Curated rules store the original alias spelling, canonical Actor, reason,
confidence, optional Evidence and the operator who added the rule. Examples such
as APT29, Cozy Bear, NOBELIUM and Midnight Blizzard may be represented by these
records only when evidence and a reviewer support them; no vendor relationship
is hardcoded in application code.

## Candidates and ambiguity

Existing source-specific Alias links with the same normalized label are candidate
evidence, not an automatic global merge rule. If exact evidence identifies more
than one Actor, the new Alias remains unresolved and all candidates are recorded.
If exact safe rules do not resolve the label, similarity can surface candidates
for review but can never link them. Similarity is deterministic and advisory;
zero, one or many fuzzy candidates all leave `Alias.actor_id` null.

## Source conflicts and preservation

`(source_id, normalized_name)` remains the source-specific Alias identity. A
repeat with the same label and source metadata is idempotent. Reusing that key
with different original spelling, native ID or metadata raises an explicit
conflict instead of overwriting the source assertion.

Source assertions may disagree. Existing linked Aliases are never relinked just
because a new rule or candidate appears. Conflicting exact assertions produce an
ambiguous decision and require manual review.

## Manual correction and audit

The service supports manual link, relink and unlink operations. Each requires an
operator and reason and may include confidence and Evidence. The Alias link is
updated while its source-native label remains unchanged.

Every automatic, unresolved and manual outcome appends an
`actor_resolution_decisions` row containing alias, selected and previous Actor,
method, reason, confidence, evidence, operator, candidate snapshot and decision
hash. A database identity sequence provides deterministic audit ordering even
when decisions share a transaction timestamp. Repeating an unchanged automatic
decision reuses the existing audit row; repeating an identical manual correction
is a no-op. Audit rows are not edited by the service.

## Transaction and scope

The service flushes but never commits. Its caller owns the transaction. Database
constraints enforce confidence, required reasons, decision shape and unique
source/rule identities. No fuzzy auto-merge, LLM, graph database, external
lookup, public write endpoint or background worker is introduced.
