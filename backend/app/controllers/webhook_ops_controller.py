from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import build_ops_actor, get_db, require_ops_user
from app.models.internal_user import InternalUser
from app.schemas.webhook import WebhookManualRetryRequest, WebhookRetryResponse
from app.services import webhook_delivery_service

router = APIRouter(prefix="/v1/ops/webhooks", tags=["webhook-ops"])


@router.post("/{event_id}/retry", response_model=WebhookRetryResponse)
def retry_webhook_event(
    event_id: str,
    audit_context: WebhookManualRetryRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: InternalUser = Depends(require_ops_user),
) -> WebhookRetryResponse:
    return webhook_delivery_service.manual_retry(
        db=db,
        event_id=event_id,
        audit_context=build_ops_actor(current_user, audit_context),
    )
