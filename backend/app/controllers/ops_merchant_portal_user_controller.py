from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db, require_ops_user
from app.models.internal_user import InternalUser
from app.schemas.merchant_portal import (
    CreateMerchantPortalUserRequest,
    MerchantPortalGeneratedPasswordResponse,
    MerchantPortalUserListResponse,
    MerchantPortalUserResponse,
    UpdateMerchantPortalUserRequest,
)
from app.services import merchant_portal_user_ops_service

router = APIRouter(prefix="/v1/ops/merchants/{merchant_id}/portal-users", tags=["merchant-portal-users"])


@router.get("", response_model=MerchantPortalUserListResponse)
def list_merchant_portal_users(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantPortalUserListResponse:
    return merchant_portal_user_ops_service.list_users(db=db, merchant_id=merchant_id)


@router.post("", response_model=MerchantPortalGeneratedPasswordResponse)
def create_merchant_portal_user(
    merchant_id: str,
    request: CreateMerchantPortalUserRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantPortalGeneratedPasswordResponse:
    return merchant_portal_user_ops_service.create_user(
        db=db,
        current_user=current_user,
        merchant_id=merchant_id,
        request=request,
    )


@router.patch("/{user_id}", response_model=MerchantPortalUserResponse)
def update_merchant_portal_user(
    merchant_id: str,
    user_id: str,
    request: UpdateMerchantPortalUserRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantPortalUserResponse:
    return merchant_portal_user_ops_service.update_user(
        db=db,
        current_user=current_user,
        merchant_id=merchant_id,
        user_id=user_id,
        full_name=request.full_name,
        role=request.role,
        status=request.status,
    )


@router.post("/{user_id}/reset-password", response_model=MerchantPortalGeneratedPasswordResponse)
def reset_merchant_portal_user_password(
    merchant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantPortalGeneratedPasswordResponse:
    return merchant_portal_user_ops_service.reset_password(
        db=db,
        current_user=current_user,
        merchant_id=merchant_id,
        user_id=user_id,
    )
