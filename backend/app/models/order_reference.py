from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrderReference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Business-level mapping between a merchant order and gateway payment attempts.

    Field meanings:
    - id: internal UUID primary key.
    - merchant_db_id: owning merchant internal UUID.
    - order_id: merchant-provided order identifier.
    - order_status_snapshot: optional cached merchant order status at reference time.
    - latest_payment_transaction_id: latest payment attempt for this order.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "order_references"
    __table_args__ = (
        UniqueConstraint("merchant_db_id", "order_id", name="uq_order_references_merchant_order"),
    )

    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    order_status_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_payment_transaction_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "payment_transactions.id",
            use_alter=True,
            name="fk_order_references_latest_payment_transaction_id",
        ),
        nullable=True,
    )
