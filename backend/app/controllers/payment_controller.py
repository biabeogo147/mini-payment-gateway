from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.controllers.deps import get_authenticated_merchant, get_db
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.payment import CreatePaymentRequest, PaymentResponse, PaymentStatusResponse
from app.services import payment_service

router = APIRouter(prefix="/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse)
def create_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> PaymentResponse:
    return payment_service.create_payment(
        db=db,
        authenticated_merchant=authenticated_merchant,
        request=request,
        idempotency_key=idempotency_key,
    )


@router.get("/by-order/{order_id}", response_model=PaymentStatusResponse)
def get_payment_by_order(
    order_id: str,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
) -> PaymentStatusResponse:
    return payment_service.get_payment_by_order_id(
        db=db,
        authenticated_merchant=authenticated_merchant,
        order_id=order_id,
    )


@router.get("/{transaction_id}", response_model=PaymentStatusResponse)
def get_payment_by_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
) -> PaymentStatusResponse:
    return payment_service.get_payment_by_transaction_id(
        db=db,
        authenticated_merchant=authenticated_merchant,
        transaction_id=transaction_id,
    )
