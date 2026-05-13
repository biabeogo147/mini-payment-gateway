from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.internal_auth import (
    build_internal_session_token,
    hash_password,
    internal_session_version,
    parse_internal_session_token,
    verify_password,
)
from app.core.time import utc_now
from app.models.enums import ActorType, EntityType, InternalUserRole, InternalUserStatus
from app.models.internal_user import InternalUser
from app.repositories import internal_user_repository
from app.schemas.internal_auth import (
    InternalAuthBootstrapRequest,
    InternalAuthChangePasswordRequest,
    InternalAuthLoginRequest,
)
from app.services import audit_service


def bootstrap_required(db: Session) -> bool:
    return internal_user_repository.count_password_enabled_users(db) == 0


def bootstrap_first_admin(
    db: Session,
    request: InternalAuthBootstrapRequest,
    now: datetime | None = None,
) -> tuple[InternalUser, str]:
    if not bootstrap_required(db):
        raise AppError(
            error_code="INTERNAL_AUTH_BOOTSTRAP_DISABLED",
            message="Internal auth bootstrap is no longer available.",
            status_code=409,
        )

    if internal_user_repository.get_by_email(db, request.email) is not None:
        raise AppError(
            error_code="INTERNAL_USER_ALREADY_EXISTS",
            message="Internal user already exists.",
            status_code=409,
            details={"email": request.email},
        )

    issued_at = now or utc_now()
    user = internal_user_repository.create(
        db=db,
        email=request.email,
        full_name=request.full_name,
        role=InternalUserRole.ADMIN,
        status=InternalUserStatus.ACTIVE,
        password_hash=hash_password(request.password),
    )
    user.last_login_at = issued_at
    internal_user_repository.save(db, user)
    audit_service.record_event(
        db=db,
        event_type="INTERNAL_USER_BOOTSTRAPPED",
        entity_type=EntityType.INTERNAL_USER,
        entity_id=user.id,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        before_state=None,
        after_state=_internal_user_state(user),
        reason="Bootstrap first internal admin.",
    )
    db.commit()
    return user, _issue_session_token(user, issued_at)


def login(
    db: Session,
    request: InternalAuthLoginRequest,
    now: datetime | None = None,
) -> tuple[InternalUser, str]:
    user = internal_user_repository.get_by_email(db, request.email)
    _require_valid_login_target(user, request.password)

    login_at = now or utc_now()
    user.last_login_at = login_at
    internal_user_repository.save(db, user)
    db.commit()
    return user, _issue_session_token(user, login_at)


def authenticate_session(
    db: Session,
    session_token: str | None,
    now: datetime | None = None,
) -> InternalUser:
    if not session_token:
        raise AppError(
            error_code="INTERNAL_AUTH_REQUIRED",
            message="Internal authentication is required.",
            status_code=401,
        )
    try:
        claims = parse_internal_session_token(
            session_token,
            secret=get_settings().internal_auth_secret,
            now=now or utc_now(),
        )
    except ValueError as exc:
        raise AppError(
            error_code="INTERNAL_AUTH_INVALID_SESSION",
            message="Internal authentication failed.",
            status_code=401,
        ) from exc

    user = internal_user_repository.get_by_id(db, claims.user_id)
    if user is None or user.password_hash is None:
        raise AppError(
            error_code="INTERNAL_AUTH_INVALID_SESSION",
            message="Internal authentication failed.",
            status_code=401,
        )
    if user.status != InternalUserStatus.ACTIVE:
        raise AppError(
            error_code="INTERNAL_AUTH_INACTIVE",
            message="Internal user is inactive.",
            status_code=403,
        )
    if internal_session_version(user) != claims.version:
        raise AppError(
            error_code="INTERNAL_AUTH_INVALID_SESSION",
            message="Internal authentication failed.",
            status_code=401,
        )
    return user


def change_password(
    db: Session,
    current_user: InternalUser,
    request: InternalAuthChangePasswordRequest,
    now: datetime | None = None,
) -> tuple[InternalUser, str]:
    if not verify_password(request.current_password, current_user.password_hash):
        raise AppError(
            error_code="INTERNAL_AUTH_INVALID_CREDENTIALS",
            message="Current password is invalid.",
            status_code=401,
        )

    changed_at = now or utc_now()
    before_state = _internal_user_state(current_user)
    current_user.password_hash = hash_password(request.new_password)
    current_user.last_login_at = changed_at
    internal_user_repository.save(db, current_user)
    audit_service.record_event(
        db=db,
        event_type="INTERNAL_USER_PASSWORD_CHANGED",
        entity_type=EntityType.INTERNAL_USER,
        entity_id=current_user.id,
        actor_type=_actor_type_for_user(current_user),
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_internal_user_state(current_user),
        reason="Internal user changed own password.",
    )
    db.commit()
    return current_user, _issue_session_token(current_user, changed_at)


def _require_valid_login_target(user: InternalUser | None, password: str) -> None:
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(
            error_code="INTERNAL_AUTH_INVALID_CREDENTIALS",
            message="Internal authentication failed.",
            status_code=401,
        )
    if user.status != InternalUserStatus.ACTIVE:
        raise AppError(
            error_code="INTERNAL_AUTH_INACTIVE",
            message="Internal user is inactive.",
            status_code=403,
        )


def _issue_session_token(user: InternalUser, issued_at: datetime) -> str:
    settings = get_settings()
    return build_internal_session_token(
        user_id=user.id,
        version=internal_session_version(user),
        secret=settings.internal_auth_secret,
        now=issued_at,
        ttl_seconds=settings.internal_auth_ttl_seconds,
    )


def _internal_user_state(user: InternalUser) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def _actor_type_for_user(user: InternalUser) -> ActorType:
    if user.role == InternalUserRole.ADMIN:
        return ActorType.ADMIN
    return ActorType.OPS
