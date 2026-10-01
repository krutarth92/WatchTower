"""Reproducible local fixture and concurrent load runner for WATCHTOWER reads."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from sqlalchemy import delete, event, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = ROOT / "apps" / "api" / "src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from watchtower.core.config import Settings  # noqa: E402
from watchtower.db.models import (  # noqa: E402
    Actor,
    Alias,
    Behavior,
    Campaign,
    Evidence,
    IntelligenceType,
    Observation,
    Origin,
    Source,
    Technique,
)
from watchtower.db.session import build_engine  # noqa: E402
from watchtower.services.actor_read import ActorReadService  # noqa: E402
from watchtower.services.search import SearchService  # noqa: E402

MARKER = "task-13-api-benchmark-v1"
SOURCE_NAME = "WATCHTOWER Task 13 API benchmark"
BENCH_NAMESPACE = uuid5(NAMESPACE_URL, "https://watchtower.local/benchmarks/api/v1")
DEFAULT_ACTORS = 2_000
DEFAULT_TIMELINE = 100


def stable_id(kind: str, index: int = 0) -> UUID:
    return uuid5(BENCH_NAMESPACE, f"{kind}:{index}")


def seed_fixture(actor_count: int, timeline_size: int) -> UUID:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = build_engine(settings)
    try:
        with Session(engine) as session:
            existing = session.scalar(select(Source).where(Source.name == SOURCE_NAME))
            if existing is not None:
                actor = session.get(Actor, stable_id("primary-actor"))
                if actor is None:
                    raise RuntimeError("Benchmark source exists without its primary actor.")
                return actor.id

            source = Source(
                id=stable_id("source"),
                name=SOURCE_NAME,
                kind="benchmark",
                base_url="https://example.invalid/watchtower-benchmark",
                source_metadata={"benchmark": MARKER},
            )
            primary = Actor(
                id=stable_id("primary-actor"),
                canonical_name="Benchmark Beacon Group",
                normalized_name="benchmark beacon group",
                description="Representative actor for local API scalability measurements.",
                actor_metadata={"benchmark": MARKER},
            )
            session.add_all([source, primary])

            behaviors = [
                Behavior(
                    id=stable_id("behavior", index),
                    name=f"Benchmark behavior {index:03d}",
                    normalized_name=f"benchmark behavior {index:03d}",
                    description="Repeatable benchmark behavior.",
                    behavior_metadata={"benchmark": MARKER},
                )
                for index in range(25)
            ]
            techniques = [
                Technique(
                    id=stable_id("technique", index),
                    source=source,
                    external_id=f"B{index:04d}",
                    name=f"Benchmark technique {index:03d}",
                    description="Repeatable benchmark technique.",
                    technique_metadata={"benchmark": MARKER},
                )
                for index in range(25)
            ]
            evidence = [
                Evidence(
                    id=stable_id("evidence", index),
                    source=source,
                    citation=f"Benchmark report section {index:02d}",
                    excerpt=(
                        "A representative evidence excerpt used to measure bounded timeline "
                        "response serialization and compression."
                    ),
                    locator=f"https://example.invalid/report#{index}",
                    captured_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
                    confidence=80,
                    origin=Origin.IMPORTED,
                    evidence_metadata={"benchmark": MARKER},
                )
                for index in range(10)
            ]
            session.add_all([*behaviors, *techniques, *evidence])

            primary.aliases.append(
                Alias(
                    id=stable_id("primary-alias"),
                    source=source,
                    name="Benchmark Beacon Alias",
                    normalized_name="benchmark beacon alias",
                    source_native_id="benchmark-primary-alias",
                    confidence=90,
                    alias_metadata={"benchmark": MARKER},
                )
            )
            for index in range(timeline_size):
                observed_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index)
                observation = Observation(
                    id=stable_id("primary-observation", index),
                    source=source,
                    source_native_id=f"benchmark-primary-observation-{index:04d}",
                    title=f"Benchmark beacon activity {index:04d}",
                    summary=(
                        "Benchmark beacon activity with representative explanatory text for "
                        "timeline response and full-text search measurement."
                    ),
                    observed_at=observed_at,
                    first_seen=observed_at,
                    last_seen=observed_at,
                    confidence=80,
                    intelligence_type=IntelligenceType.OBSERVED,
                    origin=Origin.IMPORTED,
                    observation_metadata={"benchmark": MARKER},
                )
                observation.evidence.append(evidence[index % len(evidence)])
                observation.behaviors.append(behaviors[index % len(behaviors)])
                observation.techniques.append(techniques[index % len(techniques)])
                primary.observations.append(observation)

            for index in range(1, actor_count):
                actor = Actor(
                    id=stable_id("actor", index),
                    canonical_name=f"Benchmark Actor {index:05d}",
                    normalized_name=f"benchmark actor {index:05d}",
                    description="Representative actor row for lookup and search cardinality.",
                    actor_metadata={"benchmark": MARKER},
                )
                actor.aliases.append(
                    Alias(
                        id=stable_id("alias", index),
                        source=source,
                        name=f"Benchmark Alias {index:05d}",
                        normalized_name=f"benchmark alias {index:05d}",
                        source_native_id=f"benchmark-alias-{index:05d}",
                        confidence=75,
                        alias_metadata={"benchmark": MARKER},
                    )
                )
                observation = Observation(
                    id=stable_id("observation", index),
                    source=source,
                    source_native_id=f"benchmark-observation-{index:05d}",
                    title=f"Benchmark beacon record {index:05d}",
                    summary="Benchmark beacon record for representative search cardinality.",
                    observed_at=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
                    confidence=70,
                    intelligence_type=IntelligenceType.OBSERVED,
                    origin=Origin.IMPORTED,
                    observation_metadata={"benchmark": MARKER},
                )
                actor.observations.append(observation)
                session.add(actor)
                if index % 4 == 0:
                    session.add(
                        Campaign(
                            id=stable_id("campaign", index),
                            source=source,
                            source_native_id=f"benchmark-campaign-{index:05d}",
                            name=f"Benchmark Campaign {index:05d}",
                            normalized_name=f"benchmark campaign {index:05d}",
                            description="Representative benchmark campaign.",
                            first_seen=observation.observed_at,
                            last_seen=observation.observed_at,
                            confidence=70,
                            intelligence_type=IntelligenceType.OBSERVED,
                            origin=Origin.IMPORTED,
                            campaign_metadata={"benchmark": MARKER},
                        )
                    )

            session.commit()
            return primary.id
    finally:
        engine.dispose()


def cleanup_fixture() -> None:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = build_engine(settings)
    try:
        with Session(engine) as session, session.begin():
            source = session.scalar(select(Source).where(Source.name == SOURCE_NAME))
            if source is None:
                return
            source_id = source.id
            session.execute(delete(Alias).where(Alias.source_id == source_id))
            session.execute(delete(Campaign).where(Campaign.source_id == source_id))
            session.execute(delete(Observation).where(Observation.source_id == source_id))
            session.execute(delete(Evidence).where(Evidence.source_id == source_id))
            session.execute(delete(Technique).where(Technique.source_id == source_id))
            session.execute(delete(Actor).where(Actor.actor_metadata["benchmark"].astext == MARKER))
            session.execute(
                delete(Behavior).where(Behavior.behavior_metadata["benchmark"].astext == MARKER)
            )
            session.delete(source)
    finally:
        engine.dispose()


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return ordered[index]


async def request_once(
    client: httpx.AsyncClient,
    path: str,
    accept_encoding: str,
) -> tuple[int, float, int, str | None]:
    started = perf_counter()
    raw_size = 0
    encoding = None
    async with client.stream(
        "GET",
        path,
        headers={"Accept-Encoding": accept_encoding},
    ) as response:
        encoding = response.headers.get("content-encoding")
        async for chunk in response.aiter_raw():
            raw_size += len(chunk)
    return response.status_code, (perf_counter() - started) * 1000, raw_size, encoding


async def run_scenario(
    client: httpx.AsyncClient,
    name: str,
    path: str,
    requests: int,
    concurrency: int,
    accept_encoding: str,
) -> dict[str, Any]:
    for _ in range(min(5, requests)):
        await request_once(client, path, accept_encoding)

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_request() -> tuple[int, float, int, str | None]:
        async with semaphore:
            return await request_once(client, path, accept_encoding)

    started = perf_counter()
    results = await asyncio.gather(*(bounded_request() for _ in range(requests)))
    elapsed = perf_counter() - started
    statuses = Counter(item[0] for item in results)
    latencies = [item[1] for item in results]
    sizes = [item[2] for item in results]
    encodings = Counter(item[3] or "identity" for item in results)
    return {
        "name": name,
        "path": path,
        "requests": requests,
        "concurrency": concurrency,
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(requests / elapsed, 2),
        "status_counts": dict(sorted(statuses.items())),
        "latency_ms": {
            "mean": round(mean(latencies), 3),
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3),
        },
        "transfer_bytes": {
            "mean": round(mean(sizes), 1),
            "min": min(sizes),
            "max": max(sizes),
        },
        "content_encoding_counts": dict(sorted(encodings.items())),
    }


async def run_load(args: argparse.Namespace) -> dict[str, Any]:
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(base_url=args.base_url, limits=limits, timeout=timeout) as client:
        ready = await client.get("/ready")
        ready.raise_for_status()
        scenarios = [
            ("actor_lookup", f"/api/v1/actors/{args.actor_id}"),
            (
                "timeline_100",
                f"/api/v1/actors/{args.actor_id}/timeline?limit=100",
            ),
            (
                "search_25",
                f"/api/v1/search?{urlencode({'q': args.query, 'limit': 25})}",
            ),
        ]
        results = []
        for name, path in scenarios:
            results.append(
                await run_scenario(
                    client,
                    name,
                    path,
                    args.requests,
                    args.concurrency,
                    args.accept_encoding,
                )
            )
    return {
        "base_url": args.base_url,
        "actor_id": str(args.actor_id),
        "query": args.query,
        "accept_encoding": args.accept_encoding,
        "scenarios": results,
    }


def _plan_nodes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    result = []

    def visit(node: dict[str, Any]) -> None:
        result.append(
            {
                key: node[key]
                for key in (
                    "Node Type",
                    "Relation Name",
                    "Index Name",
                    "Actual Rows",
                    "Actual Loops",
                    "Actual Total Time",
                    "Shared Hit Blocks",
                    "Shared Read Blocks",
                )
                if key in node
            }
        )
        for child in node.get("Plans", []):
            visit(child)

    visit(plan)
    return result


def _explain(
    connection: Connection,
    statement: str,
    parameters: Any,
) -> dict[str, Any]:
    explained = connection.exec_driver_sql(
        f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}",
        parameters,
    ).scalar_one()
    document = explained[0]
    return {
        "planning_time_ms": round(float(document["Planning Time"]), 3),
        "execution_time_ms": round(float(document["Execution Time"]), 3),
        "nodes": _plan_nodes(document["Plan"]),
    }


def profile_queries() -> dict[str, Any]:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = build_engine(settings)
    statements: list[dict[str, Any]] = []
    starts: list[float] = []

    def before_cursor_execute(
        _connection: Connection,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        starts.append(perf_counter())
        statements.append({"sql": statement, "parameters": parameters})

    def after_cursor_execute(
        _connection: Connection,
        _cursor: Any,
        _statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        statements[-1]["duration_ms"] = (perf_counter() - starts.pop()) * 1000

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    scenarios: list[dict[str, Any]] = []
    try:
        calls = (
            ("actor_lookup", lambda session: session.get(Actor, stable_id("primary-actor"))),
            (
                "timeline_100",
                lambda session: ActorReadService().observations(
                    session,
                    stable_id("primary-actor"),
                    limit=100,
                    cursor=None,
                    date_from=None,
                    date_to=None,
                    intelligence_type=None,
                ),
            ),
            (
                "search_25",
                lambda session: SearchService().search(
                    session,
                    "benchmark beacon",
                    limit=25,
                ),
            ),
        )
        for name, call in calls:
            statements.clear()
            with Session(engine) as session:
                call(session)
            captured = [item.copy() for item in statements]
            with engine.connect() as connection:
                plans = [
                    _explain(connection, item["sql"], item["parameters"])
                    for item in captured
                    if item["sql"].lstrip().upper().startswith("SELECT")
                ]
            scenarios.append(
                {
                    "name": name,
                    "statement_count": len(captured),
                    "database_time_ms": round(
                        sum(float(item["duration_ms"]) for item in captured),
                        3,
                    ),
                    "plans": plans,
                }
            )
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        engine.dispose()
    return {"actor_id": str(stable_id("primary-actor")), "scenarios": scenarios}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed = subparsers.add_parser("seed", help="Create the idempotent local benchmark fixture")
    seed.add_argument("--actors", type=int, default=DEFAULT_ACTORS)
    seed.add_argument("--timeline-size", type=int, default=DEFAULT_TIMELINE)
    subparsers.add_parser("cleanup", help="Delete only the marked benchmark fixture")
    profile = subparsers.add_parser("profile", help="Count SQL and explain representative plans")
    profile.add_argument("--output", type=Path)
    run = subparsers.add_parser("run", help="Run the concurrent read scenarios")
    run.add_argument("--base-url", default="http://127.0.0.1:8000")
    run.add_argument("--actor-id", type=UUID, default=stable_id("primary-actor"))
    run.add_argument("--query", default="benchmark beacon")
    run.add_argument("--requests", type=int, default=100)
    run.add_argument("--concurrency", type=int, default=10)
    run.add_argument("--accept-encoding", choices=["gzip", "identity"], default="gzip")
    run.add_argument("--timeout", type=float, default=10.0)
    run.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "seed":
        if args.actors < 2 or args.timeline_size < 1:
            raise SystemExit("--actors must be at least 2 and --timeline-size at least 1")
        print(json.dumps({"actor_id": str(seed_fixture(args.actors, args.timeline_size))}))
        return
    if args.command == "cleanup":
        cleanup_fixture()
        print(json.dumps({"cleaned": True, "marker": MARKER}))
        return
    if args.command == "profile":
        result = profile_queries()
        output = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(f"{output}\n", encoding="utf-8")
        print(output)
        return
    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("--requests and --concurrency must be positive")
    result = asyncio.run(run_load(args))
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{output}\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
