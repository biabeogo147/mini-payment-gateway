from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.provider_callback import (
    PaymentCallbackRequest,
    PaymentCallbackResponse,
    RefundCallbackRequest,
    RefundCallbackResponse,
)
from app.services import provider_callback_service

router = APIRouter(prefix="/v1/provider/callbacks", tags=["provider-callbacks"])


@router.post("/payment", response_model=PaymentCallbackResponse)
def process_payment_callback(
    request: PaymentCallbackRequest,
    db: Session = Depends(get_db),
) -> PaymentCallbackResponse:
    """Trusted simulator/provider endpoint for MVP payment result callbacks."""
    return provider_callback_service.process_payment_callback(db=db, request=request)


@router.post("/refund", response_model=RefundCallbackResponse)
def process_refund_callback(
    request: RefundCallbackRequest,
    db: Session = Depends(get_db),
) -> RefundCallbackResponse:
    """Trusted simulator/provider endpoint for MVP refund result callbacks."""
    return provider_callback_service.process_refund_callback(db=db, request=request)
