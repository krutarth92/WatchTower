"""Rollback-only stage benchmark for the WATCHTOWER ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = ROOT / "apps" / "api" / "src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from watchtower.core.config import Settings  # noqa: E402
from watchtower.db.models import Actor, NormalizationStage  # noqa: E402
from watchtower.db.session import build_engine  # noqa: E402
from watchtower.ingestion.contracts import RawEvidenceSubmission  # noqa: E402
from watchtower.ingestion.mitre_attack import (  # noqa: E402
    ConnectorRunStatus,
    MitreAttackConnector,
    MitreAttackFetcher,
    register_mitre_attack_source,
)
from watchtower.ingestion.mitre_attack_normalization import (  # noqa: E402
    MitreAttackObservationNormalizer,
    MitreAttackRecordParser,
)
from watchtower.ingestion.normalization import (  # noqa: E402
    NormalizationPipeline,
    NormalizationRecord,
)
from watchtower.ingestion.raw_evidence import IntakeResult, RawEvidenceIntake  # noqa: E402
from watchtower.services.actor_resolution import (  # noqa: E402
    ActorResolutionService,
    AliasAssertion,
)
from watchtower.storage.local import LocalObjectStore  # noqa: E402
from watchtower.workers.queue import INGESTION_QUEUE, DramatiqJobQueue  # noqa: E402

BENCH_NAMESPACE = uuid5(NAMESPACE_URL, "https://watchtower.local/benchmarks/pipeline/v1")


def elapsed_ms(started: float) -> float:
    return (perf_counter() - started) * 1000


def build_bundle(object_count: int) -> bytes:
    objects = []
    for index in range(object_count):
        object_id = uuid5(BENCH_NAMESPACE, f"intrusion-set:{index}")
        objects.append(
            {
                "type": "intrusion-set",
                "spec_version": "2.1",
                "id": f"intrusion-set--{object_id}",
                "created": "2026-01-01T00:00:00Z",
                "modified": "2026-01-02T00:00:00Z",
                "name": f"Pipeline Benchmark Group {index:05d}",
                "description": (
                    "Generated deterministic ATT&CK fixture content for stage-level "
                    "pipeline measurement."
                ),
                "aliases": [f"Benchmark Alias {index:05d}"],
                "external_references": [
                    {"source_name": "benchmark", "external_id": f"G{index:05d}"}
                ],
                "confidence": 80,
            }
        )
    bundle_id = uuid5(BENCH_NAMESPACE, f"bundle:{object_count}")
    return json.dumps(
        {"type": "bundle", "id": f"bundle--{bundle_id}", "objects": objects},
        separators=(",", ":"),
    ).encode()


class TimedIntake(RawEvidenceIntake):
    def __init__(self, object_store: LocalObjectStore, max_bytes: int) -> None:
        super().__init__(object_store, max_bytes)
        self.durations_ms: list[float] = []

    def ingest(self, session: Session, submission: RawEvidenceSubmission) -> IntakeResult:
        started = perf_counter()
        try:
            return super().ingest(session, submission)
        finally:
            self.durations_ms.append(elapsed_ms(started))


def summarize_stage(values: list[float], object_count: int) -> dict[str, float | int]:
    total = sum(values)
    return {
        "calls": len(values),
        "total_ms": round(total, 3),
        "mean_ms": round(mean(values), 6) if values else 0.0,
        "objects_per_second": round(object_count / (total / 1000), 2) if total else 0.0,
    }


def measure_redis(settings: Settings, messages: int) -> dict[str, float | int]:
    namespace = f"watchtower-task14-benchmark-{uuid4()}"
    broker = RedisBroker(url=settings.redis_url.get_secret_value(), namespace=namespace)
    queue = DramatiqJobQueue(broker)
    try:
        started = perf_counter()
        for _ in range(messages):
            queue.enqueue(uuid4())
        duration = elapsed_ms(started)
        broker_api: Any = broker
        depth = int(broker_api.do_qsize(INGESTION_QUEUE))
        return {
            "messages": messages,
            "enqueue_ms": round(duration, 3),
            "messages_per_second": round(messages / (duration / 1000), 2),
            "observed_queue_depth": depth,
        }
    finally:
        broker.flush(INGESTION_QUEUE)
        broker.close()


def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    content = build_bundle(args.objects)
    max_bytes = max(settings.max_raw_evidence_bytes, len(content) + 1024)
    engine = build_engine(settings)
    stage_values: dict[NormalizationStage, list[float]] = defaultdict(list)

    def record_stage(stage: NormalizationStage, duration_ms: float) -> None:
        stage_values[stage].append(duration_ms)

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        source = register_mitre_attack_source(session)
        with TemporaryDirectory(prefix="watchtower-pipeline-benchmark-") as directory:
            store = LocalObjectStore(Path(directory), max_bytes=max_bytes)
            intake = TimedIntake(store, max_bytes=max_bytes)
            pipeline = NormalizationPipeline(
                session,
                MitreAttackRecordParser(),
                MitreAttackObservationNormalizer(),
                stage_recorder=record_stage,
            )
            connector = MitreAttackConnector(intake, pipeline)

            def response(_request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    200,
                    headers={"content-type": "application/json"},
                    content=content,
                )

            fetcher = MitreAttackFetcher(
                max_bytes,
                transport=httpx.MockTransport(response),
            )
            fetch_started = perf_counter()
            fetched = fetcher.fetch()
            mock_fetch_ms = elapsed_ms(fetch_started)
            assert fetched.content == content

            parse_started = perf_counter()
            _, parsed_objects = MitreAttackConnector._parse_bundle(content)
            validated = [
                MitreAttackConnector._validate_object(item, index)
                for index, item in enumerate(parsed_objects)
            ]
            bundle_parse_ms = elapsed_ms(parse_started)

            pipeline_started = perf_counter()
            result = connector.run_fixture(
                session,
                content,
                fetched_at=datetime(2026, 9, 29, tzinfo=UTC),
            )
            pipeline_total_ms = elapsed_ms(pipeline_started)
            if result.status is not ConnectorRunStatus.SUCCEEDED or result.raw_evidence_id is None:
                raise RuntimeError("Generated pipeline workload did not succeed.")

            first_pass = {
                stage.value: summarize_stage(values, args.objects)
                for stage, values in stage_values.items()
            }
            stage_values.clear()
            replay_started = perf_counter()
            for index, (object_id, object_type, payload) in enumerate(validated):
                pipeline.emit(
                    NormalizationRecord(
                        source_id=source.id,
                        raw_evidence_id=result.raw_evidence_id,
                        source_native_id=object_id,
                        object_type=object_type,
                        object_index=index,
                        payload=payload,
                    )
                )
            replay_total_ms = elapsed_ms(replay_started)
            replay_stages = {
                stage.value: summarize_stage(values, args.objects)
                for stage, values in stage_values.items()
            }

        actors = [
            Actor(
                canonical_name=f"Resolution Benchmark Actor {index:05d}",
                normalized_name=f"resolution benchmark actor {index:05d}",
                actor_metadata={"benchmark": "task-14"},
            )
            for index in range(args.resolution_actors)
        ]
        session.add_all(actors)
        session.flush()
        resolver = ActorResolutionService()
        exact_started = perf_counter()
        exact = resolver.resolve(
            session,
            AliasAssertion(
                source_id=source.id,
                name="Resolution Benchmark Actor 00000",
                source_native_id="task14-exact",
            ),
        )
        exact_ms = elapsed_ms(exact_started)
        fuzzy_started = perf_counter()
        no_match = resolver.resolve(
            session,
            AliasAssertion(
                source_id=source.id,
                name="Completely unrelated pipeline label",
                source_native_id="task14-no-match",
            ),
        )
        no_match_ms = elapsed_ms(fuzzy_started)

        redis = measure_redis(settings, args.messages)
        return {
            "workload": {
                "objects": args.objects,
                "bundle_bytes": len(content),
                "resolution_actors": args.resolution_actors,
                "redis_messages": args.messages,
            },
            "external_enrichment": {
                "mock_fetch_ms": round(mock_fetch_ms, 3),
                "live_network_measured": False,
            },
            "intake": {
                "total_ms": round(sum(intake.durations_ms), 3),
                "bytes_per_second": round(
                    len(content) / (sum(intake.durations_ms) / 1000),
                    2,
                ),
            },
            "bundle_parse_validate": {
                "total_ms": round(bundle_parse_ms, 3),
                "objects_per_second": round(args.objects / (bundle_parse_ms / 1000), 2),
            },
            "first_pass": {
                "total_ms": round(pipeline_total_ms, 3),
                "objects_per_second": round(args.objects / (pipeline_total_ms / 1000), 2),
                "stages": first_pass,
            },
            "deduplication_replay": {
                "total_ms": round(replay_total_ms, 3),
                "objects_per_second": round(args.objects / (replay_total_ms / 1000), 2),
                "stages": replay_stages,
            },
            "entity_resolution": {
                "in_job_path": False,
                "exact_match_ms": round(exact_ms, 3),
                "exact_linked": exact.alias.actor_id is not None,
                "no_match_scan_ms": round(no_match_ms, 3),
                "no_match_candidates": len(no_match.candidates),
            },
            "redis_dramatiq": redis,
            "inactive_stages": {
                "embeddings": (
                    "implemented storage/retrieval boundary; no configured ingestion provider"
                ),
                "ai_calls": "disabled and absent from deterministic ingestion",
            },
        }
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objects", type=int, default=250)
    parser.add_argument("--resolution-actors", type=int, default=1000)
    parser.add_argument("--messages", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.objects < 1 or args.resolution_actors < 1 or args.messages < 1:
        parser.error("workload counts must be positive")
    return args


def main() -> None:
    args = parse_args()
    result = benchmark(args)
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{output}\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
