from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import Actor, Advisory, PublicationState, Source
from watchtower.operations.demo_data import (
    DEMO_ADVISORY_SLUG,
    IDS,
    DemoDataError,
    DemoDataService,
)

pytestmark = pytest.mark.integration


def test_demo_seed_is_idempotent_and_cleanup_preserves_unrelated_rows(
    db_session: Session,
) -> None:
    sentinel = Source(
        name=f"Unrelated source {uuid4().hex}",
        kind="test",
        publication_state=PublicationState.PUBLISHED,
        source_metadata={"owner": "test"},
    )
    db_session.add(sentinel)
    db_session.flush()
    sentinel_id = sentinel.id

    service = DemoDataService()
    first = service.seed(db_session, environment="development")
    second = service.seed(db_session, environment="development")

    assert first.state == "created"
    assert second.state == "complete"
    assert first.records == second.records
    actor = db_session.get(Actor, IDS["actor"])
    assert actor is not None
    assert actor.canonical_name == "Frost Lantern"
    advisory = db_session.scalar(select(Advisory).where(Advisory.slug == DEMO_ADVISORY_SLUG))
    assert advisory is not None
    assert advisory.published_revision == 2
    assert len(advisory.revisions) == 2
    assert len(advisory.updates) == 1

    removed = service.cleanup(db_session, environment="development")

    assert removed.state == "removed"
    assert all(count == 0 for count in removed.records.values())
    assert service.status(db_session, environment="development").state == "absent"
    assert db_session.get(Source, sentinel_id) is sentinel


def test_demo_cleanup_fails_closed_when_marker_is_changed(db_session: Session) -> None:
    service = DemoDataService()
    service.seed(db_session, environment="development")
    actor = db_session.get(Actor, IDS["actor"])
    assert actor is not None
    actor.actor_metadata = {"owner": "someone-else"}
    db_session.flush()

    with pytest.raises(DemoDataError, match="not owned"):
        service.cleanup(db_session, environment="development")

    assert db_session.get(Advisory, IDS["advisory"]) is not None


def test_demo_commands_refuse_non_development_environment(db_session: Session) -> None:
    service = DemoDataService()

    with pytest.raises(DemoDataError, match="only in development"):
        service.seed(db_session, environment="test")
    with pytest.raises(DemoDataError, match="only in development"):
        service.cleanup(db_session, environment="production")
    with pytest.raises(DemoDataError, match="only in development"):
        service.status(db_session, environment="staging")
