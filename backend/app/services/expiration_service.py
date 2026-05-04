from datetime import datetime

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.repositories import payment_repository
from app.services import webhook_event_factory
from app.services.payment_state_machine import mark_expired


def expire_overdue_payments(
    db: Session,
    now: datetime | None = None,
) -> int:
    normalized_now = now or utc_now()
    overdue_payments = payment_repository.find_overdue_pending(db, normalized_now)
    for payment in overdue_payments:
        mark_expired(payment)
        payment_repository.save(db, payment)
        webhook_event_factory.create_payment_event_if_needed(db, payment, now=normalized_now)
    db.commit()
    return len(overdue_payments)
