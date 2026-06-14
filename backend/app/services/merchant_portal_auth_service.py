from datetime import datetime
import hashlib

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.internal_auth import (
    build_internal_session_token,
    hash_password,
    parse_internal_session_token,
    verify_password,
)
from app.core.time import utc_now
from app.models.enums import ActorType, EntityType, MerchantUserStatus
from app.models.merchant_user import MerchantUser
from app.repositories import merchant_repository, merchant_user_repository
from app.schemas.merchant_portal import (
    MerchantPortalAuthChangePasswordRequest,
    MerchantPortalAuthLoginRequest,
)
from app.services import audit_service


def login(
    db: Session,
    request: MerchantPortalAuthLoginRequest,
    now: datetime | None = None,
) -> tuple[MerchantUser, str]:
    merchant = merchant_repository.get_by_public_merchant_id(db, request.merchant_id)
    user = (
        merchant_user_repository.get_by_merchant_and_email(
            db,
            merchant_db_id=merchant.id,
            email=request.email,
        )
        if merchant is not None
        else None
    )
    _require_valid_login_target(user, request.password)

    login_at = now or utc_now()
    user.last_login_at = login_at
    merchant_user_repository.save(db, user)
    db.commit()
    return user, _issue_session_token(user, login_at)


def authenticate_session(
    db: Session,
    session_token: str | None,
    now: datetime | None = None,
) -> MerchantUser:
    if not session_token:
        raise AppError(
            error_code="MERCHANT_AUTH_REQUIRED",
            message="Merchant authentication is required.",
            status_code=401,
        )
    try:
        claims = parse_internal_session_token(
            session_token,
            secret=get_settings().merchant_auth_secret,
            now=now or utc_now(),
        )
    except ValueError as exc:
        raise AppError(
            error_code="MERCHANT_AUTH_INVALID_SESSION",
            message="Merchant authentication failed.",
            status_code=401,
        ) from exc

    user = merchant_user_repository.get_by_id(db, claims.user_id)
    if user is None:
        raise AppError(
            error_code="MERCHANT_AUTH_INVALID_SESSION",
            message="Merchant authentication failed.",
            status_code=401,
        )
    if user.status != MerchantUserStatus.ACTIVE:
        raise AppError(
            error_code="MERCHANT_AUTH_INACTIVE",
            message="Merchant user is inactive.",
            status_code=403,
        )
    if _merchant_session_version(user) != claims.version:
        raise AppError(
            error_code="MERCHANT_AUTH_INVALID_SESSION",
            message="Merchant authentication failed.",
            status_code=401,
        )
    return user


def change_password(
    db: Session,
    current_user: MerchantUser,
    request: MerchantPortalAuthChangePasswordRequest,
    now: datetime | None = None,
) -> tuple[MerchantUser, str]:
    if not verify_password(request.current_password, current_user.password_hash):
        raise AppError(
            error_code="MERCHANT_AUTH_INVALID_CREDENTIALS",
            message="Current password is invalid.",
            status_code=401,
        )

    changed_at = now or utc_now()
    before_state = _merchant_user_state(current_user)
    current_user.password_hash = hash_password(request.new_password)
    current_user.last_login_at = changed_at
    merchant_user_repository.save(db, current_user)
    audit_service.record_event(
        db=db,
        event_type="MERCHANT_USER_PASSWORD_CHANGED",
        entity_type=EntityType.MERCHANT_USER,
        entity_id=current_user.id,
        actor_type=ActorType.MERCHANT,
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_merchant_user_state(current_user),
        reason="Merchant user changed own password.",
    )
    db.commit()
    return current_user, _issue_session_token(current_user, changed_at)


def _require_valid_login_target(user: MerchantUser | None, password: str) -> None:
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(
            error_code="MERCHANT_AUTH_INVALID_CREDENTIALS",
            message="Merchant authentication failed.",
            status_code=401,
        )
    if user.status != MerchantUserStatus.ACTIVE:
        raise AppError(
            error_code="MERCHANT_AUTH_INACTIVE",
            message="Merchant user is inactive.",
            status_code=403,
        )


def _issue_session_token(user: MerchantUser, issued_at: datetime) -> str:
    settings = get_settings()
    return build_internal_session_token(
        user_id=user.id,
        version=_merchant_session_version(user),
        secret=settings.merchant_auth_secret,
        now=issued_at,
        ttl_seconds=settings.merchant_auth_ttl_seconds,
    )


def _merchant_session_version(user: MerchantUser) -> str:
    source = "|".join([user.password_hash, user.role.value, user.status.value])
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _merchant_user_state(user: MerchantUser) -> dict:
    return {
        "id": str(user.id),
        "merchant_db_id": str(user.merchant_db_id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
