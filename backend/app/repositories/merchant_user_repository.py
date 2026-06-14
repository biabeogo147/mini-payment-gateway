from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.merchant_user import MerchantUser


def get_by_email(db: Session, email: str) -> MerchantUser | None:
    return db.scalar(
        select(MerchantUser)
        .options(joinedload(MerchantUser.merchant))
        .where(func.lower(MerchantUser.email) == email.strip().lower())
    )


def get_by_id(db: Session, user_id) -> MerchantUser | None:
    return db.scalar(
        select(MerchantUser)
        .options(joinedload(MerchantUser.merchant))
        .where(MerchantUser.id == user_id)
    )


def get_by_merchant_and_id(db: Session, *, merchant_db_id, user_id) -> MerchantUser | None:
    return db.scalar(
        select(MerchantUser)
        .options(joinedload(MerchantUser.merchant))
        .where(MerchantUser.merchant_db_id == merchant_db_id, MerchantUser.id == user_id)
    )


def get_by_merchant_and_email(db: Session, *, merchant_db_id, email: str) -> MerchantUser | None:
    return db.scalar(
        select(MerchantUser)
        .options(joinedload(MerchantUser.merchant))
        .where(
            MerchantUser.merchant_db_id == merchant_db_id,
            func.lower(MerchantUser.email) == email.strip().lower(),
        )
    )


def list_by_merchant(db: Session, merchant_db_id) -> list[MerchantUser]:
    return list(
        db.scalars(
            select(MerchantUser)
            .options(joinedload(MerchantUser.merchant))
            .where(MerchantUser.merchant_db_id == merchant_db_id)
            .order_by(MerchantUser.created_at.asc())
        ).all()
    )


def create(
    db: Session,
    *,
    merchant_db_id,
    email: str,
    full_name: str,
    role,
    status,
    password_hash: str,
) -> MerchantUser:
    user = MerchantUser(
        merchant_db_id=merchant_db_id,
        email=email.strip(),
        full_name=full_name,
        role=role,
        status=status,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()
    user = get_by_id(db, user.id) or user
    return user


def save(db: Session, user: MerchantUser) -> MerchantUser:
    db.add(user)
    db.flush()
    return get_by_id(db, user.id) or user
