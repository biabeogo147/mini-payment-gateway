from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import OnboardingCaseStatus
from app.models import internal_user as _internal_user  # noqa: F401
from app.models.merchant_onboarding_case import MerchantOnboardingCase


def get_by_merchant(
    db: Session,
    merchant_db_id: UUID,
) -> MerchantOnboardingCase | None:
    return db.scalar(
        select(MerchantOnboardingCase).where(MerchantOnboardingCase.merchant_db_id == merchant_db_id)
    )


def get_by_id(
    db: Session,
    case_id: UUID,
) -> MerchantOnboardingCase | None:
    return db.scalar(select(MerchantOnboardingCase).where(MerchantOnboardingCase.id == case_id))


def create(
    db: Session,
    merchant_db_id: UUID,
    status: OnboardingCaseStatus,
    domain_or_app_name: str | None,
    submitted_profile_json: dict,
    documents_json: dict,
    review_checks_json: dict,
) -> MerchantOnboardingCase:
    onboarding_case = MerchantOnboardingCase(
        merchant_db_id=merchant_db_id,
        status=status,
        domain_or_app_name=domain_or_app_name,
        submitted_profile_json=submitted_profile_json,
        documents_json=documents_json,
        review_checks_json=review_checks_json,
    )
    db.add(onboarding_case)
    db.flush()
    return onboarding_case


def save(
    db: Session,
    onboarding_case: MerchantOnboardingCase,
) -> MerchantOnboardingCase:
    db.add(onboarding_case)
    db.flush()
    return onboarding_case
