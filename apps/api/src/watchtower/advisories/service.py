"""Transactional service for immutable advisory revisions and append-only updates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from watchtower.advisories.contracts import (
    ActorLinkRead,
    AdvisoryCreate,
    AdvisoryRead,
    AdvisorySummaryRead,
    AdvisoryUpdateCreate,
    EvidenceLinkRead,
    NamedLinkRead,
    RevisionInput,
    RevisionRead,
    SectionRead,
    TechniqueLinkRead,
    UpdateRead,
)
from watchtower.db.models import (
    Actor,
    Advisory,
    AdvisoryRevision,
    AdvisorySection,
    AdvisoryStatus,
    AdvisoryUpdate,
    Campaign,
    Evidence,
    Technique,
)


class AdvisoryNotFoundError(LookupError):
    pass


class AdvisoryConflictError(ValueError):
    pass


class AdvisoryReferenceError(ValueError):
    pass


class AdvisoryService:
    def create(self, session: Session, payload: AdvisoryCreate) -> AdvisoryRead:
        if session.scalar(select(Advisory.id).where(Advisory.slug == payload.slug)) is not None:
            raise AdvisoryConflictError("An advisory with this slug already exists.")
        advisory = Advisory(slug=payload.slug)
        session.add(advisory)
        session.flush()
        self._add_revision(session, advisory, payload, version=1)
        session.flush()
        return self._operator_read(session, advisory.id, 1)

    def add_revision(
        self, session: Session, advisory_id: UUID, payload: RevisionInput
    ) -> AdvisoryRead:
        advisory = self._locked(session, advisory_id)
        advisory.updated_at = datetime.now(UTC)
        version = (
            session.scalar(
                select(func.coalesce(func.max(AdvisoryRevision.version), 0)).where(
                    AdvisoryRevision.advisory_id == advisory.id
                )
            )
            or 0
        ) + 1
        self._add_revision(session, advisory, payload, version=version)
        session.flush()
        return self._operator_read(session, advisory.id, version)

    def publish(
        self, session: Session, advisory_id: UUID, version: int, published_by: str
    ) -> AdvisoryRead:
        advisory = self._locked(session, advisory_id)
        revision = session.scalar(
            select(AdvisoryRevision).where(
                AdvisoryRevision.advisory_id == advisory.id,
                AdvisoryRevision.version == version,
            )
        )
        if revision is None:
            raise AdvisoryNotFoundError
        now = datetime.now(UTC)
        if revision.published_at is None:
            revision.published_at = now
            revision.published_by = published_by
        advisory.status = AdvisoryStatus.PUBLISHED
        advisory.published_revision = version
        advisory.published_at = now
        session.flush()
        return self.public_get(session, advisory.slug)

    def add_update(
        self, session: Session, advisory_id: UUID, payload: AdvisoryUpdateCreate
    ) -> UpdateRead:
        advisory = self._locked(session, advisory_id)
        if advisory.status != AdvisoryStatus.PUBLISHED or advisory.published_revision is None:
            raise AdvisoryConflictError("Publish an advisory revision before adding updates.")
        revision = session.scalar(
            select(AdvisoryRevision).where(
                AdvisoryRevision.advisory_id == advisory.id,
                AdvisoryRevision.version == advisory.published_revision,
            )
        )
        if revision is None:
            raise AdvisoryConflictError("The published revision pointer is invalid.")
        sequence = (
            session.scalar(
                select(func.coalesce(func.max(AdvisoryUpdate.sequence), 0)).where(
                    AdvisoryUpdate.advisory_id == advisory.id
                )
            )
            or 0
        ) + 1
        update = AdvisoryUpdate(
            advisory=advisory,
            revision=revision,
            sequence=sequence,
            occurred_at=payload.occurred_at,
            title=payload.title,
            summary=payload.summary,
            intelligence_type=payload.intelligence_type,
            created_by=payload.created_by,
            evidence=self._resolve(session, Evidence, payload.evidence_ids, "evidence"),
        )
        advisory.updated_at = datetime.now(UTC)
        session.add(update)
        session.flush()
        return self._update_read(update)

    def public_list(self, session: Session, limit: int) -> list[AdvisorySummaryRead]:
        latest_update = (
            select(func.max(AdvisoryUpdate.occurred_at))
            .where(AdvisoryUpdate.advisory_id == Advisory.id)
            .correlate(Advisory)
            .scalar_subquery()
        )
        rows = session.execute(
            select(Advisory, AdvisoryRevision, latest_update)
            .join(
                AdvisoryRevision,
                (AdvisoryRevision.advisory_id == Advisory.id)
                & (AdvisoryRevision.version == Advisory.published_revision),
            )
            .where(Advisory.status == AdvisoryStatus.PUBLISHED)
            .order_by(Advisory.published_at.desc(), Advisory.id)
            .limit(limit)
        ).all()
        output = []
        for advisory, revision, latest in rows:
            assert advisory.published_revision is not None and advisory.published_at is not None
            output.append(
                AdvisorySummaryRead(
                    id=advisory.id,
                    slug=advisory.slug,
                    title=revision.title,
                    summary=revision.summary,
                    published_revision=advisory.published_revision,
                    published_at=advisory.published_at,
                    latest_update_at=latest,
                )
            )
        return output

    def public_get(self, session: Session, slug: str) -> AdvisoryRead:
        advisory = session.scalar(
            select(Advisory).where(
                Advisory.slug == slug, Advisory.status == AdvisoryStatus.PUBLISHED
            )
        )
        if advisory is None or advisory.published_revision is None:
            raise AdvisoryNotFoundError
        return self._read(session, advisory, advisory.published_revision, update_limit=50)

    def public_revision(self, session: Session, slug: str, version: int) -> AdvisoryRead:
        advisory = session.scalar(
            select(Advisory).where(
                Advisory.slug == slug, Advisory.status == AdvisoryStatus.PUBLISHED
            )
        )
        if advisory is None:
            raise AdvisoryNotFoundError
        revision = session.scalar(
            select(AdvisoryRevision).where(
                AdvisoryRevision.advisory_id == advisory.id,
                AdvisoryRevision.version == version,
                AdvisoryRevision.published_at.is_not(None),
            )
        )
        if revision is None:
            raise AdvisoryNotFoundError
        return self._read(session, advisory, version, update_limit=0)

    def public_updates(
        self, session: Session, slug: str, after_sequence: int, limit: int
    ) -> list[UpdateRead]:
        advisory_id = session.scalar(
            select(Advisory.id).where(
                Advisory.slug == slug, Advisory.status == AdvisoryStatus.PUBLISHED
            )
        )
        if advisory_id is None:
            raise AdvisoryNotFoundError
        updates = session.scalars(
            self._update_statement(advisory_id)
            .where(AdvisoryUpdate.sequence > after_sequence)
            .order_by(AdvisoryUpdate.sequence)
            .limit(limit)
        ).all()
        return [self._update_read(item) for item in updates]

    def _operator_read(self, session: Session, advisory_id: UUID, version: int) -> AdvisoryRead:
        advisory = session.get(Advisory, advisory_id)
        if advisory is None:
            raise AdvisoryNotFoundError
        return self._read(session, advisory, version, update_limit=50)

    def _read(
        self, session: Session, advisory: Advisory, version: int, update_limit: int
    ) -> AdvisoryRead:
        revision = session.scalar(
            self._revision_statement().where(
                AdvisoryRevision.advisory_id == advisory.id,
                AdvisoryRevision.version == version,
            )
        )
        if revision is None:
            raise AdvisoryNotFoundError
        updates: list[AdvisoryUpdate] = []
        if update_limit:
            updates = list(
                session.scalars(
                    self._update_statement(advisory.id)
                    .order_by(AdvisoryUpdate.sequence.desc())
                    .limit(update_limit)
                ).all()
            )
            updates.reverse()
        return AdvisoryRead(
            id=advisory.id,
            slug=advisory.slug,
            status=advisory.status,
            published_revision=advisory.published_revision,
            published_at=advisory.published_at,
            created_at=advisory.created_at,
            updated_at=advisory.updated_at,
            revision=self._revision_read(revision),
            updates=[self._update_read(item) for item in updates],
        )

    def _add_revision(
        self, session: Session, advisory: Advisory, payload: RevisionInput, version: int
    ) -> AdvisoryRevision:
        revision = AdvisoryRevision(
            advisory=advisory,
            version=version,
            title=payload.title,
            summary=payload.summary,
            created_by=payload.created_by,
            sections=[
                AdvisorySection(
                    section_type=item.section_type,
                    position=position,
                    intelligence_type=item.intelligence_type,
                    content=item.content,
                )
                for position, item in enumerate(payload.sections)
            ],
            evidence=self._resolve(session, Evidence, payload.evidence_ids, "evidence"),
            actors=self._resolve(session, Actor, payload.actor_ids, "actors"),
            campaigns=self._resolve(session, Campaign, payload.campaign_ids, "campaigns"),
            techniques=self._resolve(session, Technique, payload.technique_ids, "techniques"),
        )
        session.add(revision)
        return revision

    @staticmethod
    def _locked(session: Session, advisory_id: UUID) -> Advisory:
        advisory = session.scalar(
            select(Advisory).where(Advisory.id == advisory_id).with_for_update()
        )
        if advisory is None:
            raise AdvisoryNotFoundError
        return advisory

    @staticmethod
    def _resolve(session: Session, model: type, ids: list[UUID], label: str) -> list:
        if not ids:
            return []
        records = list(session.scalars(select(model).where(model.id.in_(ids))).all())
        if len(records) != len(ids):
            raise AdvisoryReferenceError(f"One or more linked {label} records do not exist.")
        by_id = {record.id: record for record in records}
        return [by_id[item] for item in ids]

    @staticmethod
    def _revision_statement():
        return select(AdvisoryRevision).options(
            selectinload(AdvisoryRevision.sections),
            selectinload(AdvisoryRevision.evidence),
            selectinload(AdvisoryRevision.actors),
            selectinload(AdvisoryRevision.campaigns),
            selectinload(AdvisoryRevision.techniques),
        )

    @staticmethod
    def _update_statement(advisory_id: UUID):
        return (
            select(AdvisoryUpdate)
            .options(
                selectinload(AdvisoryUpdate.evidence),
                selectinload(AdvisoryUpdate.revision),
            )
            .where(AdvisoryUpdate.advisory_id == advisory_id)
        )

    @staticmethod
    def _evidence_read(item: Evidence) -> EvidenceLinkRead:
        return EvidenceLinkRead(
            id=item.id,
            citation=item.citation,
            excerpt=item.excerpt,
            source_id=item.source_id,
        )

    def _revision_read(self, item: AdvisoryRevision) -> RevisionRead:
        return RevisionRead(
            id=item.id,
            version=item.version,
            title=item.title,
            summary=item.summary,
            created_by=item.created_by,
            created_at=item.created_at,
            published_at=item.published_at,
            published_by=item.published_by,
            sections=[
                SectionRead(
                    section_type=section.section_type,
                    position=section.position,
                    intelligence_type=section.intelligence_type,
                    content=section.content,
                )
                for section in item.sections
            ],
            evidence=[self._evidence_read(value) for value in item.evidence],
            actors=[
                ActorLinkRead(id=value.id, canonical_name=value.canonical_name)
                for value in item.actors
            ],
            campaigns=[NamedLinkRead(id=value.id, name=value.name) for value in item.campaigns],
            techniques=[
                TechniqueLinkRead(id=value.id, name=value.name, external_id=value.external_id)
                for value in item.techniques
            ],
        )

    def _update_read(self, item: AdvisoryUpdate) -> UpdateRead:
        return UpdateRead(
            id=item.id,
            sequence=item.sequence,
            revision_version=item.revision.version,
            occurred_at=item.occurred_at,
            title=item.title,
            summary=item.summary,
            intelligence_type=item.intelligence_type,
            created_by=item.created_by,
            created_at=item.created_at,
            evidence=[self._evidence_read(value) for value in item.evidence],
        )
