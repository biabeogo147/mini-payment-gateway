from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.webhook import WebhookManualRetryRequest, WebhookRetryResponse
from app.services import webhook_delivery_service

router = APIRouter(prefix="/v1/ops/webhooks", tags=["webhook-ops"])


@router.post("/{event_id}/retry", response_model=WebhookRetryResponse)
def retry_webhook_event(
    event_id: str,
    audit_context: WebhookManualRetryRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> WebhookRetryResponse:
    return webhook_delivery_service.manual_retry(
        db=db,
        event_id=event_id,
        audit_context=audit_context,
    )
