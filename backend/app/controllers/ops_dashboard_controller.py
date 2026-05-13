from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db, require_ops_user
from app.models.enums import ActorType, EntityType, MerchantStatus, OnboardingCaseStatus, PaymentStatus, RefundStatus, WebhookEventStatus
from app.models.internal_user import InternalUser
from app.schemas.ops_dashboard import (
    AuditLogListResponse,
    DashboardChartsResponse,
    DashboardSummaryResponse,
    MerchantCredentialListResponse,
    MerchantDetailResponse,
    MerchantListResponse,
    OnboardingCaseDetailResponse,
    PaymentDetailResponse,
    PaymentListResponse,
    RefundDetailResponse,
    RefundListResponse,
    WebhookAttemptsListResponse,
    WebhookEventDetailResponse,
    WebhookEventListResponse,
)
from app.services import ops_dashboard_service

router = APIRouter(prefix="/v1/ops", tags=["ops-dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> DashboardSummaryResponse:
    return ops_dashboard_service.get_dashboard_summary(db=db)


@router.get("/dashboard/charts", response_model=DashboardChartsResponse)
def get_dashboard_charts(
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> DashboardChartsResponse:
    return ops_dashboard_service.get_dashboard_charts(db=db)


@router.get("/merchants", response_model=MerchantListResponse)
def list_merchants(
    search: str | None = None,
    status: MerchantStatus | None = None,
    onboarding_status: OnboardingCaseStatus | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantListResponse:
    return ops_dashboard_service.list_merchants(
        db=db,
        search=search,
        status=status,
        onboarding_status=onboarding_status,
        limit=limit,
    )


@router.get("/merchants/{merchant_id}/onboarding-case", response_model=OnboardingCaseDetailResponse)
def get_merchant_onboarding_case(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> OnboardingCaseDetailResponse:
    return ops_dashboard_service.get_merchant_onboarding_case(db=db, merchant_id=merchant_id)


@router.get("/merchants/{merchant_id}/credentials", response_model=MerchantCredentialListResponse)
def list_merchant_credentials(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantCredentialListResponse:
    return ops_dashboard_service.list_merchant_credentials(db=db, merchant_id=merchant_id)


@router.get("/merchants/{merchant_id}", response_model=MerchantDetailResponse)
def get_merchant_detail(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> MerchantDetailResponse:
    return ops_dashboard_service.get_merchant_detail(db=db, merchant_id=merchant_id)


@router.get("/payments", response_model=PaymentListResponse)
def list_payments(
    transaction_id: str | None = None,
    order_id: str | None = None,
    merchant_id: str | None = None,
    status: PaymentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> PaymentListResponse:
    return ops_dashboard_service.list_payments(
        db=db,
        transaction_id=transaction_id,
        order_id=order_id,
        merchant_id=merchant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/payments/{transaction_id}", response_model=PaymentDetailResponse)
def get_payment_detail(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> PaymentDetailResponse:
    return ops_dashboard_service.get_payment_detail(db=db, transaction_id=transaction_id)


@router.get("/refunds", response_model=RefundListResponse)
def list_refunds(
    refund_transaction_id: str | None = None,
    refund_id: str | None = None,
    merchant_id: str | None = None,
    status: RefundStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> RefundListResponse:
    return ops_dashboard_service.list_refunds(
        db=db,
        refund_transaction_id=refund_transaction_id,
        refund_id=refund_id,
        merchant_id=merchant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/refunds/{refund_transaction_id}", response_model=RefundDetailResponse)
def get_refund_detail(
    refund_transaction_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> RefundDetailResponse:
    return ops_dashboard_service.get_refund_detail(db=db, refund_transaction_id=refund_transaction_id)


@router.get("/webhooks", response_model=WebhookEventListResponse)
def list_webhooks(
    event_type: str | None = None,
    status: WebhookEventStatus | None = None,
    merchant_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> WebhookEventListResponse:
    return ops_dashboard_service.list_webhooks(
        db=db,
        event_type=event_type,
        status=status,
        merchant_id=merchant_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/webhooks/{event_id}/attempts", response_model=WebhookAttemptsListResponse)
def list_webhook_attempts(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> WebhookAttemptsListResponse:
    return ops_dashboard_service.list_webhook_attempts(db=db, event_id=event_id)


@router.get("/webhooks/{event_id}", response_model=WebhookEventDetailResponse)
def get_webhook_detail(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> WebhookEventDetailResponse:
    return ops_dashboard_service.get_webhook_detail(db=db, event_id=event_id)


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    actor_type: ActorType | None = None,
    actor_id: UUID | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=200, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> AuditLogListResponse:
    return ops_dashboard_service.list_audit_logs(
        db=db,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
