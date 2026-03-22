from decimal import Decimal
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import EntityType, ReconciliationStatus


class ReconciliationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Reconciliation result comparing gateway data with external provider data.

    Field meanings:
    - id: internal UUID primary key.
    - entity_type/entity_id: payment or refund being reconciled.
    - internal_status/external_status: compared status values.
    - internal_amount/external_amount: compared amounts.
    - match_result: reconciliation outcome.
    - mismatch_reason_*: why records do not match.
    - reviewed_by: internal user who reviewed the case.
    - review_note: manual review note.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "reconciliation_records"
    __table_args__ = (
        Index("ix_reconciliation_records_match_result", "match_result"),
    )

    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    internal_status: Mapped[str] = mapped_column(String(64), nullable=False)
    external_status: Mapped[str] = mapped_column(String(64), nullable=False)
    internal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    external_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    match_result: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status"),
        nullable=False,
    )
    mismatch_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mismatch_reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("internal_users.id"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
