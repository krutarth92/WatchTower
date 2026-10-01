# Evidence-grounded research RAG V1

Task 10 adds a bounded research path for actor overview, behavior-change and
evidence-support questions. It does not route ordinary actor reads or search
through a model. The research endpoint is operator-authenticated and returns 503
unless RAG is explicitly enabled and an in-process provider has been configured.

## Approved provider and data boundary

The approved baseline is provider-neutral and local-only. WATCHTOWER ships
protocols for one embedding provider and one grounded synthesis model, but no
live provider adapter or credentials. Evidence and source text must not leave
the machine, and the external-model budget is zero. Tests use deterministic
in-process providers. Enabling a real provider requires a separate decision on
the local runtime or external API, permitted source data and spending limit.

The missing `docs/design/system-workflow-reference.md` was not reconstructed or
treated as an architecture source.

## Data and pipeline

`evidence_embeddings` stores a provider model name, dimension count, content
hash and pgvector value. Each row has restrictive foreign keys to both its
`evidence` and `source` records. Indexing uses the citation and excerpt as one
bounded evidence unit and is idempotent for the evidence/model pair; changed
content replaces that pair's stale vector after its hash changes.
Task 10 does not split technical artifacts. Task 11 defines faithful typed
artifact retrieval, while any future RAG integration must consume those atomic
records without arbitrary chunking.

The request pipeline is:

1. Classify the question deterministically as actor overview, behavior change,
   or evidence support.
2. Embed the question and retrieve only evidence joined to the requested actor's
   observations. Apply optional observation-time filters, embedding model and
   dimension filters, and the cosine-distance relevance threshold.
3. Rerank candidates deterministically by semantic distance, recency and stable
   evidence identity.
4. Allocate the configured approximate token budget. Preserve record identity
   and provenance; truncate only excerpts when necessary.
5. Pass typed evidence records to a provider boundary separately from immutable
   system instructions that identify retrieved content as untrusted data.
6. Validate the structured draft. Every claim must cite retrieved evidence, and
   the claim's `observed` or `assessed` type must occur in its cited observation.
   Invalid or unsupported output fails closed as `insufficient_evidence`.

Responses label generated prose as `model_interpretation`. Citation objects
retain evidence, observation and source IDs, source metadata, time, origin and
intelligence type. No generated statement is written back to sourced records.

## Insufficient evidence and operational limits

The service does not call the synthesis model when retrieval returns no relevant
evidence or the context budget cannot fit one provenance-bearing record. It also
returns an insufficient-evidence response when provider output is malformed,
cites an unavailable record, or mislabels the cited intelligence type.

The current retrieval path performs an exact pgvector scan because the approved
provider is intentionally unspecified and vector dimensions are therefore not
fixed. Once a concrete local provider and dimension are approved, an HNSW or
IVFFlat index can be introduced from measured workload evidence. Embeddings are
not created automatically by ingestion in this task; a future approved provider
integration must call `EvidenceEmbeddingService` during processing or backfill.

## Evaluation contract

`tests/evaluations/rag-v1.json` and `tests/test_research_rag.py` cover retrieval
recall, citation membership, unsupported citations, insufficient evidence,
actor isolation, time filtering, intent selection, source metadata retention,
and observed/assessed separation. The fake evidence includes an instruction-like
string and verifies that system instructions remain a separate field.
