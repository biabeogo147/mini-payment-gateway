from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.internal_auth import hash_password
from app.core.time import utc_now
from app.models.enums import ActorType, EntityType, InternalUserRole, InternalUserStatus
from app.models.internal_user import InternalUser
from app.repositories import internal_user_repository
from app.schemas.internal_auth import (
    CreateInternalUserRequest,
    InternalUserListResponse,
    InternalUserResponse,
    ResetInternalUserPasswordRequest,
    UpdateInternalUserRequest,
)
from app.services import audit_service


def list_users(db: Session) -> InternalUserListResponse:
    return InternalUserListResponse(
        users=[InternalUserResponse.from_user(user) for user in internal_user_repository.list_users(db)]
    )


def create_user(
    db: Session,
    *,
    current_user: InternalUser,
    request: CreateInternalUserRequest,
) -> InternalUserResponse:
    if internal_user_repository.get_by_email(db, request.email) is not None:
        raise AppError(
            error_code="INTERNAL_USER_ALREADY_EXISTS",
            message="Internal user already exists.",
            status_code=409,
            details={"email": request.email},
        )

    user = internal_user_repository.create(
        db=db,
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        status=request.status,
        password_hash=hash_password(request.password),
    )
    audit_service.record_event(
        db=db,
        event_type="INTERNAL_USER_CREATED",
        entity_type=EntityType.INTERNAL_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=None,
        after_state=_internal_user_state(user),
        reason=f"Created internal user {user.email}.",
    )
    db.commit()
    return InternalUserResponse.from_user(user)


def update_user(
    db: Session,
    *,
    current_user: InternalUser,
    user_id: str,
    request: UpdateInternalUserRequest,
) -> InternalUserResponse:
    user = _require_user(db, user_id)
    target_role = request.role or user.role
    target_status = request.status or user.status
    _assert_admin_retention(db, user, target_role, target_status)

    before_state = _internal_user_state(user)
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.role is not None:
        user.role = request.role
    if request.status is not None:
        user.status = request.status
    internal_user_repository.save(db, user)
    audit_service.record_event(
        db=db,
        event_type="INTERNAL_USER_UPDATED",
        entity_type=EntityType.INTERNAL_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_internal_user_state(user),
        reason=f"Updated internal user {user.email}.",
    )
    db.commit()
    return InternalUserResponse.from_user(user)


def reset_password(
    db: Session,
    *,
    current_user: InternalUser,
    user_id: str,
    request: ResetInternalUserPasswordRequest,
    now: datetime | None = None,
) -> InternalUserResponse:
    user = _require_user(db, user_id)
    reset_at = now or utc_now()
    before_state = _internal_user_state(user)
    user.password_hash = hash_password(request.new_password)
    user.last_login_at = reset_at if user.id == current_user.id else user.last_login_at
    internal_user_repository.save(db, user)
    audit_service.record_event(
        db=db,
        event_type="INTERNAL_USER_PASSWORD_RESET",
        entity_type=EntityType.INTERNAL_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_internal_user_state(user),
        reason=f"Reset password for internal user {user.email}.",
    )
    db.commit()
    return InternalUserResponse.from_user(user)


def _require_user(db: Session, user_id: str) -> InternalUser:
    user = internal_user_repository.get_by_id(db, user_id)
    if user is None:
        raise AppError(
            error_code="INTERNAL_USER_NOT_FOUND",
            message="Internal user not found.",
            status_code=404,
            details={"user_id": user_id},
        )
    return user


def _assert_admin_retention(
    db: Session,
    user: InternalUser,
    target_role: InternalUserRole,
    target_status: InternalUserStatus,
) -> None:
    if (
        user.role == InternalUserRole.ADMIN
        and user.status == InternalUserStatus.ACTIVE
        and user.password_hash is not None
        and (target_role != InternalUserRole.ADMIN or target_status != InternalUserStatus.ACTIVE)
        and internal_user_repository.count_active_admins(db) <= 1
    ):
        raise AppError(
            error_code="LAST_ACTIVE_ADMIN_REQUIRED",
            message="At least one active admin must remain.",
            status_code=409,
        )


def _actor_type(user: InternalUser):
    if user.role == InternalUserRole.ADMIN:
        return ActorType.ADMIN
    return ActorType.OPS


def _internal_user_state(user: InternalUser) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
