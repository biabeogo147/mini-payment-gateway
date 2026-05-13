from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import ActorType, InternalUserRole
from app.models.internal_user import InternalUser
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.ops import OpsActorContext
from app.services.auth_service import authenticate_merchant_request
from app.services import internal_auth_service


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_authenticated_merchant(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedMerchant:
    body = await request.body()
    return authenticate_merchant_request(
        db=db,
        method=request.method,
        path=request.url.path,
        body=body,
        headers=request.headers,
    )


def get_current_internal_user(
    request: Request,
    db: Session = Depends(get_db),
) -> InternalUser:
    session_token = request.cookies.get(get_settings().internal_auth_cookie_name)
    return internal_auth_service.authenticate_session(db=db, session_token=session_token)


def require_ops_user(
    current_user: InternalUser = Depends(get_current_internal_user),
) -> InternalUser:
    if current_user.role not in {InternalUserRole.ADMIN, InternalUserRole.OPS}:
        raise AppError(
            error_code="INTERNAL_AUTH_FORBIDDEN",
            message="Internal user is not allowed to access this route.",
            status_code=403,
        )
    return current_user


def require_admin_user(
    current_user: InternalUser = Depends(get_current_internal_user),
) -> InternalUser:
    if current_user.role != InternalUserRole.ADMIN:
        raise AppError(
            error_code="INTERNAL_AUTH_FORBIDDEN",
            message="Admin access is required for this route.",
            status_code=403,
        )
    return current_user


def build_ops_actor(
    current_user: InternalUser,
    legacy_actor: OpsActorContext | None = None,
) -> OpsActorContext:
    actor_type = ActorType.ADMIN if current_user.role == InternalUserRole.ADMIN else ActorType.OPS
    return OpsActorContext(
        actor_type=actor_type,
        actor_id=current_user.id,
        reason=legacy_actor.reason if legacy_actor is not None else None,
    )
