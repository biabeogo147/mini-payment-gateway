from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MerchantStatus
from app.models.merchant import Merchant


def get_by_id(db: Session, merchant_db_id: UUID) -> Merchant | None:
    return db.scalar(select(Merchant).where(Merchant.id == merchant_db_id))


def get_by_public_merchant_id(db: Session, merchant_id: str) -> Merchant | None:
    return db.execute(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).scalar_one_or_none()


def create(
    db: Session,
    merchant_id: str,
    merchant_name: str,
    legal_name: str | None,
    contact_name: str | None,
    contact_email: str,
    contact_phone: str | None,
    webhook_url: str | None,
    settlement_account_name: str | None,
    settlement_account_number: str | None,
    settlement_bank_code: str | None,
) -> Merchant:
    merchant = Merchant(
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        legal_name=legal_name,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        webhook_url=webhook_url,
        settlement_account_name=settlement_account_name,
        settlement_account_number=settlement_account_number,
        settlement_bank_code=settlement_bank_code,
        status=MerchantStatus.PENDING_REVIEW,
    )
    db.add(merchant)
    db.flush()
    return merchant


def save(db: Session, merchant: Merchant) -> Merchant:
    db.add(merchant)
    db.flush()
    return merchant
