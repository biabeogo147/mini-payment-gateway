from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import RefundStatus


class RefundTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Refund flow record linked to a successful payment transaction.

    Field meanings:
    - id: internal UUID primary key.
    - refund_transaction_id: public refund transaction identifier.
    - merchant_db_id: owning merchant internal UUID.
    - payment_transaction_id: original payment being refunded.
    - refund_id: merchant-provided refund business id.
    - refund_amount: requested refund amount.
    - reason: merchant reason for refund.
    - status: refund lifecycle state.
    - external_reference: provider-side refund reference.
    - idempotency_key: technical idempotency key from caller.
    - processed_at: when final processing result was recorded.
    - failed_reason_*: refund failure diagnostics.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "refund_transactions"
    __table_args__ = (
        UniqueConstraint("merchant_db_id", "refund_id", name="uq_refund_transactions_merchant_refund"),
    )

    refund_transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", name="fk_refunds_merchant"),
        nullable=False,
    )
    payment_transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payment_transactions.id", name="fk_refunds_payment"),
        nullable=False,
    )
    refund_id: Mapped[str] = mapped_column(String(128), nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, name="refund_status"),
        nullable=False,
        default=RefundStatus.REFUND_PENDING,
        server_default=RefundStatus.REFUND_PENDING.value,
    )
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failed_reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
