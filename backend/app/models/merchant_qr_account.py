from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import MerchantQrAccountStatus, QrProvider


class MerchantQrAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Merchant receiving account used to generate provider-specific payment QR codes.
    """

    __tablename__ = "merchant_qr_accounts"
    __table_args__ = (
        Index(
            "ux_merchant_qr_accounts_active_provider_per_merchant",
            "merchant_db_id",
            "provider",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_merchant_qr_accounts_merchant_db_id", "merchant_db_id"),
    )

    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    provider: Mapped[QrProvider] = mapped_column(
        Enum(QrProvider, name="qr_provider"),
        nullable=False,
        default=QrProvider.VIETQR,
        server_default=QrProvider.VIETQR.value,
    )
    bank_code: Mapped[str] = mapped_column(String(32), nullable=False)
    bank_bin: Mapped[str] = mapped_column(String(16), nullable=False)
    account_number: Mapped[str] = mapped_column(String(64), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template: Mapped[str] = mapped_column(String(32), nullable=False, default="compact", server_default="compact")
    status: Mapped[MerchantQrAccountStatus] = mapped_column(
        Enum(MerchantQrAccountStatus, name="merchant_qr_account_status"),
        nullable=False,
        default=MerchantQrAccountStatus.ACTIVE,
        server_default=MerchantQrAccountStatus.ACTIVE.value,
    )
