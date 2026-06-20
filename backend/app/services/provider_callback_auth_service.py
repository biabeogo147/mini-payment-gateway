from collections.abc import Mapping
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import build_signing_string, constant_time_equal, sign_hmac_sha256
from app.core.time import utc_now

TIMESTAMP_WINDOW_SECONDS = 5 * 60

_HEADER_PROVIDER_ID = "x-provider-id"
_HEADER_SIGNATURE = "x-provider-signature"
_HEADER_TIMESTAMP = "x-provider-timestamp"


def authenticate_provider_callback_request(
    method: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
    now: datetime | None = None,
    settings: Settings | None = None,
) -> str:
    normalized_headers = _normalize_headers(headers)
    provider_id = _required_header(normalized_headers, _HEADER_PROVIDER_ID).lower()
    signature = _required_header(normalized_headers, _HEADER_SIGNATURE)
    timestamp = _required_header(normalized_headers, _HEADER_TIMESTAMP)

    _assert_timestamp_fresh(timestamp, now or utc_now())

    secret = (settings or get_settings()).provider_callback_secrets.get(provider_id)
    if secret is None:
        raise AppError(
            error_code="PROVIDER_AUTH_UNKNOWN_PROVIDER",
            message="Provider callback authentication failed.",
            status_code=401,
        )

    signing_string = build_signing_string(timestamp, method, path, body)
    expected_signature = sign_hmac_sha256(secret, signing_string)
    if not constant_time_equal(signature, expected_signature):
        raise AppError(
            error_code="PROVIDER_AUTH_INVALID_SIGNATURE",
            message="Provider callback authentication failed.",
            status_code=401,
        )

    return provider_id


def _normalize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def _required_header(headers: Mapping[str, str], header_name: str) -> str:
    value = headers.get(header_name)
    if value is None or value == "":
        raise AppError(
            error_code="PROVIDER_AUTH_MISSING_HEADER",
            message=f"Missing required provider callback header: {header_name}",
            status_code=401,
            details={"header": header_name},
        )
    return value


def _assert_timestamp_fresh(timestamp_value: str, now: datetime) -> None:
    try:
        timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError(
            error_code="PROVIDER_AUTH_TIMESTAMP_EXPIRED",
            message="Provider callback timestamp is invalid or expired.",
            status_code=401,
        ) from exc

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    normalized_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    delta_seconds = abs((normalized_now - timestamp).total_seconds())
    if delta_seconds > TIMESTAMP_WINDOW_SECONDS:
        raise AppError(
            error_code="PROVIDER_AUTH_TIMESTAMP_EXPIRED",
            message="Provider callback timestamp is invalid or expired.",
            status_code=401,
        )
