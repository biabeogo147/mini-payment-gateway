from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import build_ops_actor, get_db, require_admin_user, require_ops_user
from app.models.internal_user import InternalUser
from app.schemas.ops import (
    CreateCredentialRequest,
    CreateMerchantRequest,
    CredentialOpsResponse,
    MerchantOpsResponse,
    OnboardingCaseResponse,
    OpsReasonRequest,
    ReviewOnboardingCaseRequest,
    RotateCredentialRequest,
    SubmitOnboardingCaseRequest,
)
from app.services import merchant_ops_service

router = APIRouter(prefix="/v1/ops/merchants", tags=["ops-merchants"])


@router.post("", response_model=MerchantOpsResponse)
def create_merchant(
    request: CreateMerchantRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantOpsResponse:
    return merchant_ops_service.create_merchant(
        db=db,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.put("/{merchant_id}/onboarding-case", response_model=OnboardingCaseResponse)
def submit_onboarding_case(
    merchant_id: str,
    request: SubmitOnboardingCaseRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> OnboardingCaseResponse:
    return merchant_ops_service.submit_onboarding_case(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/onboarding-case/approve", response_model=OnboardingCaseResponse)
def approve_onboarding_case(
    merchant_id: str,
    request: ReviewOnboardingCaseRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> OnboardingCaseResponse:
    return merchant_ops_service.approve_onboarding_case(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/onboarding-case/reject", response_model=OnboardingCaseResponse)
def reject_onboarding_case(
    merchant_id: str,
    request: ReviewOnboardingCaseRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> OnboardingCaseResponse:
    return merchant_ops_service.reject_onboarding_case(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/credentials", response_model=CredentialOpsResponse)
def create_credential(
    merchant_id: str,
    request: CreateCredentialRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> CredentialOpsResponse:
    return merchant_ops_service.create_credential(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/credentials/rotate", response_model=CredentialOpsResponse)
def rotate_credential(
    merchant_id: str,
    request: RotateCredentialRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> CredentialOpsResponse:
    return merchant_ops_service.rotate_credential(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/activate", response_model=MerchantOpsResponse)
def activate_merchant(
    merchant_id: str,
    request: OpsReasonRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantOpsResponse:
    return merchant_ops_service.activate_merchant(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/suspend", response_model=MerchantOpsResponse)
def suspend_merchant(
    merchant_id: str,
    request: OpsReasonRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantOpsResponse:
    return merchant_ops_service.suspend_merchant(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )


@router.post("/{merchant_id}/disable", response_model=MerchantOpsResponse)
def disable_merchant(
    merchant_id: str,
    request: OpsReasonRequest,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_admin_user),
) -> MerchantOpsResponse:
    return merchant_ops_service.disable_merchant(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=build_ops_actor(current_user, request.actor),
    )
