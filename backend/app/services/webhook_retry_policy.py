from datetime import datetime, timedelta

MAX_AUTOMATIC_ATTEMPTS = 4

_RETRY_DELAYS_BY_ATTEMPT = {
    1: timedelta(minutes=1),
    2: timedelta(minutes=5),
    3: timedelta(minutes=15),
}


def next_retry_at(attempt_no: int, now: datetime) -> datetime | None:
    delay = _RETRY_DELAYS_BY_ATTEMPT.get(attempt_no)
    if delay is None:
        return None
    return now + delay


def has_automatic_attempts_remaining(attempt_no: int) -> bool:
    return attempt_no < MAX_AUTOMATIC_ATTEMPTS
