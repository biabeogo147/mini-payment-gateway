import json
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import sha256_hex, sign_hmac_sha256
from app.core.time import utc_now
from app.models.enums import DeliveryAttemptResult, EntityType, WebhookEventStatus
from app.models.webhook_event import WebhookEvent
from app.repositories import credential_repository, merchant_repository, webhook_repository
from app.schemas.ops import OpsActorContext
from app.schemas.webhook import WebhookRetryResponse
from app.services import audit_service, webhook_retry_policy

HTTP_TIMEOUT_SECONDS = 10


def deliver_event(
    db: Session,
    event: WebhookEvent,
    now: datetime | None = None,
    http_client=None,
    manual: bool = False,
) -> WebhookRetryResponse:
    attempted_at = now or utc_now()
    merchant = merchant_repository.get_by_id(db, event.merchant_db_id)
    if merchant is None or not merchant.webhook_url:
        event.status = WebhookEventStatus.FAILED
        event.next_retry_at = None
        event.last_attempt_at = attempted_at
        webhook_repository.save_event(db, event)
        db.commit()
        return _response(event, last_attempt_result=None)

    credential = credential_repository.get_active_by_merchant(db, event.merchant_db_id)
    if credential is None:
        last_result = _record_attempt_without_delivery(
            db=db,
            event=event,
            request_url=merchant.webhook_url,
            attempted_at=attempted_at,
            result=DeliveryAttemptResult.FAILED,
            error_message="Active merchant credential was not found.",
        )
        event.status = WebhookEventStatus.FAILED
        event.next_retry_at = None
        webhook_repository.save_event(db, event)
        db.commit()
        return _response(event, last_attempt_result=last_result)

    body = _body_bytes(event.payload_json)
    timestamp = _timestamp(attempted_at)
    signature = _signature(
        secret=credential.secret_key_encrypted,
        timestamp=timestamp,
        event_id=event.event_id,
        body=body,
    )
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event-Id": event.event_id,
        "X-Webhook-Event-Type": event.event_type,
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Signature": signature,
    }

    client_created = http_client is None
    client = http_client or httpx.Client()
    try:
        result, status_code, response_body, error_message = _post_webhook(
            http_client=client,
            url=merchant.webhook_url,
            body=body,
            headers=headers,
        )
    finally:
        if client_created:
            client.close()

    attempt_no = (event.attempt_count or 0) + 1
    webhook_repository.create_delivery_attempt(
        db=db,
        webhook_event_id=event.id,
        attempt_no=attempt_no,
        request_url=merchant.webhook_url,
        request_headers_json=headers,
        request_body_json=event.payload_json,
        response_status_code=status_code,
        response_body_snippet=_snippet(response_body),
        error_message=error_message,
        started_at=attempted_at,
        finished_at=attempted_at,
        result=result,
    )
    event.attempt_count = attempt_no
    event.last_attempt_at = attempted_at
    event.signature = signature
    _apply_delivery_result(event, result, attempted_at, manual=manual)
    webhook_repository.save_event(db, event)
    db.commit()
    return _response(event, last_attempt_result=result)


def deliver_due_webhooks(
    db: Session,
    now: datetime | None = None,
    limit: int = 100,
    http_client=None,
) -> int:
    normalized_now = now or utc_now()
    due_events = webhook_repository.find_due_events(db, normalized_now, limit=limit)
    for event in due_events:
        deliver_event(db, event, now=normalized_now, http_client=http_client)
    return len(due_events)


def manual_retry(
    db: Session,
    event_id: str,
    now: datetime | None = None,
    http_client=None,
    audit_context: OpsActorContext | None = None,
) -> WebhookRetryResponse:
    event = webhook_repository.get_by_event_id(db, event_id)
    if event is None:
        raise AppError(
            error_code="WEBHOOK_EVENT_NOT_FOUND",
            message="Webhook event not found.",
            status_code=404,
            details={"event_id": event_id},
        )
    if event.status != WebhookEventStatus.FAILED:
        raise AppError(
            error_code="WEBHOOK_RETRY_NOT_ALLOWED",
            message="Only failed webhook events can be retried manually.",
            status_code=409,
            details={"event_id": event_id, "status": event.status.value},
        )
    before_state = _event_state(event) if audit_context is not None else None
    response = deliver_event(db, event, now=now, http_client=http_client, manual=True)
    if audit_context is not None:
        audit_service.record_event(
            db=db,
            event_type="WEBHOOK_MANUAL_RETRY",
            entity_type=EntityType.WEBHOOK_EVENT,
            entity_id=event.id,
            actor_type=audit_context.actor_type,
            actor_id=audit_context.actor_id,
            before_state=before_state,
            after_state=_event_state(event),
            reason=audit_context.reason,
        )
        db.commit()
    return response


def _post_webhook(http_client, url: str, body: bytes, headers: dict[str, str]):
    try:
        response = http_client.post(
            url,
            content=body,
            headers=headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        return DeliveryAttemptResult.TIMEOUT, None, None, str(exc)
    except httpx.RequestError as exc:
        return DeliveryAttemptResult.NETWORK_ERROR, None, None, str(exc)

    if 200 <= response.status_code <= 299:
        return DeliveryAttemptResult.SUCCESS, response.status_code, response.text, None
    return DeliveryAttemptResult.FAILED, response.status_code, response.text, None


def _record_attempt_without_delivery(
    db: Session,
    event: WebhookEvent,
    request_url: str,
    attempted_at: datetime,
    result: DeliveryAttemptResult,
    error_message: str,
) -> DeliveryAttemptResult:
    attempt_no = (event.attempt_count or 0) + 1
    webhook_repository.create_delivery_attempt(
        db=db,
        webhook_event_id=event.id,
        attempt_no=attempt_no,
        request_url=request_url,
        request_headers_json={},
        request_body_json=event.payload_json,
        response_status_code=None,
        response_body_snippet=None,
        error_message=error_message,
        started_at=attempted_at,
        finished_at=attempted_at,
        result=result,
    )
    event.attempt_count = attempt_no
    event.last_attempt_at = attempted_at
    return result


def _apply_delivery_result(
    event: WebhookEvent,
    result: DeliveryAttemptResult,
    attempted_at: datetime,
    manual: bool,
) -> None:
    if result == DeliveryAttemptResult.SUCCESS:
        event.status = WebhookEventStatus.DELIVERED
        event.next_retry_at = None
        return

    if manual:
        event.status = WebhookEventStatus.FAILED
        event.next_retry_at = None
        return

    if webhook_retry_policy.has_automatic_attempts_remaining(event.attempt_count):
        event.status = WebhookEventStatus.PENDING
        event.next_retry_at = webhook_retry_policy.next_retry_at(event.attempt_count, attempted_at)
        return

    event.status = WebhookEventStatus.FAILED
    event.next_retry_at = None


def _response(
    event: WebhookEvent,
    last_attempt_result: DeliveryAttemptResult | None,
) -> WebhookRetryResponse:
    return WebhookRetryResponse(
        event_id=event.event_id,
        status=event.status,
        attempt_count=event.attempt_count or 0,
        last_attempt_result=last_attempt_result,
        next_retry_at=event.next_retry_at,
    )


def _signature(secret: str, timestamp: str, event_id: str, body: bytes) -> str:
    return sign_hmac_sha256(secret, f"{timestamp}.{event_id}.{sha256_hex(body)}")


def _timestamp(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _body_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _snippet(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:1000]


def _event_state(event: WebhookEvent) -> dict:
    return {
        "id": str(event.id),
        "event_id": event.event_id,
        "merchant_db_id": str(event.merchant_db_id),
        "event_type": event.event_type,
        "entity_type": event.entity_type.value,
        "entity_id": str(event.entity_id),
        "status": event.status.value,
        "attempt_count": event.attempt_count,
        "next_retry_at": event.next_retry_at.isoformat() if event.next_retry_at else None,
        "last_attempt_at": event.last_attempt_at.isoformat() if event.last_attempt_at else None,
        "payload_json": event.payload_json,
    }
