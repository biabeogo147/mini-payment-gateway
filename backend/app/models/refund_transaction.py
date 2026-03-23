from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import RefundStatus


class RefundTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Refund flow record linked to a successful payment transaction.
    """

    __tablename__ = "refund_transactions"
    __table_args__ = (
        UniqueConstraint("merchant_db_id", "refund_id", name="uq_refund_transactions_merchant_refund"),
        CheckConstraint("refund_amount > 0", name="ck_refund_transactions_refund_amount_positive"),
        Index(
            "ux_refund_transactions_refunded_payment",
            "payment_transaction_id",
            unique=True,
            postgresql_where=text("status = 'REFUNDED'"),
        ),
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
