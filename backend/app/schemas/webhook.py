from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer

from app.models.enums import DeliveryAttemptResult, WebhookEventStatus


class WebhookRetryResponse(BaseModel):
    event_id: str
    status: WebhookEventStatus
    attempt_count: int
    last_attempt_result: DeliveryAttemptResult | None = None
    next_retry_at: datetime | None = None

    @field_serializer("next_retry_at")
    def serialize_next_retry_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
