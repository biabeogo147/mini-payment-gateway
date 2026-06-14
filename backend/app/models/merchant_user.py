from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import MerchantUserRole, MerchantUserStatus


class MerchantUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Merchant-facing dashboard user scoped to exactly one merchant.
    """

    __tablename__ = "merchant_users"
    __table_args__ = (
        UniqueConstraint("merchant_db_id", "email", name="uq_merchant_users_merchant_email"),
        Index("ix_merchant_users_merchant_db_id", "merchant_db_id"),
        Index("ix_merchant_users_email", "email"),
    )

    merchant_db_id: Mapped[UUID] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[MerchantUserRole] = mapped_column(
        Enum(MerchantUserRole, name="merchant_user_role"),
        nullable=False,
    )
    status: Mapped[MerchantUserStatus] = mapped_column(
        Enum(MerchantUserStatus, name="merchant_user_status"),
        nullable=False,
        default=MerchantUserStatus.ACTIVE,
        server_default=MerchantUserStatus.ACTIVE.value,
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merchant = relationship("Merchant")
