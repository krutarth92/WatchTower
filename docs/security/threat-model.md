# WATCHTOWER threat model

Status: Task 15 baseline, 2026-09-29.

## Scope and security objective

WATCHTOWER stores and interprets intelligence controlled by external publishers.
Every fetched byte, STIX object, Sigma rule, title, description, citation,
locator and retrieved model context is untrusted. The objective is to preserve
provenance and availability without executing source content, allowing it to
select network destinations, exposing unpublished material, or allowing it to
become trusted model instructions.

This review covers the implemented FastAPI API, PostgreSQL data model, Redis and
Dramatiq jobs, fixed MITRE ATT&CK connector, local object-store adapter,
deterministic normalization, technical-artifact parsers, and disabled-by-default
research boundary. It does not claim production hosting controls. The referenced
`docs/design/system-workflow-reference.md` does not exist and its contents were
not inferred.

## Assets, actors, and trust boundaries

Protected assets are unpublished intelligence and raw evidence, provenance and
source identity, operator credentials, database/Redis credentials, object-store
objects, job integrity, system availability, and the separation between sourced
facts and model interpretation.

Relevant attackers include an unauthenticated internet client, a client holding
malicious source content, a compromised upstream publisher, a party that has
obtained the operator token, and a tenant or local process with more filesystem
or network access than intended. Compromise of the host administrator, database
superuser, or cloud account is outside application containment and must be
handled by deployment controls and incident response.

The main trust transitions are:

```text
internet client -> reverse proxy (future) -> FastAPI -> PostgreSQL
operator client -> operator token boundary -> administrative API
worker -> fixed HTTPS ATT&CK host -> raw bytes -> object storage + PostgreSQL
PostgreSQL evidence -> untrusted RAG context -> disabled provider boundary
PostgreSQL job UUID -> Redis transport -> worker -> durable job state
```

The local Compose deployment binds PostgreSQL and Redis to loopback. Uvicorn is
also documented as loopback-only. This is a development boundary and is not a
production network policy.

## Threat assessment

| Threat | Current control | Residual risk and required action | Status |
| --- | --- | --- | --- |
| SSRF and arbitrary URL fetching | The only network client uses a code-defined HTTPS ATT&CK URL. API input cannot choose a URL. Source/evidence locators are stored data and are never dereferenced. Environment proxy variables are ignored by the fetcher. | A compromised DNS, CA, upstream repository, or host network can still influence the fixed request. Production egress must resolve through controlled DNS and allow only approved HTTPS destinations. Any new connector needs a reviewed allowlist; never reuse stored locators as fetch targets. | Controlled in code; deployment control required |
| Malicious redirects | HTTP redirects are disabled and every redirect response fails closed. | New clients must keep this rule or revalidate every redirect target against an exact scheme/host/port allowlist. | Controlled in code |
| Compressed responses, archives, and decompression bombs | The connector requests identity encoding and rejects every encoded response before iterating content. No ZIP, TAR, or other archive is extracted. Streamed unencoded bytes are capped. | A future archive feature must limit compressed bytes, expanded bytes, entry count, nesting, paths, and CPU/time, and extract in an isolated directory. | Controlled for current path; future feature gate |
| Oversized requests and source payloads | HTTP bodies default to 64 KiB and are rejected at 413 using declared or streamed size. Fixed-source retrieval, raw intake, local storage, and artifact ingestion have byte limits. Searches, pages, RAG context, jobs, retries, and queue depth are bounded. | The edge proxy must enforce equal or lower header/body, connection, and request-time limits before traffic reaches Python. Parser CPU/memory can still be nonlinear within an allowed body; measure before raising limits. | Controlled in code and deployment |
| HTML/XML attacks | HTML and XML may be preserved as raw evidence but no current parser renders HTML or processes XML, DTDs, external entities, XInclude, stylesheets, or network references. API JSON responses send `nosniff`. | If rendering is added, escape/sanitize in the frontend and use a restrictive CSP. Any XML parser must disable DTD/entity expansion and network access. | Format not parsed; future feature gate |
| PDF/parser exploitation | There is no PDF parser. PDF bytes can only be stored by the internal intake boundary. STIX and Sigma parsing is bounded to internal ingestion and errors fail closed. YAML uses safe loading. | Do not add a native PDF/OCR/parser process to the API or worker trust domain. Use a patched, resource-limited sandbox with no network and treat output as untrusted. Keep parser libraries under advisory review. | PDF deferred; parser hardening ongoing |
| Unsafe file handling and traversal | Object keys are content-addressed and source-scoped. Absolute paths, traversal, backslashes, unsafe segments, collisions, and oversize objects are rejected. User filenames are basename metadata only. Writes use temporary files and atomic hard links; content is never executed. | Protect the storage root from untrusted local writers. A local attacker who can alter directories can race filesystem checks. Multi-host deployment must replace local storage with a private S3-compatible adapter. | Controlled for single-host development |
| Object-storage disclosure or overwrite | The application does not expose raw-object download URLs and uses immutable put-if-absent semantics. | Production must use a private bucket, block public ACLs/policies, use TLS and encryption at rest, separate read/write IAM roles, enable audit/versioning as policy requires, and avoid long-lived signed URLs. Retention and deletion policy remains a product decision. | Deployment blocker |
| SQL injection | SQLAlchemy expressions and bound parameters handle all user values. `text()` and `literal_column()` occurrences contain application constants, not request strings. Database parameters are hidden from SQL logs and statements have timeouts. | Use a non-superuser runtime role with only required schema permissions. Review every future raw SQL fragment. Database network access must remain private and TLS-enabled in production. | Controlled in code; deployment least privilege required |
| Prompt injection and model data exfiltration | RAG is disabled by default, has no provider or credentials, and does not run in ingestion or ordinary reads. Retrieved records are passed as a typed `untrusted_context` separate from fixed system instructions. Output must cite retrieved evidence, use its intelligence type, and passes schema/support validation or fails closed. | Instruction separation reduces risk but cannot guarantee model obedience. Enabling a provider requires approval of data classes, egress destination, retention policy, model/version, budget, monitoring, and adversarial evaluation. Never grant a model tools, network access, or write access based on retrieved content. | Disabled; explicit approval gate |
| API abuse and missing rate limits | Inputs, pages, queries, response collections, request bodies, job attempts, job time, active backlog, and database statements are bounded. Administrative endpoints require the operator token. | There is no per-client request rate limit. Production must enforce IP/client quotas, connection limits, timeouts, and burst limits at an API gateway or reverse proxy shared by all workers. Do not trust forwarding headers except from that proxy. Application-local counters are insufficient for a multi-process deployment. | Production blocker |
| Authentication and authorization | Ingestion, research, artifact detail, queue metrics, and STIX export operations require a constant-time compared token of at least 32 characters. They fail closed when no token is configured. No browser cookie authentication is used and CORS is not enabled. | One static token has no roles, operator identity, expiry, revocation list, or per-action audit identity. Before remote administration, place these paths behind an identity-aware gateway with MFA, short-lived credentials, roles, audit logs, TLS, and brute-force limits. Rotate the fallback token through a secret manager. | Local/operator baseline only |
| Public disclosure and publication state | Raw objects and technical artifacts are not public routes. Operator responses use `Cache-Control: no-store`. Actor and search reads now require explicit per-record publication with fail-closed defaults and published provenance Sources; internal Actors are indistinguishable from missing records. | No authenticated, attributable editorial publication workflow exists yet. Keep publication mutation local until operator identity, authorization, audit and withdrawal policy are approved. | Read disclosure controlled; editorial operations pending |
| Secrets exposure | Database, Redis, and operator values use `SecretStr`; settings hide inputs; `.env*` is ignored except the example; SQL parameters are hidden. Application exceptions log only their class. Structured log fields recursively redact token, password, secret, authorization, cookie, database URL, and Redis URL keys. | Redaction is key-based and cannot make arbitrary message strings safe. Log event names must remain application constants and source bodies/headers must never be logged. Production secrets belong in a managed secret store with scoped access and rotation. Protect logs as sensitive data. | Controlled in code; operational policy required |
| Sensitive caching, sniffing, and browser rendering | Responses set `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`; operator paths also set `Cache-Control: no-store`. Raw artifacts are returned as JSON strings to authenticated operators. | Terminate TLS at a controlled proxy. Restrict or disable Swagger/OpenAPI in production if disclosure policy requires it; the default Swagger page loads browser assets from a third-party CDN. A future UI needs output encoding and CSP. | Partly controlled; deployment/UI work required |
| Dependency and parser supply-chain risk | Direct dependencies have bounded ranges; `uv.lock` fixes the environment and pip exports include hashes. CI gates locked runtime dependencies with pip-audit, gates the built image with Trivy, and retains a checksum-bound CycloneDX SBOM tied to the image content ID and commit. No runtime plugin loading or shell execution exists. | The deployment still uses a mutable source tag and no durable registry subject or signed provenance attestation exists. Review parser advisories and the bounded audit exception, assign patch ownership, publish production images by immutable digest, and attest that published subject. | CI controls active; release provenance pending |
| Logging hostile values | Request logs use validated/generated request IDs and only the URL path, never query strings, headers, or bodies. Connector metrics omit payloads. Controlled errors omit database and arbitrary exception messages. Central redaction covers sensitive structured keys. | Parser validation text is stored with operator-only artifacts and may include source fragments; treat it as untrusted data in any future UI. Define retention/access controls and alert without copying raw payloads. | Controlled in code; operations required |
| Outbound network control | The only fetch is fixed, uses HTTPS, rejects redirects and content encodings, has connect/total timeouts and byte limits, and ignores ambient proxy configuration. RAG has no live adapter. | Enforce egress deny-by-default at the host/VPC and explicitly allow required DNS and approved HTTPS destinations. Metadata services, RFC1918/link-local ranges, and cloud control planes must not be reachable by future content-selected destinations. | Deployment control required |
| Job-queue abuse | Only an authenticated fixed job kind is accepted. Messages contain only UUIDs; PostgreSQL is authoritative. Idempotency, row locks, attempts, exponential retry, leases, hard timeouts, recovery batches, active capacity, and HTTP 429 backpressure bound work. Redis is loopback-only in development. | Production Redis needs private networking, authentication/ACLs, TLS where supported, memory/maxmemory policy, persistence/availability choices, and queue-depth/oldest-job alerts. Never expose Redis publicly. Consider separate queues only after measured conflicting job classes exist. | Controlled in code; deployment hardening required |
| Error and metadata disclosure | API errors are stable and omit internal exception text. Readiness reports only ready/not-ready. Request IDs accept a restricted character set and length. | Uvicorn and proxy access-log formats must be reviewed before public deployment. Health endpoints can be public only if infrastructure policy accepts their availability signal. | Controlled in application |

## High-confidence Task 15 changes

This task made four bounded changes:

1. Fixed-source HTTP requests now ask for identity encoding, reject any encoded
   response, and ignore ambient proxy variables. This prevents automatic
   decompression from bypassing the post-decompression byte boundary and keeps
   the destination policy deterministic.
2. A global 64 KiB HTTP request-body boundary rejects both declared and streamed
   oversized bodies with HTTP 413 before route work. The value is configurable
   but capped at 10 MiB.
3. Application responses add `nosniff` and `no-referrer`; authenticated
   operational responses also disable caching.
4. JSON logging recursively redacts values under common secret-bearing field
   names while preserving safe diagnostic fields.

Regression tests cover compressed-response rejection, the identity-encoding
request, declared and chunked request limits, response headers, and nested log
redaction.

## Deployment release gates

Do not expose the current service publicly until all of these are true:

- A publication-state contract prevents public actor/search routes from
  returning drafts or internal records.
- A TLS reverse proxy or API gateway enforces body/header limits, shared rate
  limits, connection/time limits, trusted-host handling, and forwarding-header
  trust.
- Administrative routes use an identity-aware authentication and authorization
  layer with MFA, short-lived credentials, roles, audit identity, and rotation.
- PostgreSQL, Redis, and object storage are private, least-privileged, encrypted,
  backed up, monitored, and covered by tested restore procedures.
- Host/VPC egress is deny-by-default with an explicit allowlist for approved
  source endpoints; future model-provider egress remains disabled until approved.
- Dependency and container advisory scanning plus retained SBOM generation are
  active; patch ownership and immutable, attested production image references
  are established in release operations.
- Log access, retention, redaction review, alerting, and incident response are
  owned and tested.

## Security invariants for future work

- Never turn a stored locator, model output, artifact field, or source string
  into a network request, filesystem path, SQL fragment, template, shell command,
  or job name without a new explicit allowlist and test boundary.
- Never parse or render a new hostile format in the API process by default.
- Never allow retrieved content to change model instructions or grant tools.
- Never expose an administrative route merely because it is read-only; raw
  artifacts, queue state, and exports remain sensitive.
- Keep source facts immutable and distinguish imported observations from
  assessments and model interpretation through every output path.
