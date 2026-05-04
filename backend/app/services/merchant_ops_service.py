from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import (
    CredentialStatus,
    EntityType,
    MerchantStatus,
    OnboardingCaseStatus,
)
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase
from app.repositories import credential_repository, merchant_repository, onboarding_repository
from app.schemas.ops import (
    CreateCredentialRequest,
    CreateMerchantRequest,
    CredentialOpsResponse,
    MerchantOpsResponse,
    OnboardingCaseResponse,
    OpsActorContext,
    OpsReasonRequest,
    ReviewOnboardingCaseRequest,
    RotateCredentialRequest,
    SubmitOnboardingCaseRequest,
)
from app.services import audit_service

FINAL_ONBOARDING_STATUSES = {
    OnboardingCaseStatus.APPROVED,
    OnboardingCaseStatus.REJECTED,
}


def create_merchant(
    db: Session,
    request: CreateMerchantRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> MerchantOpsResponse:
    existing = merchant_repository.get_by_public_merchant_id(db, request.merchant_id)
    if existing is not None:
        raise AppError(
            error_code="MERCHANT_ALREADY_EXISTS",
            message="Merchant already exists.",
            status_code=409,
            details={"merchant_id": request.merchant_id},
        )

    merchant = merchant_repository.create(
        db=db,
        merchant_id=request.merchant_id,
        merchant_name=request.merchant_name,
        legal_name=request.legal_name,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        webhook_url=request.webhook_url,
        settlement_account_name=request.settlement_account_name,
        settlement_account_number=request.settlement_account_number,
        settlement_bank_code=request.settlement_bank_code,
    )
    _record_audit(
        db=db,
        event_type="MERCHANT_CREATED",
        entity_type=EntityType.MERCHANT,
        entity_id=merchant.id,
        actor=actor,
        before_state=None,
        after_state=_merchant_state(merchant),
    )
    db.commit()
    return MerchantOpsResponse.from_merchant(merchant)


def submit_onboarding_case(
    db: Session,
    merchant_id: str,
    request: SubmitOnboardingCaseRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> OnboardingCaseResponse:
    merchant = _require_merchant(db, merchant_id)
    onboarding_case = onboarding_repository.get_by_merchant(db, merchant.id)
    before_state = _onboarding_case_state(onboarding_case) if onboarding_case is not None else None

    if onboarding_case is None:
        onboarding_case = onboarding_repository.create(
            db=db,
            merchant_db_id=merchant.id,
            status=OnboardingCaseStatus.PENDING_REVIEW,
            domain_or_app_name=request.domain_or_app_name,
            submitted_profile_json=request.submitted_profile_json,
            documents_json=request.documents_json,
            review_checks_json=request.review_checks_json,
        )
    else:
        if onboarding_case.status in FINAL_ONBOARDING_STATUSES:
            raise AppError(
                error_code="ONBOARDING_CASE_FINAL",
                message="Final onboarding cases cannot be updated.",
                status_code=409,
                details={"merchant_id": merchant_id, "status": onboarding_case.status.value},
            )
        onboarding_case.status = OnboardingCaseStatus.PENDING_REVIEW
        onboarding_case.domain_or_app_name = request.domain_or_app_name
        onboarding_case.submitted_profile_json = request.submitted_profile_json
        onboarding_case.documents_json = request.documents_json
        onboarding_case.review_checks_json = request.review_checks_json
        onboarding_case.decision_note = None
        onboarding_case.reviewed_by = None
        onboarding_case.reviewed_at = None
        onboarding_repository.save(db, onboarding_case)

    _record_audit(
        db=db,
        event_type="ONBOARDING_CASE_SUBMITTED",
        entity_type=EntityType.ONBOARDING_CASE,
        entity_id=onboarding_case.id,
        actor=actor,
        before_state=before_state,
        after_state=_onboarding_case_state(onboarding_case),
    )
    db.commit()
    return OnboardingCaseResponse.from_case(onboarding_case, merchant.merchant_id)


def approve_onboarding_case(
    db: Session,
    merchant_id: str,
    request: ReviewOnboardingCaseRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> OnboardingCaseResponse:
    return _decide_onboarding_case(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=actor,
        target_status=OnboardingCaseStatus.APPROVED,
        event_type="ONBOARDING_CASE_APPROVED",
        now=now,
    )


def reject_onboarding_case(
    db: Session,
    merchant_id: str,
    request: ReviewOnboardingCaseRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> OnboardingCaseResponse:
    return _decide_onboarding_case(
        db=db,
        merchant_id=merchant_id,
        request=request,
        actor=actor,
        target_status=OnboardingCaseStatus.REJECTED,
        event_type="ONBOARDING_CASE_REJECTED",
        now=now,
    )


def create_credential(
    db: Session,
    merchant_id: str,
    request: CreateCredentialRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> CredentialOpsResponse:
    merchant = _require_merchant(db, merchant_id)
    active_credential = credential_repository.get_active_by_merchant(db, merchant.id)
    if active_credential is not None:
        raise AppError(
            error_code="ACTIVE_CREDENTIAL_EXISTS",
            message="An active credential already exists for this merchant.",
            status_code=409,
            details={"merchant_id": merchant_id},
        )

    credential = credential_repository.create(
        db=db,
        merchant_db_id=merchant.id,
        access_key=request.access_key,
        secret_key=request.secret_key,
        now=now,
    )
    _record_audit(
        db=db,
        event_type="CREDENTIAL_CREATED",
        entity_type=EntityType.MERCHANT_CREDENTIAL,
        entity_id=credential.id,
        actor=actor,
        before_state=None,
        after_state=_credential_state(credential),
    )
    db.commit()
    return CredentialOpsResponse.from_credential(credential, merchant.merchant_id)


def activate_merchant(
    db: Session,
    merchant_id: str,
    request: OpsReasonRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> MerchantOpsResponse:
    merchant = _require_merchant(db, merchant_id)
    onboarding_case = onboarding_repository.get_by_merchant(db, merchant.id)
    if onboarding_case is None or onboarding_case.status != OnboardingCaseStatus.APPROVED:
        raise AppError(
            error_code="ONBOARDING_CASE_NOT_APPROVED",
            message="Merchant onboarding must be approved before activation.",
            status_code=409,
            details={"merchant_id": merchant_id},
        )
    if credential_repository.get_active_by_merchant(db, merchant.id) is None:
        raise AppError(
            error_code="ACTIVE_CREDENTIAL_REQUIRED",
            message="An active credential is required before merchant activation.",
            status_code=409,
            details={"merchant_id": merchant_id},
        )
    return _change_merchant_status(
        db=db,
        merchant=merchant,
        actor=actor,
        status=MerchantStatus.ACTIVE,
        event_type="MERCHANT_ACTIVATED",
    )


def suspend_merchant(
    db: Session,
    merchant_id: str,
    request: OpsReasonRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> MerchantOpsResponse:
    merchant = _require_merchant(db, merchant_id)
    return _change_merchant_status(
        db=db,
        merchant=merchant,
        actor=actor,
        status=MerchantStatus.SUSPENDED,
        event_type="MERCHANT_SUSPENDED",
    )


def disable_merchant(
    db: Session,
    merchant_id: str,
    request: OpsReasonRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> MerchantOpsResponse:
    merchant = _require_merchant(db, merchant_id)
    return _change_merchant_status(
        db=db,
        merchant=merchant,
        actor=actor,
        status=MerchantStatus.DISABLED,
        event_type="MERCHANT_DISABLED",
    )


def rotate_credential(
    db: Session,
    merchant_id: str,
    request: RotateCredentialRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> CredentialOpsResponse:
    rotated_at = now or utc_now()
    merchant = _require_merchant(db, merchant_id)
    old_credential = credential_repository.get_active_by_merchant(db, merchant.id)
    if old_credential is None:
        raise AppError(
            error_code="ACTIVE_CREDENTIAL_NOT_FOUND",
            message="Active credential was not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )

    before_state = _credential_state(old_credential)
    old_credential.status = CredentialStatus.ROTATED
    old_credential.rotated_at = rotated_at
    old_credential.expired_at = rotated_at
    credential_repository.save(db, old_credential)
    new_credential = credential_repository.create(
        db=db,
        merchant_db_id=merchant.id,
        access_key=request.access_key,
        secret_key=request.secret_key,
        now=rotated_at,
    )
    _record_audit(
        db=db,
        event_type="CREDENTIAL_ROTATED",
        entity_type=EntityType.MERCHANT_CREDENTIAL,
        entity_id=old_credential.id,
        actor=actor,
        before_state=before_state,
        after_state={
            "old_credential": _credential_state(old_credential),
            "new_credential": _credential_state(new_credential),
        },
    )
    db.commit()
    return CredentialOpsResponse.from_credential(new_credential, merchant.merchant_id)


def _decide_onboarding_case(
    db: Session,
    merchant_id: str,
    request: ReviewOnboardingCaseRequest,
    actor: OpsActorContext,
    target_status: OnboardingCaseStatus,
    event_type: str,
    now: datetime | None = None,
) -> OnboardingCaseResponse:
    reviewed_at = now or utc_now()
    merchant = _require_merchant(db, merchant_id)
    onboarding_case = onboarding_repository.get_by_merchant(db, merchant.id)
    if onboarding_case is None:
        raise AppError(
            error_code="ONBOARDING_CASE_NOT_FOUND",
            message="Onboarding case not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    if onboarding_case.status != OnboardingCaseStatus.PENDING_REVIEW:
        raise AppError(
            error_code="ONBOARDING_CASE_FINAL",
            message="Onboarding case is not pending review.",
            status_code=409,
            details={"merchant_id": merchant_id, "status": onboarding_case.status.value},
        )

    before_state = _onboarding_case_state(onboarding_case)
    onboarding_case.status = target_status
    onboarding_case.reviewed_by = request.reviewed_by or actor.actor_id
    onboarding_case.reviewed_at = reviewed_at
    onboarding_case.decision_note = request.decision_note
    onboarding_repository.save(db, onboarding_case)
    _record_audit(
        db=db,
        event_type=event_type,
        entity_type=EntityType.ONBOARDING_CASE,
        entity_id=onboarding_case.id,
        actor=actor,
        before_state=before_state,
        after_state=_onboarding_case_state(onboarding_case),
    )
    db.commit()
    return OnboardingCaseResponse.from_case(onboarding_case, merchant.merchant_id)


def _change_merchant_status(
    db: Session,
    merchant: Merchant,
    actor: OpsActorContext,
    status: MerchantStatus,
    event_type: str,
) -> MerchantOpsResponse:
    before_state = _merchant_state(merchant)
    merchant.status = status
    merchant_repository.save(db, merchant)
    _record_audit(
        db=db,
        event_type=event_type,
        entity_type=EntityType.MERCHANT,
        entity_id=merchant.id,
        actor=actor,
        before_state=before_state,
        after_state=_merchant_state(merchant),
    )
    db.commit()
    return MerchantOpsResponse.from_merchant(merchant)


def _require_merchant(db: Session, merchant_id: str) -> Merchant:
    merchant = merchant_repository.get_by_public_merchant_id(db, merchant_id)
    if merchant is None:
        raise AppError(
            error_code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    return merchant


def _record_audit(
    db: Session,
    event_type: str,
    entity_type: EntityType,
    entity_id,
    actor: OpsActorContext,
    before_state: dict | None,
    after_state: dict | None,
):
    return audit_service.record_event(
        db=db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        before_state=before_state,
        after_state=after_state,
        reason=actor.reason,
    )


def _merchant_state(merchant: Merchant) -> dict[str, Any]:
    return {
        "id": str(merchant.id),
        "merchant_id": merchant.merchant_id,
        "merchant_name": merchant.merchant_name,
        "legal_name": merchant.legal_name,
        "contact_name": merchant.contact_name,
        "contact_email": merchant.contact_email,
        "contact_phone": merchant.contact_phone,
        "webhook_url": merchant.webhook_url,
        "status": _enum_value(merchant.status),
        "settlement_account_name": merchant.settlement_account_name,
        "settlement_account_number": merchant.settlement_account_number,
        "settlement_bank_code": merchant.settlement_bank_code,
    }


def _onboarding_case_state(onboarding_case: MerchantOnboardingCase | None) -> dict[str, Any] | None:
    if onboarding_case is None:
        return None
    return {
        "id": str(onboarding_case.id),
        "merchant_db_id": str(onboarding_case.merchant_db_id),
        "status": _enum_value(onboarding_case.status),
        "domain_or_app_name": onboarding_case.domain_or_app_name,
        "submitted_profile_json": onboarding_case.submitted_profile_json,
        "documents_json": onboarding_case.documents_json,
        "review_checks_json": onboarding_case.review_checks_json,
        "decision_note": onboarding_case.decision_note,
        "reviewed_by": str(onboarding_case.reviewed_by) if onboarding_case.reviewed_by else None,
        "reviewed_at": _datetime_value(onboarding_case.reviewed_at),
    }


def _credential_state(credential: MerchantCredential) -> dict[str, Any]:
    return {
        "id": str(credential.id),
        "merchant_db_id": str(credential.merchant_db_id),
        "access_key": credential.access_key,
        "secret_key_encrypted": credential.secret_key_encrypted,
        "secret_key_last4": credential.secret_key_last4,
        "status": _enum_value(credential.status),
        "expired_at": _datetime_value(credential.expired_at),
        "rotated_at": _datetime_value(credential.rotated_at),
    }


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _datetime_value(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()

