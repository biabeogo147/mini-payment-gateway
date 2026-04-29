from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import build_signing_string, constant_time_equal, sign_hmac_sha256
from app.core.time import utc_now
from app.repositories import credential_repository, merchant_repository
from app.schemas.auth import AuthenticatedMerchant

TIMESTAMP_WINDOW_SECONDS = 5 * 60

_HEADER_MERCHANT_ID = "x-merchant-id"
_HEADER_ACCESS_KEY = "x-access-key"
_HEADER_SIGNATURE = "x-signature"
_HEADER_TIMESTAMP = "x-timestamp"


def authenticate_merchant_request(
    db: Session,
    method: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
    now: datetime | None = None,
) -> AuthenticatedMerchant:
    normalized_headers = _normalize_headers(headers)
    merchant_id = _required_header(normalized_headers, _HEADER_MERCHANT_ID)
    access_key = _required_header(normalized_headers, _HEADER_ACCESS_KEY)
    signature = _required_header(normalized_headers, _HEADER_SIGNATURE)
    timestamp = _required_header(normalized_headers, _HEADER_TIMESTAMP)

    _assert_timestamp_fresh(timestamp, now or utc_now())

    merchant = merchant_repository.get_by_public_merchant_id(db, merchant_id)
    if merchant is None:
        raise AppError(
            error_code="AUTH_INVALID_MERCHANT",
            message="Merchant authentication failed.",
            status_code=401,
        )

    credential = credential_repository.get_active_by_merchant_and_access_key(
        db,
        merchant.id,
        access_key,
    )
    if credential is None:
        raise AppError(
            error_code="AUTH_INVALID_CREDENTIAL",
            message="Merchant authentication failed.",
            status_code=401,
        )

    signing_string = build_signing_string(timestamp, method, path, body)
    expected_signature = sign_hmac_sha256(_decrypt_secret(credential.secret_key_encrypted), signing_string)
    if not constant_time_equal(signature, expected_signature):
        raise AppError(
            error_code="AUTH_INVALID_SIGNATURE",
            message="Merchant authentication failed.",
            status_code=401,
        )

    return AuthenticatedMerchant(
        merchant=merchant,
        credential=credential,
        merchant_id=merchant.merchant_id,
    )


def _normalize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def _required_header(headers: Mapping[str, str], header_name: str) -> str:
    value = headers.get(header_name)
    if value is None or value == "":
        raise AppError(
            error_code="AUTH_MISSING_HEADER",
            message=f"Missing required header: {header_name}",
            status_code=401,
            details={"header": header_name},
        )
    return value


def _assert_timestamp_fresh(timestamp_value: str, now: datetime) -> None:
    try:
        timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError(
            error_code="AUTH_TIMESTAMP_EXPIRED",
            message="Request timestamp is invalid or expired.",
            status_code=401,
        ) from exc

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    normalized_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    delta_seconds = abs((normalized_now - timestamp).total_seconds())
    if delta_seconds > TIMESTAMP_WINDOW_SECONDS:
        raise AppError(
            error_code="AUTH_TIMESTAMP_EXPIRED",
            message="Request timestamp is invalid or expired.",
            status_code=401,
        )


def _decrypt_secret(secret_key_encrypted: str) -> str:
    return secret_key_encrypted
