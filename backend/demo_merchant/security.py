from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any


class WebhookAuthError(ValueError):
    pass


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def build_merchant_headers(
    *,
    merchant_id: str,
    access_key: str,
    secret: str,
    method: str,
    path: str,
    body: bytes,
    now: datetime,
) -> dict[str, str]:
    timestamp = _timestamp(now)
    signature = _sign(secret, f"{timestamp}.{method.upper()}.{path}.{_sha256(body)}")
    return {
        "Content-Type": "application/json",
        "X-Merchant-Id": merchant_id,
        "X-Access-Key": access_key,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    }


def build_provider_headers(
    *,
    provider_id: str,
    secret: str,
    method: str,
    path: str,
    body: bytes,
    now: datetime,
) -> dict[str, str]:
    timestamp = _timestamp(now)
    signature = _sign(secret, f"{timestamp}.{method.upper()}.{path}.{_sha256(body)}")
    return {
        "Content-Type": "application/json",
        "X-Provider-Id": provider_id,
        "X-Provider-Timestamp": timestamp,
        "X-Provider-Signature": signature,
    }


def verify_webhook_signature(
    *,
    secret: str,
    event_id: str | None,
    timestamp: str | None,
    signature: str | None,
    body: bytes,
    now: datetime,
    max_age_seconds: int = 300,
) -> None:
    if not event_id or not timestamp or not signature:
        raise WebhookAuthError("Missing webhook authentication header.")
    received_at = _parse_timestamp(timestamp)
    normalized_now = _as_utc(now)
    if abs((normalized_now - received_at).total_seconds()) > max_age_seconds:
        raise WebhookAuthError("Webhook timestamp is outside the allowed window.")
    expected = _sign(secret, f"{timestamp}.{event_id}.{_sha256(body)}")
    if not hmac.compare_digest(expected, signature):
        raise WebhookAuthError("Webhook signature is invalid.")


def _sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _timestamp(value: datetime) -> str:
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WebhookAuthError("Webhook timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise WebhookAuthError("Webhook timestamp must include timezone information.")
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
