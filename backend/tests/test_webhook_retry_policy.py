import unittest
from datetime import datetime, timedelta, timezone


class WebhookRetryPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)

    def test_next_retry_at_uses_phase_06_schedule(self) -> None:
        from app.services.webhook_retry_policy import next_retry_at

        self.assertEqual(next_retry_at(1, self.now), self.now + timedelta(minutes=1))
        self.assertEqual(next_retry_at(2, self.now), self.now + timedelta(minutes=5))
        self.assertEqual(next_retry_at(3, self.now), self.now + timedelta(minutes=15))
        self.assertIsNone(next_retry_at(4, self.now))

    def test_automatic_attempts_remaining_stops_after_attempt_4(self) -> None:
        from app.services.webhook_retry_policy import has_automatic_attempts_remaining

        self.assertTrue(has_automatic_attempts_remaining(1))
        self.assertTrue(has_automatic_attempts_remaining(2))
        self.assertTrue(has_automatic_attempts_remaining(3))
        self.assertFalse(has_automatic_attempts_remaining(4))


if __name__ == "__main__":
    unittest.main()
