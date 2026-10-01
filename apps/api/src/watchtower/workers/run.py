"""Settings-backed Dramatiq worker launcher."""

from dramatiq.cli import main as dramatiq_main
from dramatiq.cli import make_argument_parser

from watchtower.core.config import Settings


def worker_arguments(settings: Settings) -> list[str]:
    return [
        "watchtower.workers.tasks",
        "--processes",
        str(settings.ingestion_worker_processes),
        "--threads",
        str(settings.ingestion_worker_threads),
    ]


def main() -> int:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    arguments = make_argument_parser().parse_args(worker_arguments(settings))
    result = dramatiq_main(arguments)
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
