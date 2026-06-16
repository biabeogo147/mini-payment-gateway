import os
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch


class WorkerConfigTest(unittest.TestCase):
    def test_config_from_env_parses_worker_flags_and_limits(self) -> None:
        from app.worker.config import load_worker_config

        env = {
            "WORKER_ENABLED": "true",
            "WORKER_LOOP_INTERVAL_SECONDS": "7",
            "PAYMENT_EXPIRATION_BATCH_LIMIT": "11",
            "WEBHOOK_DELIVERY_BATCH_LIMIT": "13",
            "WORKER_PAYMENT_EXPIRATION_ENABLED": "false",
            "WORKER_WEBHOOK_DELIVERY_ENABLED": "true",
            "WORKER_HEARTBEAT_PATH": "tmp/worker.heartbeat",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_worker_config()

        self.assertTrue(config.enabled)
        self.assertEqual(config.loop_interval_seconds, 7)
        self.assertEqual(config.payment_expiration_batch_limit, 11)
        self.assertEqual(config.webhook_delivery_batch_limit, 13)
        self.assertFalse(config.payment_expiration_enabled)
        self.assertTrue(config.webhook_delivery_enabled)
        self.assertEqual(config.heartbeat_path, "tmp/worker.heartbeat")


class WorkerRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        self.db = _FakeSession()

    def test_run_once_expires_payments_and_delivers_due_webhooks_under_locks(self) -> None:
        from app.worker.config import WorkerConfig
        from app.worker.runner import run_once

        config = WorkerConfig(
            enabled=True,
            loop_interval_seconds=15,
            payment_expiration_batch_limit=2,
            webhook_delivery_batch_limit=3,
            payment_expiration_enabled=True,
            webhook_delivery_enabled=True,
            heartbeat_path=None,
        )

        with patch(
            "app.worker.runner.expiration_service.expire_overdue_payments",
            return_value=2,
        ) as expire, patch(
            "app.worker.runner.webhook_delivery_service.deliver_due_webhooks",
            return_value=3,
        ) as deliver, patch(
            "app.worker.runner.locks.advisory_lock",
            side_effect=[_lock(True), _lock(True)],
        ):
            result = run_once(
                db_factory=lambda: self.db,
                config=config,
                now=self.now,
                http_client="client",
            )

        self.assertEqual(result.payment_expiration.processed, 2)
        self.assertEqual(result.webhook_delivery.processed, 3)
        expire.assert_called_once_with(self.db, now=self.now, limit=2)
        deliver.assert_called_once_with(self.db, now=self.now, limit=3, http_client="client")
        self.assertTrue(self.db.closed)

    def test_run_once_skips_jobs_when_advisory_locks_are_contended(self) -> None:
        from app.worker.config import WorkerConfig
        from app.worker.runner import run_once

        config = WorkerConfig(
            enabled=True,
            loop_interval_seconds=15,
            payment_expiration_batch_limit=2,
            webhook_delivery_batch_limit=3,
            payment_expiration_enabled=True,
            webhook_delivery_enabled=True,
            heartbeat_path=None,
        )

        with patch(
            "app.worker.runner.expiration_service.expire_overdue_payments",
        ) as expire, patch(
            "app.worker.runner.webhook_delivery_service.deliver_due_webhooks",
        ) as deliver, patch(
            "app.worker.runner.locks.advisory_lock",
            side_effect=[_lock(False), _lock(False)],
        ):
            result = run_once(db_factory=lambda: self.db, config=config, now=self.now)

        self.assertFalse(result.payment_expiration.lock_acquired)
        self.assertFalse(result.webhook_delivery.lock_acquired)
        expire.assert_not_called()
        deliver.assert_not_called()

    def test_run_once_rolls_back_failed_job_and_continues(self) -> None:
        from app.worker.config import WorkerConfig
        from app.worker.runner import run_once

        config = WorkerConfig(
            enabled=True,
            loop_interval_seconds=15,
            payment_expiration_batch_limit=2,
            webhook_delivery_batch_limit=3,
            payment_expiration_enabled=True,
            webhook_delivery_enabled=True,
            heartbeat_path=None,
        )

        with patch(
            "app.worker.runner.expiration_service.expire_overdue_payments",
            side_effect=RuntimeError("database unavailable"),
        ), patch(
            "app.worker.runner.webhook_delivery_service.deliver_due_webhooks",
            return_value=1,
        ), patch(
            "app.worker.runner.locks.advisory_lock",
            side_effect=[_lock(True), _lock(True)],
        ), self.assertLogs("app.worker.runner", level="ERROR"):
            result = run_once(db_factory=lambda: self.db, config=config, now=self.now)

        self.assertEqual(result.payment_expiration.failures, 1)
        self.assertEqual(result.webhook_delivery.processed, 1)
        self.assertEqual(self.db.rollback_count, 1)


class WorkerLocksTest(unittest.TestCase):
    def test_advisory_lock_acquires_and_releases_session_lock(self) -> None:
        from app.worker.locks import advisory_lock

        db = _LockDb([True, True])
        with advisory_lock(db, 12345) as acquired:
            self.assertTrue(acquired)

        self.assertEqual(db.statements[0][0], "SELECT pg_try_advisory_lock(:key)")
        self.assertEqual(db.statements[0][1], {"key": 12345})
        self.assertEqual(db.statements[1][0], "SELECT pg_advisory_unlock(:key)")
        self.assertEqual(db.statements[1][1], {"key": 12345})

    def test_advisory_lock_does_not_release_when_lock_not_acquired(self) -> None:
        from app.worker.locks import advisory_lock

        db = _LockDb([False])
        with advisory_lock(db, 12345) as acquired:
            self.assertFalse(acquired)

        self.assertEqual(len(db.statements), 1)
        self.assertEqual(db.statements[0][0], "SELECT pg_try_advisory_lock(:key)")


@contextmanager
def _lock(acquired: bool):
    yield acquired


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.rollback_count = 0

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        self.rollback_count += 1


class _ScalarResult:
    def __init__(self, value: bool) -> None:
        self.value = value

    def scalar(self) -> bool:
        return self.value


class _LockDb:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.statements = []

    def execute(self, statement, params):
        self.statements.append((str(statement), params))
        return _ScalarResult(self.results.pop(0))


if __name__ == "__main__":
    unittest.main()
