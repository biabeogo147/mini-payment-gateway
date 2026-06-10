from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_merchant_user, get_db
from app.models.enums import PaymentStatus, RefundStatus, WebhookEventStatus
from app.models.merchant_user import MerchantUser
from app.schemas.merchant_portal import (
    MerchantPortalAnalyticsResponse,
    MerchantPortalCredentialListResponse,
    MerchantPortalDashboardChartsResponse,
    MerchantPortalDashboardSummaryResponse,
    MerchantPortalProfileResponse,
)
from app.schemas.ops_dashboard import (
    PaymentDetailResponse,
    PaymentListResponse,
    RefundDetailResponse,
    RefundListResponse,
    WebhookEventDetailResponse,
    WebhookEventListResponse,
)
from app.services import merchant_portal_service

router = APIRouter(prefix="/v1/merchant-portal", tags=["merchant-portal"])


@router.get("/dashboard/summary", response_model=MerchantPortalDashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalDashboardSummaryResponse:
    return merchant_portal_service.get_dashboard_summary(db=db, current_user=current_user)


@router.get("/dashboard/charts", response_model=MerchantPortalDashboardChartsResponse)
def get_dashboard_charts(
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalDashboardChartsResponse:
    return merchant_portal_service.get_dashboard_charts(db=db, current_user=current_user)


@router.get("/analytics", response_model=MerchantPortalAnalyticsResponse)
def get_analytics(
    days: int = Query(default=30),
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalAnalyticsResponse:
    return merchant_portal_service.get_analytics(
        db=db,
        current_user=current_user,
        days=days,
    )


@router.get("/profile", response_model=MerchantPortalProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalProfileResponse:
    return merchant_portal_service.get_profile(db=db, current_user=current_user)


@router.get("/credentials", response_model=MerchantPortalCredentialListResponse)
def list_credentials(
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> MerchantPortalCredentialListResponse:
    return merchant_portal_service.list_credentials(db=db, current_user=current_user)


@router.get("/payments", response_model=PaymentListResponse)
def list_payments(
    transaction_id: str | None = None,
    order_id: str | None = None,
    status: PaymentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> PaymentListResponse:
    return merchant_portal_service.list_payments(
        db=db,
        current_user=current_user,
        transaction_id=transaction_id,
        order_id=order_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/payments/{transaction_id}", response_model=PaymentDetailResponse)
def get_payment_detail(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> PaymentDetailResponse:
    return merchant_portal_service.get_payment_detail(
        db=db,
        current_user=current_user,
        transaction_id=transaction_id,
    )


@router.get("/refunds", response_model=RefundListResponse)
def list_refunds(
    refund_transaction_id: str | None = None,
    refund_id: str | None = None,
    status: RefundStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> RefundListResponse:
    return merchant_portal_service.list_refunds(
        db=db,
        current_user=current_user,
        refund_transaction_id=refund_transaction_id,
        refund_id=refund_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/refunds/{refund_transaction_id}", response_model=RefundDetailResponse)
def get_refund_detail(
    refund_transaction_id: str,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> RefundDetailResponse:
    return merchant_portal_service.get_refund_detail(
        db=db,
        current_user=current_user,
        refund_transaction_id=refund_transaction_id,
    )


@router.get("/webhooks", response_model=WebhookEventListResponse)
def list_webhooks(
    event_type: str | None = None,
    status: WebhookEventStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> WebhookEventListResponse:
    return merchant_portal_service.list_webhooks(
        db=db,
        current_user=current_user,
        event_type=event_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/webhooks/{event_id}", response_model=WebhookEventDetailResponse)
def get_webhook_detail(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
) -> WebhookEventDetailResponse:
    return merchant_portal_service.get_webhook_detail(
        db=db,
        current_user=current_user,
        event_id=event_id,
    )
