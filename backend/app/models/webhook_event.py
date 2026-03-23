from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import EntityType, WebhookEventStatus


class WebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Snapshot of a business event queued for delivery to a merchant webhook.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_webhook_events_attempt_count_non_negative"),
        Index("ix_webhook_events_merchant_status_retry", "merchant_db_id", "status", "next_retry_at"),
    )

    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", name="fk_webhook_events_merchant"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WebhookEventStatus] = mapped_column(
        Enum(WebhookEventStatus, name="webhook_event_status"),
        nullable=False,
        default=WebhookEventStatus.PENDING,
        server_default=WebhookEventStatus.PENDING.value,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
