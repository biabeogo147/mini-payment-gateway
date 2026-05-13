from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_internal_user, get_db
from app.core.config import get_settings
from app.models.internal_user import InternalUser
from app.schemas.internal_auth import (
    InternalAuthBootstrapRequest,
    InternalAuthBootstrapStatusResponse,
    InternalAuthChangePasswordRequest,
    InternalAuthLoginRequest,
    InternalAuthSessionResponse,
    InternalAuthStatusResponse,
    InternalUserResponse,
)
from app.services import internal_auth_service

router = APIRouter(prefix="/v1/internal/auth", tags=["internal-auth"])


@router.get("/bootstrap-status", response_model=InternalAuthBootstrapStatusResponse)
def get_bootstrap_status(
    db: Session = Depends(get_db),
) -> InternalAuthBootstrapStatusResponse:
    return InternalAuthBootstrapStatusResponse(
        bootstrap_required=internal_auth_service.bootstrap_required(db)
    )


@router.post("/bootstrap", response_model=InternalAuthSessionResponse)
def bootstrap_first_admin(
    request: InternalAuthBootstrapRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> InternalAuthSessionResponse:
    user, session_token = internal_auth_service.bootstrap_first_admin(db=db, request=request)
    _set_session_cookie(response, session_token)
    return InternalAuthSessionResponse(user=InternalUserResponse.from_user(user))


@router.post("/login", response_model=InternalAuthSessionResponse)
def login_internal_user(
    request: InternalAuthLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> InternalAuthSessionResponse:
    user, session_token = internal_auth_service.login(db=db, request=request)
    _set_session_cookie(response, session_token)
    return InternalAuthSessionResponse(user=InternalUserResponse.from_user(user))


@router.post("/logout", response_model=InternalAuthStatusResponse)
def logout_internal_user(
    response: Response,
) -> InternalAuthStatusResponse:
    settings = get_settings()
    response.delete_cookie(settings.internal_auth_cookie_name, path="/")
    return InternalAuthStatusResponse(status="ok")


@router.get("/me", response_model=InternalAuthSessionResponse)
def get_current_session_user(
    current_user: InternalUser = Depends(get_current_internal_user),
) -> InternalAuthSessionResponse:
    return InternalAuthSessionResponse(user=InternalUserResponse.from_user(current_user))


@router.post("/change-password", response_model=InternalAuthSessionResponse)
def change_internal_user_password(
    request: InternalAuthChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(get_current_internal_user),
) -> InternalAuthSessionResponse:
    user, session_token = internal_auth_service.change_password(
        db=db,
        current_user=current_user,
        request=request,
    )
    _set_session_cookie(response, session_token)
    return InternalAuthSessionResponse(user=InternalUserResponse.from_user(user))


def _set_session_cookie(response: Response, session_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.internal_auth_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.internal_auth_cookie_secure,
        samesite="lax",
        max_age=settings.internal_auth_ttl_seconds,
        path="/",
    )
