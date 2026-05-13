import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from uuid import UUID

from app.models.internal_user import InternalUser

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 240000
SESSION_TOKEN_VERSION = 1


@dataclass(frozen=True)
class InternalSessionClaims:
    user_id: str
    expires_at: datetime
    version: str


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    ).hex()
    return hmac.compare_digest(candidate, digest_hex)


def build_internal_session_token(
    *,
    user_id: UUID | str,
    version: str,
    secret: str,
    now: datetime,
    ttl_seconds: int,
) -> str:
    payload = {
        "v": SESSION_TOKEN_VERSION,
        "sub": str(user_id),
        "ver": version,
        "exp": int(_ensure_utc(now).timestamp()) + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def parse_internal_session_token(
    token: str,
    *,
    secret: str,
    now: datetime,
) -> InternalSessionClaims:
    try:
        payload_encoded, signature_encoded = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed session token.") from exc

    payload_bytes = _b64url_decode(payload_encoded)
    expected_signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    provided_signature = _b64url_decode(signature_encoded)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise ValueError("Invalid session token signature.")

    payload = json.loads(payload_bytes.decode("utf-8"))
    if payload.get("v") != SESSION_TOKEN_VERSION:
        raise ValueError("Unsupported session token version.")

    expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    if _ensure_utc(now) >= expires_at:
        raise ValueError("Session token expired.")

    version = payload.get("ver")
    if not isinstance(version, str) or not version:
        raise ValueError("Missing session token version fingerprint.")

    return InternalSessionClaims(
        user_id=str(payload["sub"]),
        expires_at=expires_at,
        version=version,
    )


def internal_session_version(user: InternalUser) -> str:
    source = "|".join(
        [
            user.password_hash or "",
            user.role.value,
            user.status.value,
        ]
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
