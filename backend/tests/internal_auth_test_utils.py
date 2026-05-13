from datetime import datetime, timezone
from uuid import uuid4

from app.models.enums import InternalUserRole, InternalUserStatus
from app.models.internal_user import InternalUser


def make_internal_user(
    *,
    role: InternalUserRole = InternalUserRole.OPS,
    status: InternalUserStatus = InternalUserStatus.ACTIVE,
    email: str | None = None,
) -> InternalUser:
    now = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
    return InternalUser(
        id=uuid4(),
        email=email or f"{role.value.lower()}-{uuid4().hex[:8]}@example.com",
        full_name=f"{role.value.title()} User",
        role=role,
        status=status,
        password_hash="pbkdf2_sha256$240000$testsalt$testdigest",
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )


def override_current_internal_user(app, user: InternalUser) -> None:
    from app.controllers.deps import get_current_internal_user

    def current_user_override() -> InternalUser:
        return user

    app.dependency_overrides[get_current_internal_user] = current_user_override
