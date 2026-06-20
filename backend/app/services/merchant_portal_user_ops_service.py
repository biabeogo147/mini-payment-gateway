import secrets
import string

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.internal_auth import hash_password
from app.models.enums import ActorType, EntityType, InternalUserRole
from app.models.internal_user import InternalUser
from app.repositories import merchant_repository, merchant_user_repository
from app.schemas.merchant_portal import (
    CreateMerchantPortalUserRequest,
    MerchantPortalGeneratedPasswordResponse,
    MerchantPortalUserListResponse,
    MerchantPortalUserResponse,
)
from app.services import audit_service


def list_users(
    db: Session,
    *,
    merchant_id: str,
) -> MerchantPortalUserListResponse:
    merchant = _require_merchant(db, merchant_id)
    return MerchantPortalUserListResponse(
        users=[
            MerchantPortalUserResponse.from_user(user)
            for user in merchant_user_repository.list_by_merchant(db, merchant.id)
        ]
    )


def create_user(
    db: Session,
    *,
    current_user: InternalUser,
    merchant_id: str,
    request: CreateMerchantPortalUserRequest,
) -> MerchantPortalGeneratedPasswordResponse:
    _require_operator(current_user)
    merchant = _require_merchant(db, merchant_id)
    if merchant_user_repository.get_by_merchant_and_email(
        db,
        merchant_db_id=merchant.id,
        email=request.email,
    ) is not None:
        raise AppError(
            error_code="MERCHANT_PORTAL_USER_ALREADY_EXISTS",
            message="Merchant portal user already exists.",
            status_code=409,
            details={"merchant_id": merchant_id, "email": request.email},
        )

    generated_password = _generate_password()
    user = merchant_user_repository.create(
        db=db,
        merchant_db_id=merchant.id,
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        status=request.status,
        password_hash=hash_password(generated_password),
    )
    audit_service.record_event(
        db=db,
        event_type="MERCHANT_USER_CREATED",
        entity_type=EntityType.MERCHANT_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=None,
        after_state=_merchant_user_state(user),
        reason=f"Created merchant portal user {user.email}.",
    )
    db.commit()
    return MerchantPortalGeneratedPasswordResponse(
        user=MerchantPortalUserResponse.from_user(user),
        generated_password=generated_password,
    )


def update_user(
    db: Session,
    *,
    current_user: InternalUser,
    merchant_id: str,
    user_id: str,
    full_name=None,
    role=None,
    status=None,
) -> MerchantPortalUserResponse:
    _require_operator(current_user)
    merchant = _require_merchant(db, merchant_id)
    user = _require_user(db, merchant.id, user_id)
    before_state = _merchant_user_state(user)
    if full_name is not None:
        user.full_name = full_name
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
    user = merchant_user_repository.save(db, user)
    audit_service.record_event(
        db=db,
        event_type="MERCHANT_USER_UPDATED",
        entity_type=EntityType.MERCHANT_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_merchant_user_state(user),
        reason=f"Updated merchant portal user {user.email}.",
    )
    db.commit()
    return MerchantPortalUserResponse.from_user(user)


def reset_password(
    db: Session,
    *,
    current_user: InternalUser,
    merchant_id: str,
    user_id: str,
) -> MerchantPortalGeneratedPasswordResponse:
    _require_operator(current_user)
    merchant = _require_merchant(db, merchant_id)
    user = _require_user(db, merchant.id, user_id)
    before_state = _merchant_user_state(user)
    generated_password = _generate_password()
    user.password_hash = hash_password(generated_password)
    user = merchant_user_repository.save(db, user)
    audit_service.record_event(
        db=db,
        event_type="MERCHANT_USER_PASSWORD_RESET",
        entity_type=EntityType.MERCHANT_USER,
        entity_id=user.id,
        actor_type=_actor_type(current_user),
        actor_id=current_user.id,
        before_state=before_state,
        after_state=_merchant_user_state(user),
        reason=f"Reset password for merchant portal user {user.email}.",
    )
    db.commit()
    return MerchantPortalGeneratedPasswordResponse(
        user=MerchantPortalUserResponse.from_user(user),
        generated_password=generated_password,
    )


def _require_operator(current_user: InternalUser) -> None:
    if current_user.role not in {InternalUserRole.ADMIN, InternalUserRole.OPS}:
        raise AppError(
            error_code="INTERNAL_AUTH_FORBIDDEN",
            message="Internal operator access is required for this route.",
            status_code=403,
        )


def _actor_type(current_user: InternalUser) -> ActorType:
    if current_user.role == InternalUserRole.ADMIN:
        return ActorType.ADMIN
    return ActorType.OPS


def _require_merchant(db: Session, merchant_id: str):
    merchant = merchant_repository.get_by_public_merchant_id(db, merchant_id)
    if merchant is None:
        raise AppError(
            error_code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    return merchant


def _require_user(db: Session, merchant_db_id, user_id: str):
    user = merchant_user_repository.get_by_merchant_and_id(
        db,
        merchant_db_id=merchant_db_id,
        user_id=user_id,
    )
    if user is None:
        raise AppError(
            error_code="MERCHANT_PORTAL_USER_NOT_FOUND",
            message="Merchant portal user not found.",
            status_code=404,
            details={"user_id": user_id},
        )
    return user


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))


def _merchant_user_state(user) -> dict:
    return {
        "id": str(user.id),
        "merchant_db_id": str(user.merchant_db_id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
