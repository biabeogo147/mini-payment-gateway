from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import MerchantStatus


class Merchant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Merchant master profile and integration configuration.

    Field meanings:
    - id: internal UUID primary key.
    - merchant_id: public merchant identifier exposed to APIs.
    - merchant_name: merchant display name.
    - legal_name: registered business/legal name.
    - contact_name/contact_email/contact_phone: merchant contact details.
    - webhook_url: merchant endpoint receiving payment/refund events.
    - allowed_ip_list: optional whitelist of allowed caller IPs.
    - status: merchant lifecycle status.
    - settlement_account_*: payout account metadata.
    - approved_at: when merchant was approved.
    - approved_by: internal user who approved the merchant.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_ip_list: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    status: Mapped[MerchantStatus] = mapped_column(
        Enum(MerchantStatus, name="merchant_status"),
        nullable=False,
        default=MerchantStatus.PENDING,
    )
    settlement_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settlement_account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    settlement_bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("internal_users.id"),
        nullable=True,
    )
