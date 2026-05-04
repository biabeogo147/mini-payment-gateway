from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import ActorType, CredentialStatus, MerchantStatus, OnboardingCaseStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase


class OpsActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_type: ActorType
    actor_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=1000)


class CreateMerchantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext
    merchant_id: str = Field(min_length=1, max_length=64)
    merchant_name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str = Field(min_length=1, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)
    webhook_url: str | None = None
    settlement_account_name: str | None = Field(default=None, max_length=255)
    settlement_account_number: str | None = Field(default=None, max_length=64)
    settlement_bank_code: str | None = Field(default=None, max_length=32)


class MerchantOpsResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    status: MerchantStatus

    @classmethod
    def from_merchant(cls, merchant: Merchant) -> "MerchantOpsResponse":
        return cls(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            status=merchant.status,
        )


class SubmitOnboardingCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext
    domain_or_app_name: str | None = Field(default=None, max_length=255)
    submitted_profile_json: dict[str, Any]
    documents_json: dict[str, Any]
    review_checks_json: dict[str, Any] = Field(default_factory=dict)


class OnboardingCaseResponse(BaseModel):
    case_id: str
    merchant_id: str
    status: OnboardingCaseStatus
    domain_or_app_name: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    decision_note: str | None = None

    @field_serializer("reviewed_at")
    def serialize_reviewed_at(self, value: datetime | None) -> str | None:
        return _serialize_datetime(value)

    @classmethod
    def from_case(cls, onboarding_case: MerchantOnboardingCase, merchant_id: str) -> "OnboardingCaseResponse":
        return cls(
            case_id=str(onboarding_case.id),
            merchant_id=merchant_id,
            status=onboarding_case.status,
            domain_or_app_name=onboarding_case.domain_or_app_name,
            reviewed_by=onboarding_case.reviewed_by,
            reviewed_at=onboarding_case.reviewed_at,
            decision_note=onboarding_case.decision_note,
        )


class ReviewOnboardingCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext
    reviewed_by: UUID | None = None
    decision_note: str = Field(min_length=1)


class CreateCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext
    access_key: str = Field(min_length=1, max_length=128)
    secret_key: str = Field(min_length=1)


class RotateCredentialRequest(CreateCredentialRequest):
    pass


class CredentialOpsResponse(BaseModel):
    credential_id: str
    merchant_id: str
    access_key: str
    secret_key_last4: str
    status: CredentialStatus
    expired_at: datetime | None = None
    rotated_at: datetime | None = None

    @field_serializer("expired_at", "rotated_at")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        return _serialize_datetime(value)

    @classmethod
    def from_credential(
        cls,
        credential: MerchantCredential,
        merchant_id: str,
    ) -> "CredentialOpsResponse":
        return cls(
            credential_id=str(credential.id),
            merchant_id=merchant_id,
            access_key=credential.access_key,
            secret_key_last4=credential.secret_key_last4,
            status=credential.status,
            expired_at=credential.expired_at,
            rotated_at=credential.rotated_at,
        )


class OpsReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
