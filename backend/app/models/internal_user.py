from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import InternalUserRole, InternalUserStatus


class InternalUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Internal operator account used by admin/ops flows.

    Field meanings:
    - id: internal UUID primary key.
    - email: unique login/contact email of the internal user.
    - full_name: display name for audit and approval actions.
    - role: operator role such as ADMIN or OPS.
    - status: whether this internal account is active for use.
    - password_hash: local internal-auth password hash.
    - last_login_at: latest successful internal-auth login timestamp.
    - created_at: when the account record was created.
    - updated_at: latest update timestamp.
    """

    __tablename__ = "internal_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[InternalUserRole] = mapped_column(
        Enum(InternalUserRole, name="internal_user_role"),
        nullable=False,
    )
    status: Mapped[InternalUserStatus] = mapped_column(
        Enum(InternalUserStatus, name="internal_user_status"),
        nullable=False,
        default=InternalUserStatus.ACTIVE,
    )
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
