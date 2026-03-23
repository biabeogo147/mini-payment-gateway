from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import CredentialStatus


class MerchantCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Merchant API credential record with rotation history.

    Field meanings:
    - id: internal UUID primary key.
    - merchant_db_id: owning merchant internal UUID.
    - access_key: public access key used together with merchant_id.
    - secret_key_encrypted: encrypted secret value stored at rest.
    - secret_key_last4: masked suffix shown for operator reference.
    - status: current credential state.
    - expired_at: when the credential stopped being valid.
    - rotated_at: when the credential was rotated.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "merchant_credentials"
    __table_args__ = (
        Index(
            "ux_merchant_credentials_active_per_merchant",
            "merchant_db_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    access_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    secret_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[CredentialStatus] = mapped_column(
        Enum(CredentialStatus, name="credential_status"),
        nullable=False,
        default=CredentialStatus.ACTIVE,
        server_default=CredentialStatus.ACTIVE.value,
    )
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
