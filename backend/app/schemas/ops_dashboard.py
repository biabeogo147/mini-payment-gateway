from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditLog
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import (
    ActorType,
    CallbackProcessingResult,
    CallbackSourceType,
    CallbackType,
    CredentialStatus,
    DeliveryAttemptResult,
    EntityType,
    MerchantQrAccountStatus,
    MerchantStatus,
    OnboardingCaseStatus,
    PaymentStatus,
    QrProvider,
    ReconciliationStatus,
    RefundStatus,
    WebhookEventStatus,
)
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase
from app.models.merchant_qr_account import MerchantQrAccount
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord
from app.models.refund_transaction import RefundTransaction
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent
from app.schemas.reconciliation import ReconciliationRecordResponse


def _serialize_datetime(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class OpsDashboardBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={
            datetime: _serialize_datetime,
            Decimal: lambda value: str(value),
            date: lambda value: value.isoformat(),
        },
    )


class AuditLogItemResponse(OpsDashboardBaseModel):
    log_id: str
    event_type: str
    entity_type: EntityType
    entity_id: str
    actor_type: ActorType
    actor_id: str | None = None
    reason: str | None = None
    before_state_json: dict[str, Any] | None = None
    after_state_json: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_log(cls, log: AuditLog) -> "AuditLogItemResponse":
        return cls(
            log_id=str(log.id),
            event_type=log.event_type,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            actor_type=log.actor_type,
            actor_id=str(log.actor_id) if log.actor_id else None,
            reason=log.reason,
            before_state_json=log.before_state_json,
            after_state_json=log.after_state_json,
            created_at=log.created_at,
        )


class AuditLogListResponse(OpsDashboardBaseModel):
    logs: list[AuditLogItemResponse]


class CallbackEvidenceResponse(OpsDashboardBaseModel):
    callback_id: str
    source_type: CallbackSourceType
    callback_type: CallbackType
    external_reference: str | None = None
    transaction_reference: str | None = None
    normalized_status: str | None = None
    processing_result: CallbackProcessingResult
    error_message: str | None = None
    raw_payload_json: dict[str, Any]
    received_at: datetime
    processed_at: datetime | None = None

    @classmethod
    def from_log(cls, log: BankCallbackLog) -> "CallbackEvidenceResponse":
        return cls(
            callback_id=str(log.id),
            source_type=log.source_type,
            callback_type=log.callback_type,
            external_reference=log.external_reference,
            transaction_reference=log.transaction_reference,
            normalized_status=log.normalized_status,
            processing_result=log.processing_result,
            error_message=log.error_message,
            raw_payload_json=log.raw_payload_json,
            received_at=log.received_at,
            processed_at=log.processed_at,
        )


class PaymentListItemResponse(OpsDashboardBaseModel):
    transaction_id: str
    merchant_id: str
    merchant_name: str
    order_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    expire_at: datetime
    paid_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_payment(
        cls,
        payment: PaymentTransaction,
        merchant: Merchant,
    ) -> "PaymentListItemResponse":
        return cls(
            transaction_id=payment.transaction_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            expire_at=payment.expire_at,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
        )


class PaymentRefundLinkResponse(OpsDashboardBaseModel):
    refund_transaction_id: str
    refund_id: str
    refund_amount: Decimal
    refund_status: RefundStatus
    created_at: datetime

    @classmethod
    def from_refund(cls, refund: RefundTransaction) -> "PaymentRefundLinkResponse":
        return cls(
            refund_transaction_id=refund.refund_transaction_id,
            refund_id=refund.refund_id,
            refund_amount=refund.refund_amount,
            refund_status=refund.status,
            created_at=refund.created_at,
        )


class PaymentDetailResponse(PaymentListItemResponse):
    description: str
    qr_reference: str | None = None
    qr_content: str
    qr_image_url: str | None = None
    qr_image_base64: str | None = None
    external_reference: str | None = None
    idempotency_key: str | None = None
    failed_reason_code: str | None = None
    failed_reason_message: str | None = None
    callback_logs: list[CallbackEvidenceResponse]
    refunds: list[PaymentRefundLinkResponse]
    reconciliation: ReconciliationRecordResponse | None = None

    @classmethod
    def from_bundle(
        cls,
        *,
        payment: PaymentTransaction,
        merchant: Merchant,
        callback_logs: list[BankCallbackLog],
        refunds: list[RefundTransaction],
        reconciliation: ReconciliationRecord | None,
    ) -> "PaymentDetailResponse":
        return cls(
            **PaymentListItemResponse.from_payment(payment, merchant).model_dump(),
            description=payment.description,
            qr_reference=payment.qr_reference,
            qr_content=payment.qr_content,
            qr_image_url=payment.qr_image_url,
            qr_image_base64=payment.qr_image_base64,
            external_reference=payment.external_reference,
            idempotency_key=payment.idempotency_key,
            failed_reason_code=payment.failed_reason_code,
            failed_reason_message=payment.failed_reason_message,
            callback_logs=[CallbackEvidenceResponse.from_log(item) for item in callback_logs],
            refunds=[PaymentRefundLinkResponse.from_refund(item) for item in refunds],
            reconciliation=(
                ReconciliationRecordResponse.from_record(reconciliation)
                if reconciliation is not None
                else None
            ),
        )


class PaymentListResponse(OpsDashboardBaseModel):
    payments: list[PaymentListItemResponse]


class RefundListItemResponse(OpsDashboardBaseModel):
    refund_transaction_id: str
    refund_id: str
    merchant_id: str
    merchant_name: str
    original_transaction_id: str
    refund_amount: Decimal
    refund_status: RefundStatus
    reason: str
    created_at: datetime

    @classmethod
    def from_bundle(
        cls,
        *,
        refund: RefundTransaction,
        merchant: Merchant,
        payment: PaymentTransaction,
    ) -> "RefundListItemResponse":
        return cls(
            refund_transaction_id=refund.refund_transaction_id,
            refund_id=refund.refund_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            original_transaction_id=payment.transaction_id,
            refund_amount=refund.refund_amount,
            refund_status=refund.status,
            reason=refund.reason,
            created_at=refund.created_at,
        )


class RefundDetailResponse(RefundListItemResponse):
    external_reference: str | None = None
    idempotency_key: str | None = None
    processed_at: datetime | None = None
    failed_reason_code: str | None = None
    failed_reason_message: str | None = None
    callback_logs: list[CallbackEvidenceResponse]
    reconciliation: ReconciliationRecordResponse | None = None

    @classmethod
    def from_full_bundle(
        cls,
        *,
        refund: RefundTransaction,
        merchant: Merchant,
        payment: PaymentTransaction,
        callback_logs: list[BankCallbackLog],
        reconciliation: ReconciliationRecord | None,
    ) -> "RefundDetailResponse":
        return cls(
            **RefundListItemResponse.from_bundle(
                refund=refund,
                merchant=merchant,
                payment=payment,
            ).model_dump(),
            external_reference=refund.external_reference,
            idempotency_key=refund.idempotency_key,
            processed_at=refund.processed_at,
            failed_reason_code=refund.failed_reason_code,
            failed_reason_message=refund.failed_reason_message,
            callback_logs=[CallbackEvidenceResponse.from_log(item) for item in callback_logs],
            reconciliation=(
                ReconciliationRecordResponse.from_record(reconciliation)
                if reconciliation is not None
                else None
            ),
        )


class RefundListResponse(OpsDashboardBaseModel):
    refunds: list[RefundListItemResponse]


class WebhookAttemptResponse(OpsDashboardBaseModel):
    attempt_id: str
    attempt_no: int
    request_url: str
    response_status_code: int | None = None
    response_body_snippet: str | None = None
    error_message: str | None = None
    result: DeliveryAttemptResult
    started_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def from_attempt(cls, attempt: WebhookDeliveryAttempt) -> "WebhookAttemptResponse":
        return cls(
            attempt_id=str(attempt.id),
            attempt_no=attempt.attempt_no,
            request_url=attempt.request_url,
            response_status_code=attempt.response_status_code,
            response_body_snippet=attempt.response_body_snippet,
            error_message=attempt.error_message,
            result=attempt.result,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
        )


class WebhookEventListItemResponse(OpsDashboardBaseModel):
    event_id: str
    merchant_id: str
    merchant_name: str
    event_type: str
    entity_type: EntityType
    entity_id: str
    status: WebhookEventStatus
    attempt_count: int
    next_retry_at: datetime | None = None
    last_attempt_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_bundle(
        cls,
        *,
        event: WebhookEvent,
        merchant: Merchant,
    ) -> "WebhookEventListItemResponse":
        return cls(
            event_id=event.event_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=str(event.entity_id),
            status=event.status,
            attempt_count=event.attempt_count,
            next_retry_at=event.next_retry_at,
            last_attempt_at=event.last_attempt_at,
            created_at=event.created_at,
        )


class WebhookEventDetailResponse(WebhookEventListItemResponse):
    payload_json: dict[str, Any]
    signature: str | None = None
    attempts: list[WebhookAttemptResponse]
    latest_failure_reason: str | None = None

    @classmethod
    def from_full_bundle(
        cls,
        *,
        event: WebhookEvent,
        merchant: Merchant,
        attempts: list[WebhookDeliveryAttempt],
    ) -> "WebhookEventDetailResponse":
        latest_failure_reason = next(
            (
                attempt.error_message or attempt.response_body_snippet
                for attempt in attempts
                if attempt.result != DeliveryAttemptResult.SUCCESS
                and (attempt.error_message or attempt.response_body_snippet)
            ),
            None,
        )
        return cls(
            **WebhookEventListItemResponse.from_bundle(event=event, merchant=merchant).model_dump(),
            payload_json=event.payload_json,
            signature=event.signature,
            attempts=[WebhookAttemptResponse.from_attempt(item) for item in attempts],
            latest_failure_reason=latest_failure_reason,
        )


class WebhookEventListResponse(OpsDashboardBaseModel):
    events: list[WebhookEventListItemResponse]


class WebhookAttemptsListResponse(OpsDashboardBaseModel):
    attempts: list[WebhookAttemptResponse]


class MerchantCredentialDetailResponse(OpsDashboardBaseModel):
    credential_id: str
    access_key: str
    secret_key_last4: str
    status: CredentialStatus
    expired_at: datetime | None = None
    rotated_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_credential(cls, credential: MerchantCredential) -> "MerchantCredentialDetailResponse":
        return cls(
            credential_id=str(credential.id),
            access_key=credential.access_key,
            secret_key_last4=credential.secret_key_last4,
            status=credential.status,
            expired_at=credential.expired_at,
            rotated_at=credential.rotated_at,
            created_at=credential.created_at,
        )


class MerchantCredentialListResponse(OpsDashboardBaseModel):
    credentials: list[MerchantCredentialDetailResponse]


class MerchantQrAccountDetailResponse(OpsDashboardBaseModel):
    qr_account_id: str
    provider: QrProvider
    bank_code: str
    bank_bin: str
    account_number: str
    account_name: str
    template: str
    status: MerchantQrAccountStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_qr_account(cls, qr_account: MerchantQrAccount) -> "MerchantQrAccountDetailResponse":
        return cls(
            qr_account_id=str(qr_account.id),
            provider=qr_account.provider,
            bank_code=qr_account.bank_code,
            bank_bin=qr_account.bank_bin,
            account_number=qr_account.account_number,
            account_name=qr_account.account_name,
            template=qr_account.template,
            status=qr_account.status,
            created_at=qr_account.created_at,
            updated_at=qr_account.updated_at,
        )


class OnboardingCaseDetailResponse(OpsDashboardBaseModel):
    case_id: str
    status: OnboardingCaseStatus
    domain_or_app_name: str | None = None
    submitted_profile_json: dict[str, Any]
    documents_json: dict[str, Any]
    review_checks_json: dict[str, Any]
    decision_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_case(cls, onboarding_case: MerchantOnboardingCase) -> "OnboardingCaseDetailResponse":
        return cls(
            case_id=str(onboarding_case.id),
            status=onboarding_case.status,
            domain_or_app_name=onboarding_case.domain_or_app_name,
            submitted_profile_json=onboarding_case.submitted_profile_json,
            documents_json=onboarding_case.documents_json,
            review_checks_json=onboarding_case.review_checks_json,
            decision_note=onboarding_case.decision_note,
            reviewed_by=str(onboarding_case.reviewed_by) if onboarding_case.reviewed_by else None,
            reviewed_at=onboarding_case.reviewed_at,
            created_at=onboarding_case.created_at,
            updated_at=onboarding_case.updated_at,
        )


class MerchantListItemResponse(OpsDashboardBaseModel):
    merchant_id: str
    merchant_name: str
    contact_email: str
    contact_name: str | None = None
    webhook_url: str | None = None
    status: MerchantStatus
    onboarding_status: OnboardingCaseStatus | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_bundle(
        cls,
        *,
        merchant: Merchant,
        onboarding_case: MerchantOnboardingCase | None,
    ) -> "MerchantListItemResponse":
        return cls(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            contact_email=merchant.contact_email,
            contact_name=merchant.contact_name,
            webhook_url=merchant.webhook_url,
            status=merchant.status,
            onboarding_status=onboarding_case.status if onboarding_case else None,
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
        )


class MerchantDetailResponse(OpsDashboardBaseModel):
    merchant_id: str
    merchant_name: str
    legal_name: str | None = None
    contact_name: str | None = None
    contact_email: str
    contact_phone: str | None = None
    webhook_url: str | None = None
    allowed_ip_list: list[str] | None = None
    status: MerchantStatus
    settlement_account_name: str | None = None
    settlement_account_number: str | None = None
    settlement_bank_code: str | None = None
    created_at: datetime
    updated_at: datetime
    onboarding_case: OnboardingCaseDetailResponse | None = None
    credentials: list[MerchantCredentialDetailResponse]
    qr_accounts: list[MerchantQrAccountDetailResponse]
    recent_payments: list[PaymentListItemResponse]
    recent_refunds: list[RefundListItemResponse]
    recent_webhooks: list[WebhookEventListItemResponse]
    recent_audit_logs: list[AuditLogItemResponse]

    @classmethod
    def from_full_bundle(
        cls,
        *,
        merchant: Merchant,
        onboarding_case: MerchantOnboardingCase | None,
        credentials: list[MerchantCredential],
        qr_accounts: list[MerchantQrAccount],
        recent_payments: list[tuple[PaymentTransaction, Merchant]],
        recent_refunds: list[tuple[RefundTransaction, Merchant, PaymentTransaction]],
        recent_webhooks: list[tuple[WebhookEvent, Merchant]],
        recent_audit_logs: list[AuditLog],
    ) -> "MerchantDetailResponse":
        return cls(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            legal_name=merchant.legal_name,
            contact_name=merchant.contact_name,
            contact_email=merchant.contact_email,
            contact_phone=merchant.contact_phone,
            webhook_url=merchant.webhook_url,
            allowed_ip_list=merchant.allowed_ip_list,
            status=merchant.status,
            settlement_account_name=merchant.settlement_account_name,
            settlement_account_number=merchant.settlement_account_number,
            settlement_bank_code=merchant.settlement_bank_code,
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
            onboarding_case=(
                OnboardingCaseDetailResponse.from_case(onboarding_case)
                if onboarding_case is not None
                else None
            ),
            credentials=[MerchantCredentialDetailResponse.from_credential(item) for item in credentials],
            qr_accounts=[MerchantQrAccountDetailResponse.from_qr_account(item) for item in qr_accounts],
            recent_payments=[PaymentListItemResponse.from_payment(item[0], item[1]) for item in recent_payments],
            recent_refunds=[
                RefundListItemResponse.from_bundle(refund=item[0], merchant=item[1], payment=item[2])
                for item in recent_refunds
            ],
            recent_webhooks=[
                WebhookEventListItemResponse.from_bundle(event=item[0], merchant=item[1])
                for item in recent_webhooks
            ],
            recent_audit_logs=[AuditLogItemResponse.from_log(item) for item in recent_audit_logs],
        )


class MerchantListResponse(OpsDashboardBaseModel):
    merchants: list[MerchantListItemResponse]


class DashboardMerchantQueueItemResponse(OpsDashboardBaseModel):
    merchant_id: str
    merchant_name: str
    contact_email: str
    onboarding_status: OnboardingCaseStatus
    created_at: datetime

    @classmethod
    def from_bundle(
        cls,
        *,
        merchant: Merchant,
        onboarding_case: MerchantOnboardingCase,
    ) -> "DashboardMerchantQueueItemResponse":
        return cls(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            contact_email=merchant.contact_email,
            onboarding_status=onboarding_case.status,
            created_at=onboarding_case.created_at,
        )


class DashboardWebhookQueueItemResponse(OpsDashboardBaseModel):
    event_id: str
    merchant_id: str
    merchant_name: str
    event_type: str
    status: WebhookEventStatus
    created_at: datetime

    @classmethod
    def from_bundle(
        cls,
        *,
        event: WebhookEvent,
        merchant: Merchant,
    ) -> "DashboardWebhookQueueItemResponse":
        return cls(
            event_id=event.event_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            event_type=event.event_type,
            status=event.status,
            created_at=event.created_at,
        )


class DashboardReconciliationQueueItemResponse(OpsDashboardBaseModel):
    record_id: str
    entity_type: EntityType
    match_result: ReconciliationStatus
    mismatch_reason_code: str | None = None
    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: ReconciliationRecord,
    ) -> "DashboardReconciliationQueueItemResponse":
        return cls(
            record_id=str(record.id),
            entity_type=record.entity_type,
            match_result=record.match_result,
            mismatch_reason_code=record.mismatch_reason_code,
            created_at=record.created_at,
        )


class DashboardSummaryResponse(OpsDashboardBaseModel):
    merchants_pending_review: int
    merchants_active: int
    payments_last_24h: int
    successful_payment_amount_last_24h: Decimal
    refunds_last_24h: int
    failed_webhook_events_open: int
    reconciliation_open: int
    onboarding_queue: list[DashboardMerchantQueueItemResponse]
    failed_webhooks: list[DashboardWebhookQueueItemResponse]
    reconciliation_queue: list[DashboardReconciliationQueueItemResponse]


class PaymentStatusChartPoint(OpsDashboardBaseModel):
    date: date
    pending: int
    success: int
    failed: int
    expired: int


class RefundCountChartPoint(OpsDashboardBaseModel):
    date: date
    count: int


class WebhookStatusChartPoint(OpsDashboardBaseModel):
    date: date
    pending: int
    delivered: int
    failed: int


class ReconciliationChartPoint(OpsDashboardBaseModel):
    date: date
    created: int
    resolved: int


class DashboardChartsResponse(OpsDashboardBaseModel):
    payment_status_by_day: list[PaymentStatusChartPoint]
    refund_count_by_day: list[RefundCountChartPoint]
    webhook_status_by_day: list[WebhookStatusChartPoint]
    reconciliation_by_day: list[ReconciliationChartPoint]
