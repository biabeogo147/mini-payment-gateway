from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_merchant_user, get_db
from app.core.config import get_settings
from app.models.merchant_user import MerchantUser
from app.schemas.merchant_portal import (
    MerchantPortalAuthChangePasswordRequest,
    MerchantPortalAuthLoginRequest,
    MerchantPortalAuthSessionResponse,
    MerchantPortalStatusResponse,
)
from app.services import merchant_portal_auth_service

router = APIRouter(prefix="/v1/merchant-portal/auth", tags=["merchant-portal-auth"])


@router.post("/login", response_model=MerchantPortalAuthSessionResponse)
def login_merchant_user(
    request: MerchantPortalAuthLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> MerchantPortalAuthSessionResponse:
    user, session_token = merchant_portal_auth_service.login(db=db, request=request)
    _set_session_cookie(response, session_token)
    return MerchantPortalAuthSessionResponse.from_user(user)


@router.post("/logout", response_model=MerchantPortalStatusResponse)
def logout_merchant_user(response: Response) -> MerchantPortalStatusResponse:
    settings = get_settings()
    response.delete_cookie(settings.merchant_auth_cookie_name, path="/")
    return MerchantPortalStatusResponse(status="ok")


@router.get("/me", response_model=MerchantPortalAuthSessionResponse)
def get_current_session_user(
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalAuthSessionResponse:
    return MerchantPortalAuthSessionResponse.from_user(current_user)


@router.post("/change-password", response_model=MerchantPortalAuthSessionResponse)
def change_merchant_user_password(
    request: MerchantPortalAuthChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalAuthSessionResponse:
    user, session_token = merchant_portal_auth_service.change_password(
        db=db,
        current_user=current_user,
        request=request,
    )
    _set_session_cookie(response, session_token)
    return MerchantPortalAuthSessionResponse.from_user(user)


def _set_session_cookie(response: Response, session_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.merchant_auth_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.merchant_auth_cookie_secure,
        samesite="lax",
        max_age=settings.merchant_auth_ttl_seconds,
        path="/",
    )
