import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Iterator[Session]:
    url = os.environ.get("WATCHTOWER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set WATCHTOWER_TEST_DATABASE_URL to run database integration tests")
    engine: Engine = create_engine(url, hide_parameters=True)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, expire_on_commit=False) as session:
            yield session
        if transaction.is_active:
            transaction.rollback()
    engine.dispose()
