import hashlib
import hmac


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_signing_string(timestamp: str, method: str, path: str, body: bytes) -> str:
    return f"{timestamp}.{method.upper()}.{path}.{sha256_hex(body)}"


def sign_hmac_sha256(secret: str, message: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
