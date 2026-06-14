from functools import lru_cache
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    internal_auth_secret: str
    internal_auth_cookie_name: str
    internal_auth_ttl_seconds: int
    internal_auth_cookie_secure: bool
    merchant_auth_secret: str
    merchant_auth_cookie_name: str
    merchant_auth_ttl_seconds: int
    merchant_auth_cookie_secure: bool


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/mini_payment_gateway",
        ),
        internal_auth_secret=os.getenv(
            "INTERNAL_AUTH_SECRET",
            "dev-insecure-internal-auth-secret-change-me",
        ),
        internal_auth_cookie_name=os.getenv(
            "INTERNAL_AUTH_COOKIE_NAME",
            "mini_payment_gateway_internal_session",
        ),
        internal_auth_ttl_seconds=_env_int("INTERNAL_AUTH_TTL_SECONDS", 12 * 60 * 60),
        internal_auth_cookie_secure=_env_bool("INTERNAL_AUTH_COOKIE_SECURE", False),
        merchant_auth_secret=os.getenv(
            "MERCHANT_AUTH_SECRET",
            "dev-insecure-merchant-auth-secret-change-me",
        ),
        merchant_auth_cookie_name=os.getenv(
            "MERCHANT_AUTH_COOKIE_NAME",
            "mini_payment_gateway_merchant_session",
        ),
        merchant_auth_ttl_seconds=_env_int("MERCHANT_AUTH_TTL_SECONDS", 12 * 60 * 60),
        merchant_auth_cookie_secure=_env_bool("MERCHANT_AUTH_COOKIE_SECURE", False),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)
