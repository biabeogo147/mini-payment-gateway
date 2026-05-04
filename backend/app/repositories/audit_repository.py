from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import ActorType, EntityType
from app.models import internal_user as _internal_user  # noqa: F401


def create(
    db: Session,
    event_type: str,
    entity_type: EntityType,
    entity_id: UUID,
    actor_type: ActorType,
    actor_id: UUID | None = None,
    before_state_json: dict | None = None,
    after_state_json: dict | None = None,
    reason: str | None = None,
) -> AuditLog:
    log = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_type=actor_type,
        actor_id=actor_id,
        before_state_json=before_state_json,
        after_state_json=after_state_json,
        reason=reason,
    )
    db.add(log)
    db.flush()
    return log
