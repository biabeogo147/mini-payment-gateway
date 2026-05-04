from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.controllers.deps import get_authenticated_merchant, get_db
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.refund import CreateRefundRequest, RefundResponse, RefundStatusResponse
from app.services import refund_service

router = APIRouter(prefix="/v1/refunds", tags=["refunds"])


@router.post("", response_model=RefundResponse)
def create_refund(
    request: CreateRefundRequest,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> RefundResponse:
    return refund_service.create_refund(
        db=db,
        authenticated_merchant=authenticated_merchant,
        request=request,
        idempotency_key=idempotency_key,
    )


@router.get("/by-refund-id/{refund_id}", response_model=RefundStatusResponse)
def get_refund_by_refund_id(
    refund_id: str,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
) -> RefundStatusResponse:
    return refund_service.get_refund_by_refund_id(
        db=db,
        authenticated_merchant=authenticated_merchant,
        refund_id=refund_id,
    )


@router.get("/{refund_transaction_id}", response_model=RefundStatusResponse)
def get_refund_by_transaction(
    refund_transaction_id: str,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
) -> RefundStatusResponse:
    return refund_service.get_refund_by_transaction_id(
        db=db,
        authenticated_merchant=authenticated_merchant,
        refund_transaction_id=refund_transaction_id,
    )
