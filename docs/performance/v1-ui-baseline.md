# V1 local UI timing baseline

Date: 2026-11-21

This is a local acceptance measurement for the deterministic
`watchtower_demo/v1` dataset. It is not a production service-level objective,
capacity result or AWS performance claim.

## Environment and method

- Windows host in Asia/Calcutta with Docker Desktop 4.92.0 and Docker Engine
  29.8.0.
- Compose production builds: Node.js 24 SvelteKit web service, Python 3.12
  FastAPI service, PostgreSQL 17 with pgvector and Redis 7.
- All traffic stayed on `127.0.0.1`; no external network was involved.
- The seeded graph contained the expected 25 records across actor, alias,
  indicator, CVE, behavior, technique, evidence, campaign and advisory data.
- Each route received one warm request followed by 20 sequential
  `Invoke-WebRequest` samples. Times are end-to-end client elapsed time in
  milliseconds and include local SvelteKit server rendering plus API/database
  work where the route requires it.

## Results

| Route | Status | Response bytes | Minimum | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 200 | 13,375 | 16.8 ms | 17.6 ms | 25.5 ms | 25.9 ms |
| Actor search | 200 | 13,991 | 22.9 ms | 24.7 ms | 29.7 ms | 126.6 ms |
| Indicator search | 200 | 13,740 | 23.1 ms | 24.9 ms | 31.9 ms | 35.8 ms |
| Actor dossier | 200 | 17,692 | 35.5 ms | 39.1 ms | 42.3 ms | 43.3 ms |
| Advisory | 200 | 15,285 | 23.1 ms | 24.5 ms | 25.8 ms | 28.9 ms |
| Integration register | 200 | 18,820 | 7.7 ms | 8.2 ms | 8.7 ms | 8.9 ms |
| API readiness | 200 | 18 | 3.5 ms | 3.8 ms | 4.3 ms | 4.3 ms |

The single actor-search maximum is retained rather than discarded; it did not
change the 24.7 ms median or 29.7 ms p95 for this run.

## Interpretation and limits

The baseline shows that the accepted local demo journeys respond successfully
and remain comfortably interactive on this machine. It does not measure
concurrency, browser rendering, geographic latency, production data volume,
AWS services, sustained load or failure recovery. Those require a licensed
representative dataset, an approved staging environment and a separately
agreed SLO during V2 productionization.
