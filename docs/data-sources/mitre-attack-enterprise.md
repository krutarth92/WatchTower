# MITRE ATT&CK Enterprise STIX source

Status: approved reference connector source for Task 04.
Reviewed: 2026-09-27.

## Selection and source contract

The approved V1 scope names a versioned MITRE ATT&CK STIX dataset as the first
connector. No project document specifies a different first source. The original
`docs/design/system-workflow-reference.md` is absent, so no missing content is
inferred.

WATCHTOWER reads the Enterprise ATT&CK 19.2 release from this fixed URL:

`https://raw.githubusercontent.com/mitre-attack/attack-stix-data/v19.2/enterprise-attack/enterprise-attack-19.2.json`

The source is a UTF-8 JSON STIX 2.1 bundle. A valid payload has a top-level
`type` of `bundle`, a STIX bundle identifier, and an `objects` array. Task 04
performs only the structural checks needed to preserve the bundle and emit
source objects at the normalization boundary. Canonical domain mapping belongs
to Task 05.

Version 19.2 was published on 2026-08-05. The connector uses its official
`v19.2` release tag. The repository also publishes an unversioned
`enterprise-attack.json` file that follows the newest release; the connector
intentionally avoids it so replay does not silently change inputs. Changing the
pinned ATT&CK version is a reviewed code and documentation change.

Authoritative references:

- Repository and STIX 2.1 format: <https://github.com/mitre-attack/attack-stix-data>
- Release index: <https://github.com/mitre-attack/attack-stix-data/blob/master/index.md>
- Release tag: <https://github.com/mitre-attack/attack-stix-data/releases/tag/v19.2>
- Usage guidance: <https://github.com/mitre-attack/attack-stix-data/blob/master/USAGE.md>
- License: <https://github.com/mitre-attack/attack-stix-data/blob/master/LICENSE.txt>
- ATT&CK data access options: <https://attack.mitre.org/resources/working-with-attack/>

## Usage and retrieval policy

The connector makes one GET request per live run. It follows no redirects,
sets explicit connect/read/write/pool timeouts, accepts JSON or plain-text JSON
responses, checks `Content-Length` when present, and enforces the byte limit
while streaming. The production fetch path exposes no user-supplied URL.

The public repository does not publish a connector-specific request quota. Run
the versioned import deliberately rather than polling it frequently. If future
automation checks the collection index, it should use conditional requests and
backoff in a separately reviewed task.

MITRE grants research, development and commercial use provided copies reproduce
its copyright designation and license. Source registration retains the license
URL and the required notice:

`© 2026 The MITRE Corporation. This work is reproduced and distributed with the permission of The MITRE Corporation.`

## Provenance and replay

The exact response bytes are written to raw object storage before parsing. The
raw record stores the fixed locator, fetch time, release time, response media
type, bundle ID, ATT&CK domain/version, and available `ETag` and
`Last-Modified` headers. SHA-256 over the exact bytes is the replay identity.

An exact duplicate whose prior processing succeeded is skipped. A failed run is
requeued from the same raw bytes; an interrupted `processing` record is first
recovered to `pending` and then retried. A changed payload creates a new raw
evidence version. Object emissions carry both source and raw-evidence IDs, so
Task 05 can persist normalized records without losing provenance.

Malformed bundles remain preserved as raw evidence and finish in `failed`
state with a bounded diagnostic. A transport failure before any bytes arrive is
logged and reported without creating a false raw-evidence record.

## Task 05 normalization

STIX `intrusion-set` objects map deterministically to imported, observed
WATCHTOWER Observations. Their STIX ID is the source-native identity, `name` is
the title, optional `description` is the summary, and `modified` is the observed
timestamp. Optional source time ranges, aliases and external references remain
explicit. Other STIX object types receive a durable rejected ledger entry with
an unsupported-type reason; they are available for separately reviewed mappings
without being silently discarded or misrepresented as observations.
