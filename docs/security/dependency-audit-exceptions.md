# Dependency audit exceptions

Status: one bounded exception, reviewed 2026-09-29.

## DiskCache unsafe deserialization advisory

Identifiers: `PYSEC-2026-2447`, `GHSA-w8v5-vhqr-4h9v`, and
`CVE-2025-69872`.

`diskcache==5.6.3` is a transitive dependency of `pysigma`, which WATCHTOWER
uses to parse and validate Sigma artifacts. No patched DiskCache release is
available. The advisory requires an attacker to write a malicious serialized
value into a cache directory that a victim later reads.

WATCHTOWER does not instantiate or read a DiskCache cache. Its Sigma path uses
`SigmaCollection.from_yaml`, and the application containers have a read-only
root filesystem. The only writable paths are the API temporary filesystem and
the worker's raw-evidence volume; neither is configured as a DiskCache cache.
The advisory therefore is not reachable through the current application path.

CI ignores only the two audit identifiers above. All other dependency findings
still fail the audit. Remove the exception when PySigma removes DiskCache,
DiskCache publishes a patched release, or WATCHTOWER begins using DiskCache.
Recheck this exception during every dependency update and no later than
2026-12-31.
