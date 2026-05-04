from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import ActorType, EntityType
from app.repositories import audit_repository

MASKED_SECRET = "***"
SECRET_KEYS = {"secret_key", "secret_key_encrypted"}


def record_event(
    db: Session,
    event_type: str,
    entity_type: EntityType,
    entity_id: UUID,
    actor_type: ActorType,
    actor_id: UUID | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    reason: str | None = None,
) -> AuditLog:
    return audit_repository.create(
        db=db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_type=actor_type,
        actor_id=actor_id,
        before_state_json=_sanitize_state(before_state),
        after_state_json=_sanitize_state(after_state),
        reason=reason,
    )


def _sanitize_state(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            key: MASKED_SECRET if key in SECRET_KEYS else _sanitize_state(item)
            for key, item in deepcopy(value).items()
        }
    if isinstance(value, list):
        return [_sanitize_state(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_state(item) for item in value)
    return value
