from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from watchtower.db.models import Source
from watchtower.ingestion.contracts import SourceRegistration


class SourceConflictError(ValueError):
    """A source name is already registered with different immutable details."""


@dataclass(frozen=True, slots=True)
class SourceRegistrationResult:
    source: Source
    duplicate: bool


class SourceRegistry:
    def register(
        self, session: Session, registration: SourceRegistration
    ) -> SourceRegistrationResult:
        existing = session.scalar(select(Source).where(Source.name == registration.name))
        if existing is not None:
            self._require_same_registration(existing, registration)
            return SourceRegistrationResult(source=existing, duplicate=True)

        source = Source(
            name=registration.name,
            kind=registration.kind,
            base_url=str(registration.base_url) if registration.base_url else None,
            policy_notes=registration.policy_notes,
            license_name=registration.license_name,
            license_url=str(registration.license_url) if registration.license_url else None,
            source_metadata=registration.metadata,
        )
        try:
            with session.begin_nested():
                session.add(source)
                session.flush()
        except IntegrityError:
            existing = session.scalar(select(Source).where(Source.name == registration.name))
            if existing is None:
                raise
            self._require_same_registration(existing, registration)
            return SourceRegistrationResult(source=existing, duplicate=True)
        return SourceRegistrationResult(source=source, duplicate=False)

    @staticmethod
    def _require_same_registration(source: Source, registration: SourceRegistration) -> None:
        expected = (
            registration.kind,
            str(registration.base_url) if registration.base_url else None,
            registration.policy_notes,
            registration.license_name,
            str(registration.license_url) if registration.license_url else None,
            registration.metadata,
        )
        actual = (
            source.kind,
            source.base_url,
            source.policy_notes,
            source.license_name,
            source.license_url,
            source.source_metadata,
        )
        if actual != expected:
            raise SourceConflictError(
                f"Source {registration.name!r} already exists with different registration details"
            )
