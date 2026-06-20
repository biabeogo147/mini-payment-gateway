from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.provider_callback import (
    PaymentCallbackRequest,
    PaymentCallbackResponse,
    RefundCallbackRequest,
    RefundCallbackResponse,
)
from app.services import provider_callback_auth_service, provider_callback_service

router = APIRouter(prefix="/v1/provider/callbacks", tags=["provider-callbacks"])


@router.post("/payment", response_model=PaymentCallbackResponse)
async def process_payment_callback(
    raw_request: Request,
    request: PaymentCallbackRequest,
    db: Session = Depends(get_db),
) -> PaymentCallbackResponse:
    """Signed simulator/provider endpoint for payment result callbacks."""
    body = await raw_request.body()
    provider_callback_auth_service.authenticate_provider_callback_request(
        method=raw_request.method,
        path=raw_request.url.path,
        body=body,
        headers=raw_request.headers,
    )
    return provider_callback_service.process_payment_callback(db=db, request=request)


@router.post("/refund", response_model=RefundCallbackResponse)
async def process_refund_callback(
    raw_request: Request,
    request: RefundCallbackRequest,
    db: Session = Depends(get_db),
) -> RefundCallbackResponse:
    """Signed simulator/provider endpoint for refund result callbacks."""
    body = await raw_request.body()
    provider_callback_auth_service.authenticate_provider_callback_request(
        method=raw_request.method,
        path=raw_request.url.path,
        body=body,
        headers=raw_request.headers,
    )
    return provider_callback_service.process_refund_callback(db=db, request=request)
