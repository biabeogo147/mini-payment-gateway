import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.base import Base as _ModelRegistry  # noqa: F401
from app.db.session import SessionLocal
from app.services import expiration_service, webhook_delivery_service
from app.worker import locks
from app.worker.config import WorkerConfig, load_worker_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerJobResult:
    name: str
    enabled: bool
    lock_acquired: bool
    processed: int
    failures: int
    duration_seconds: float


@dataclass(frozen=True)
class WorkerCycleResult:
    payment_expiration: WorkerJobResult
    webhook_delivery: WorkerJobResult


def run_once(
    *,
    db_factory: Callable[[], Session] = SessionLocal,
    config: WorkerConfig | None = None,
    now: datetime | None = None,
    http_client=None,
) -> WorkerCycleResult:
    worker_config = config or load_worker_config()
    cycle_now = now or utc_now()
    if not worker_config.enabled:
        result = WorkerCycleResult(
            payment_expiration=_disabled_result("payment_expiration"),
            webhook_delivery=_disabled_result("webhook_delivery"),
        )
        _write_heartbeat(worker_config, cycle_now)
        return result

    with _session_scope(db_factory) as db:
        payment_result = _run_locked_job(
            db=db,
            name="payment_expiration",
            enabled=worker_config.payment_expiration_enabled,
            lock_key=locks.PAYMENT_EXPIRATION_LOCK_KEY,
            job=lambda: expiration_service.expire_overdue_payments(
                db,
                now=cycle_now,
                limit=worker_config.payment_expiration_batch_limit,
            ),
        )
        webhook_result = _run_locked_job(
            db=db,
            name="webhook_delivery",
            enabled=worker_config.webhook_delivery_enabled,
            lock_key=locks.WEBHOOK_DELIVERY_LOCK_KEY,
            job=lambda: webhook_delivery_service.deliver_due_webhooks(
                db,
                now=cycle_now,
                limit=worker_config.webhook_delivery_batch_limit,
                http_client=http_client,
            ),
        )

    _write_heartbeat(worker_config, cycle_now)
    return WorkerCycleResult(
        payment_expiration=payment_result,
        webhook_delivery=webhook_result,
    )


def run_forever(
    *,
    config: WorkerConfig | None = None,
    db_factory: Callable[[], Session] = SessionLocal,
    stop_event: Event | None = None,
) -> None:
    worker_config = config or load_worker_config()
    event = stop_event or Event()
    if not worker_config.enabled:
        logger.info("worker_disabled")
        return

    logger.info("worker_started interval_seconds=%s", worker_config.loop_interval_seconds)
    while not event.is_set():
        started = time.perf_counter()
        result = run_once(db_factory=db_factory, config=worker_config)
        logger.info(
            "worker_cycle_completed payment_processed=%s webhook_processed=%s duration_seconds=%.3f",
            result.payment_expiration.processed,
            result.webhook_delivery.processed,
            time.perf_counter() - started,
        )
        event.wait(worker_config.loop_interval_seconds)
    logger.info("worker_stopped")


def _run_locked_job(
    *,
    db: Session,
    name: str,
    enabled: bool,
    lock_key: int,
    job: Callable[[], int],
) -> WorkerJobResult:
    started = time.perf_counter()
    if not enabled:
        logger.info("worker_job_disabled job=%s", name)
        return WorkerJobResult(
            name=name,
            enabled=False,
            lock_acquired=False,
            processed=0,
            failures=0,
            duration_seconds=time.perf_counter() - started,
        )

    with locks.advisory_lock(db, lock_key) as acquired:
        if not acquired:
            logger.info("worker_job_lock_contended job=%s", name)
            return WorkerJobResult(
                name=name,
                enabled=True,
                lock_acquired=False,
                processed=0,
                failures=0,
                duration_seconds=time.perf_counter() - started,
            )

        try:
            processed = job()
        except Exception:
            _rollback(db)
            logger.exception("worker_job_failed job=%s", name)
            return WorkerJobResult(
                name=name,
                enabled=True,
                lock_acquired=True,
                processed=0,
                failures=1,
                duration_seconds=time.perf_counter() - started,
            )

    logger.info("worker_job_completed job=%s processed=%s", name, processed)
    return WorkerJobResult(
        name=name,
        enabled=True,
        lock_acquired=True,
        processed=processed,
        failures=0,
        duration_seconds=time.perf_counter() - started,
    )


@contextmanager
def _session_scope(db_factory: Callable[[], Session]):
    db = db_factory()
    try:
        yield db
    finally:
        db.close()


def _disabled_result(name: str) -> WorkerJobResult:
    return WorkerJobResult(
        name=name,
        enabled=False,
        lock_acquired=False,
        processed=0,
        failures=0,
        duration_seconds=0.0,
    )


def _rollback(db: Session) -> None:
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        rollback()


def _write_heartbeat(config: WorkerConfig, now: datetime) -> None:
    if config.heartbeat_path is None:
        return
    heartbeat = Path(config.heartbeat_path)
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text(now.isoformat(), encoding="utf-8")
