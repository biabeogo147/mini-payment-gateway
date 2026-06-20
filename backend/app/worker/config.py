import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerConfig:
    enabled: bool
    loop_interval_seconds: int
    payment_expiration_batch_limit: int
    webhook_delivery_batch_limit: int
    payment_expiration_enabled: bool
    webhook_delivery_enabled: bool
    heartbeat_path: str | None


def load_worker_config() -> WorkerConfig:
    return WorkerConfig(
        enabled=_env_bool("WORKER_ENABLED", True),
        loop_interval_seconds=_env_int("WORKER_LOOP_INTERVAL_SECONDS", 15),
        payment_expiration_batch_limit=_env_int("PAYMENT_EXPIRATION_BATCH_LIMIT", 200),
        webhook_delivery_batch_limit=_env_int("WEBHOOK_DELIVERY_BATCH_LIMIT", 100),
        payment_expiration_enabled=_env_bool("WORKER_PAYMENT_EXPIRATION_ENABLED", True),
        webhook_delivery_enabled=_env_bool("WORKER_WEBHOOK_DELIVERY_ENABLED", True),
        heartbeat_path=_env_optional_str("WORKER_HEARTBEAT_PATH"),
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


def _env_optional_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value
