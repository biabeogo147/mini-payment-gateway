from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import PaymentStatus


class PaymentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Core payment transaction row representing one QR payment attempt.
    """

    __tablename__ = "payment_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_transactions_amount_positive"),
        Index(
            "ux_payment_transactions_active_order",
            "merchant_db_id",
            "order_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("ix_payment_transactions_merchant_order", "merchant_db_id", "order_id"),
    )

    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    order_reference_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("order_references.id", name="fk_payments_order_ref"),
        nullable=False,
    )
    order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VND", server_default="VND")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )
    qr_content: Mapped[str] = mapped_column(Text, nullable=False)
    qr_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failed_reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
