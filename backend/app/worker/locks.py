from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

PAYMENT_EXPIRATION_LOCK_KEY = 73312001
WEBHOOK_DELIVERY_LOCK_KEY = 73312002


@contextmanager
def advisory_lock(db: Session, key: int) -> Iterator[bool]:
    acquired = bool(db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar())
    try:
        yield acquired
    finally:
        if acquired:
            db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
