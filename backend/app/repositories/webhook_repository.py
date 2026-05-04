from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DeliveryAttemptResult, EntityType, WebhookEventStatus
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent


def get_by_event_id(db: Session, event_id: str) -> WebhookEvent | None:
    return db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))


def get_existing_event(
    db: Session,
    merchant_db_id: UUID,
    event_type: str,
    entity_type: EntityType,
    entity_id: UUID,
) -> WebhookEvent | None:
    return db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.merchant_db_id == merchant_db_id,
            WebhookEvent.event_type == event_type,
            WebhookEvent.entity_type == entity_type,
            WebhookEvent.entity_id == entity_id,
        )
    )


def find_due_events(db: Session, now: datetime, limit: int = 100) -> list[WebhookEvent]:
    return list(
        db.scalars(
            select(WebhookEvent)
            .where(
                WebhookEvent.status == WebhookEventStatus.PENDING,
                WebhookEvent.next_retry_at.is_not(None),
                WebhookEvent.next_retry_at <= now,
            )
            .order_by(WebhookEvent.next_retry_at.asc(), WebhookEvent.created_at.asc())
            .limit(limit)
        ).all()
    )


def create_event(
    db: Session,
    event_id: str,
    merchant_db_id: UUID,
    event_type: str,
    entity_type: EntityType,
    entity_id: UUID,
    payload_json: dict,
    next_retry_at: datetime | None,
) -> WebhookEvent:
    event = WebhookEvent(
        event_id=event_id,
        merchant_db_id=merchant_db_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload_json,
        status=WebhookEventStatus.PENDING,
        attempt_count=0,
        next_retry_at=next_retry_at,
    )
    db.add(event)
    db.flush()
    return event


def save_event(db: Session, event: WebhookEvent) -> WebhookEvent:
    db.add(event)
    db.flush()
    return event


def create_delivery_attempt(
    db: Session,
    webhook_event_id: UUID,
    attempt_no: int,
    request_url: str,
    request_headers_json: dict,
    request_body_json: dict,
    response_status_code: int | None,
    response_body_snippet: str | None,
    error_message: str | None,
    started_at: datetime,
    finished_at: datetime | None,
    result: DeliveryAttemptResult,
) -> WebhookDeliveryAttempt:
    attempt = WebhookDeliveryAttempt(
        webhook_event_id=webhook_event_id,
        attempt_no=attempt_no,
        request_url=request_url,
        request_headers_json=request_headers_json,
        request_body_json=request_body_json,
        response_status_code=response_status_code,
        response_body_snippet=response_body_snippet,
        error_message=error_message,
        started_at=started_at,
        finished_at=finished_at,
        result=result,
    )
    db.add(attempt)
    db.flush()
    return attempt
