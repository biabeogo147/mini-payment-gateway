from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.merchant import Merchant


def get_by_id(db: Session, merchant_db_id: UUID) -> Merchant | None:
    return db.scalar(select(Merchant).where(Merchant.id == merchant_db_id))


def get_by_public_merchant_id(db: Session, merchant_id: str) -> Merchant | None:
    return db.execute(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).scalar_one_or_none()
