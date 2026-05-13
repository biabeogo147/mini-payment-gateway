import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.internal_auth import (
    build_internal_session_token,
    hash_password,
    parse_internal_session_token,
    verify_password,
)


class InternalAuthCoreTest(unittest.TestCase):
    def test_hash_password_round_trip(self) -> None:
        password_hash = hash_password("super-secret-password")

        self.assertTrue(verify_password("super-secret-password", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))

    def test_build_and_parse_internal_session_token(self) -> None:
        now = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
        user_id = uuid4()

        token = build_internal_session_token(
            user_id=user_id,
            version="session-version",
            secret="test-secret",
            now=now,
            ttl_seconds=3600,
        )

        claims = parse_internal_session_token(token, secret="test-secret", now=now + timedelta(minutes=5))

        self.assertEqual(claims.user_id, str(user_id))
        self.assertEqual(claims.version, "session-version")
        self.assertEqual(claims.expires_at, now + timedelta(hours=1))

    def test_parse_internal_session_token_rejects_expired_token(self) -> None:
        now = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
        token = build_internal_session_token(
            user_id=uuid4(),
            version="expired-version",
            secret="test-secret",
            now=now,
            ttl_seconds=60,
        )

        with self.assertRaises(ValueError):
            parse_internal_session_token(
                token,
                secret="test-secret",
                now=now + timedelta(minutes=2),
            )


if __name__ == "__main__":
    unittest.main()
