# WATCHTOWER

WATCHTOWER is an adversary-first cyber threat intelligence backend for studying
threat actors, their behavior over time, and the evidence behind each claim.

It provides a FastAPI service, PostgreSQL intelligence model, deterministic
MITRE ATT&CK ingestion, actor timelines, search, evidence-grounded research
contracts, STIX 2.1 export, technical artifact storage, asynchronous jobs, and
versioned living intelligence advisories.

## Current status

The backend is suitable for local development and private staging evaluation.
The [V1 readiness audit](docs/exec-plans/active/v1-readiness.md) lists the
remaining controls required before an internet-facing production release.

Frontend implementation is outside the current backend V1 scope.

## Quick start

Requirements:

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose

From the repository root:

```powershell
uv sync --locked
Copy-Item .env.example .env
```

Replace the password and operator-token placeholders in `.env`, then start the
database and Redis:

```powershell
docker compose up -d --wait
uv run --locked alembic upgrade head
```

Start the API:

```powershell
uv run --locked uvicorn watchtower.main:create_app --factory --host 127.0.0.1 --port 8000
```

Start the worker in another terminal:

```powershell
uv run --locked python -m watchtower.workers.run
```

Open:

- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- Readiness check: <http://127.0.0.1:8000/ready>

The complete setup and configuration reference is in [SETUP.md](SETUP.md).

## Main API areas

- `/api/v1/actors` — actor lookup, evidence and timelines
- `/api/v1/search` — deterministic cross-entity search
- `/api/v1/advisories` — published living intelligence advisories
- `/api/v1/operations/ingestion/jobs` — operator ingestion jobs
- `/api/v1/operations/artifacts` — faithful technical artifact reads
- `/api/v1/operations/exports/stix` — actor-centered STIX 2.1 export
- `/api/v1/operations/research/answers` — disabled-by-default grounded research

Operator routes require the `X-WATCHTOWER-Operator-Token` header.

## Validation

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked pytest
uv run --locked alembic check
```

PostgreSQL-backed tests require `WATCHTOWER_TEST_DATABASE_URL`. GitHub Actions
runs the full suite with PostgreSQL and Redis, builds the package and container,
audits dependencies, and scans the container for high-severity vulnerabilities.

## Documentation

- [V1 scope](docs/product-specs/v1-scope.md)
- [Intelligence data model](docs/design/intelligence-data-model.md)
- [Security threat model](docs/security/threat-model.md)
- [Private staging deployment](docs/deployment/ubuntu-ec2-staging.md)
- [Living intelligence contract](docs/design/living-intelligence-advisories.md)

## License

See [LICENSE](LICENSE).
