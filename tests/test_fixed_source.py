import gzip
from datetime import UTC, datetime

import httpx
import pytest

from watchtower.ingestion.contracts import SourceRegistration
from watchtower.ingestion.fixed_source import (
    FixedSourceDefinition,
    FixedSourceFetcher,
    FixedSourceFetchError,
)

DEFINITION = FixedSourceDefinition(
    key="fixture",
    url="https://source.example.test/feed.json",
    filename="feed.json",
    accepted_media_types=frozenset({"application/json"}),
    registration=SourceRegistration(name="Fixture", kind="dataset"),
)


def test_fixed_source_fetcher_accepts_only_bounded_exact_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == DEFINITION.url
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "ETag": '"fixture"'},
            content=b'{"ok":true}',
        )

    result = FixedSourceFetcher(
        DEFINITION,
        100,
        transport=httpx.MockTransport(handler),
        timeout=httpx.Timeout(1),
    ).fetch()

    assert result.content == b'{"ok":true}'
    assert result.media_type == "application/json"
    assert result.etag == '"fixture"'
    assert result.fetched_at.tzinfo == UTC


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(302, headers={"Location": "https://elsewhere.test"}), "redirects"),
        (httpx.Response(200, headers={"Content-Type": "text/html"}, text="no"), "media type"),
        (
            httpx.Response(
                200,
                headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
                content=gzip.compress(b"123"),
            ),
            "Encoded",
        ),
        (
            httpx.Response(
                200,
                headers={"Content-Type": "application/json", "Content-Length": "101"},
                content=b"1",
            ),
            "exceeds",
        ),
    ],
)
def test_fixed_source_fetcher_rejects_unapproved_responses(
    response: httpx.Response, message: str
) -> None:
    fetcher = FixedSourceFetcher(
        DEFINITION,
        100,
        transport=httpx.MockTransport(lambda request: response),
        timeout=httpx.Timeout(1),
    )

    with pytest.raises(FixedSourceFetchError, match=message):
        fetcher.fetch()


def test_fixed_source_fixture_timestamp_is_timezone_aware() -> None:
    assert datetime(2026, 11, 23, tzinfo=UTC).utcoffset() is not None
