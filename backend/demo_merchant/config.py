from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoMerchantSettings:
    gateway_base_url: str = "http://127.0.0.1:8000"
    provider_id: str = "simulator"
    provider_callback_secret: str = "dev-insecure-provider-callback-secret-change-me"
    demo_mode: bool = True
    webhook_max_age_seconds: int = 300
    request_timeout_seconds: int = 10

    @classmethod
    def from_env(cls) -> "DemoMerchantSettings":
        provider_id = os.getenv("DEMO_PROVIDER_ID", "simulator").strip().lower()
        return cls(
            gateway_base_url=os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            provider_id=provider_id,
            provider_callback_secret=_provider_callback_secret(provider_id),
            demo_mode=_env_bool("DEMO_MODE", True),
            webhook_max_age_seconds=int(os.getenv("DEMO_WEBHOOK_MAX_AGE_SECONDS", "300")),
            request_timeout_seconds=int(os.getenv("DEMO_REQUEST_TIMEOUT_SECONDS", "10")),
        )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _provider_callback_secret(provider_id: str) -> str:
    explicit_secret = os.getenv("DEMO_PROVIDER_CALLBACK_SECRET")
    if explicit_secret:
        return explicit_secret

    mapping = os.getenv("PROVIDER_CALLBACK_SECRETS")
    if mapping is None:
        return "dev-insecure-provider-callback-secret-change-me"

    for item in mapping.split(","):
        mapped_provider, separator, secret = item.strip().partition("=")
        if separator and mapped_provider.strip().lower() == provider_id and secret:
            return secret

    raise ValueError(f"No callback secret configured for provider '{provider_id}'.")
