from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, JSON, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPrimaryKeyMixin
from .enums import ActorType, EntityType


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """
    What this model means:
    Immutable operator/system audit trail for manual or administrative actions.

    Field meanings:
    - id: internal UUID primary key.
    - event_type: audit event code.
    - entity_type/entity_id: affected entity.
    - actor_type: who performed the action.
    - actor_id: internal user UUID when action is human-triggered.
    - before_state_json/after_state_json: state snapshots around the change.
    - reason: optional operator note or reason.
    - created_at: when the audit record was written.
    """

    __tablename__ = "audit_logs"

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type"),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("internal_users.id"),
        nullable=True,
    )
    before_state_json: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    after_state_json: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
