from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import InternalUserRole, InternalUserStatus
from app.models.internal_user import InternalUser


def count_password_enabled_users(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(InternalUser.id)).where(InternalUser.password_hash.is_not(None))
        )
        or 0
    )


def get_by_email(db: Session, email: str) -> InternalUser | None:
    return db.scalar(
        select(InternalUser).where(func.lower(InternalUser.email) == email.strip().lower())
    )


def get_by_id(db: Session, user_id) -> InternalUser | None:
    return db.scalar(select(InternalUser).where(InternalUser.id == user_id))


def list_users(db: Session) -> list[InternalUser]:
    return list(db.scalars(select(InternalUser).order_by(InternalUser.created_at.asc())).all())


def count_active_admins(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(InternalUser.id)).where(
                InternalUser.role == InternalUserRole.ADMIN,
                InternalUser.status == InternalUserStatus.ACTIVE,
                InternalUser.password_hash.is_not(None),
            )
        )
        or 0
    )


def create(
    db: Session,
    *,
    email: str,
    full_name: str,
    role,
    status,
    password_hash: str,
) -> InternalUser:
    user = InternalUser(
        email=email.strip(),
        full_name=full_name,
        role=role,
        status=status,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()
    return user


def save(db: Session, user: InternalUser) -> InternalUser:
    db.add(user)
    db.flush()
    return user
