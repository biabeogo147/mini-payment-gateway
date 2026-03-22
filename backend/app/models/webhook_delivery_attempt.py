from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPrimaryKeyMixin
from .enums import DeliveryAttemptResult


class WebhookDeliveryAttempt(UUIDPrimaryKeyMixin, Base):
    """
    What this model means:
    One HTTP delivery attempt for a webhook event.

    Field meanings:
    - id: internal UUID primary key.
    - webhook_event_id: parent webhook event internal UUID.
    - attempt_no: delivery attempt sequence number.
    - request_url: target URL used for this attempt.
    - request_headers_json/request_body_json: exact outbound payload snapshot.
    - response_status_code/response_body_snippet: response diagnostics.
    - error_message: network or client error detail.
    - started_at/finished_at: attempt timing.
    - result: final outcome of this attempt.
    """

    __tablename__ = "webhook_delivery_attempts"

    webhook_event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("webhook_events.id", name="fk_webhook_attempts_event"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    request_headers_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    request_body_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[DeliveryAttemptResult] = mapped_column(
        Enum(DeliveryAttemptResult, name="delivery_attempt_result"),
        nullable=False,
    )
