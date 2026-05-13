from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InternalUserRole, InternalUserStatus
from app.models.internal_user import InternalUser


def _serialize_datetime(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class InternalSchemaBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={
            datetime: _serialize_datetime,
            Decimal: lambda value: str(value),
        },
    )


class InternalUserResponse(InternalSchemaBase):
    user_id: str
    email: str
    full_name: str
    role: InternalUserRole
    status: InternalUserStatus
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: InternalUser) -> "InternalUserResponse":
        return cls(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class InternalAuthBootstrapStatusResponse(InternalSchemaBase):
    bootstrap_required: bool


class InternalAuthBootstrapRequest(InternalSchemaBase):
    email: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class InternalAuthLoginRequest(InternalSchemaBase):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class InternalAuthChangePasswordRequest(InternalSchemaBase):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class InternalAuthSessionResponse(InternalSchemaBase):
    user: InternalUserResponse


class InternalAuthStatusResponse(InternalSchemaBase):
    status: str


class CreateInternalUserRequest(InternalSchemaBase):
    email: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: InternalUserRole
    password: str = Field(min_length=8, max_length=255)
    status: InternalUserStatus = InternalUserStatus.ACTIVE


class UpdateInternalUserRequest(InternalSchemaBase):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: InternalUserRole | None = None
    status: InternalUserStatus | None = None


class ResetInternalUserPasswordRequest(InternalSchemaBase):
    new_password: str = Field(min_length=8, max_length=255)


class InternalUserListResponse(InternalSchemaBase):
    users: list[InternalUserResponse]
