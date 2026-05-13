from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db, require_admin_user
from app.models.internal_user import InternalUser
from app.schemas.internal_auth import (
    CreateInternalUserRequest,
    InternalUserListResponse,
    InternalUserResponse,
    ResetInternalUserPasswordRequest,
    UpdateInternalUserRequest,
)
from app.services import internal_user_admin_service

router = APIRouter(prefix="/v1/internal/users", tags=["internal-users"])


@router.get("", response_model=InternalUserListResponse)
def list_internal_users(
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> InternalUserListResponse:
    return internal_user_admin_service.list_users(db)


@router.post("", response_model=InternalUserResponse)
def create_internal_user(
    request: CreateInternalUserRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> InternalUserResponse:
    return internal_user_admin_service.create_user(
        db=db,
        current_user=current_user,
        request=request,
    )


@router.patch("/{user_id}", response_model=InternalUserResponse)
def update_internal_user(
    user_id: str,
    request: UpdateInternalUserRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> InternalUserResponse:
    return internal_user_admin_service.update_user(
        db=db,
        current_user=current_user,
        user_id=user_id,
        request=request,
    )


@router.post("/{user_id}/reset-password", response_model=InternalUserResponse)
def reset_internal_user_password(
    user_id: str,
    request: ResetInternalUserPasswordRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> InternalUserResponse:
    return internal_user_admin_service.reset_password(
        db=db,
        current_user=current_user,
        user_id=user_id,
        request=request,
    )
