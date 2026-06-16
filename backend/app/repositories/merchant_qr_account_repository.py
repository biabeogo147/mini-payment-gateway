from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MerchantQrAccountStatus, QrProvider
from app.models.merchant_qr_account import MerchantQrAccount


def get_by_id(db: Session, qr_account_id: UUID | str) -> MerchantQrAccount | None:
    normalized_id = qr_account_id
    if isinstance(qr_account_id, str):
        try:
            normalized_id = UUID(qr_account_id)
        except ValueError:
            return None
    return db.scalar(select(MerchantQrAccount).where(MerchantQrAccount.id == normalized_id))


def get_active_by_merchant_provider(
    db: Session,
    merchant_db_id: UUID,
    provider: QrProvider,
) -> MerchantQrAccount | None:
    return db.scalar(
        select(MerchantQrAccount).where(
            MerchantQrAccount.merchant_db_id == merchant_db_id,
            MerchantQrAccount.provider == provider,
            MerchantQrAccount.status == MerchantQrAccountStatus.ACTIVE,
        )
    )


def list_by_merchant(db: Session, merchant_db_id: UUID) -> list[MerchantQrAccount]:
    return list(
        db.scalars(
            select(MerchantQrAccount)
            .where(MerchantQrAccount.merchant_db_id == merchant_db_id)
            .order_by(MerchantQrAccount.created_at.desc())
        ).all()
    )


def create(
    db: Session,
    *,
    merchant_db_id: UUID,
    provider: QrProvider,
    bank_code: str,
    bank_bin: str,
    account_number: str,
    account_name: str,
    template: str,
    status: MerchantQrAccountStatus,
) -> MerchantQrAccount:
    qr_account = MerchantQrAccount(
        merchant_db_id=merchant_db_id,
        provider=provider,
        bank_code=bank_code,
        bank_bin=bank_bin,
        account_number=account_number,
        account_name=account_name,
        template=template,
        status=status,
    )
    db.add(qr_account)
    db.flush()
    return qr_account


def save(db: Session, qr_account: MerchantQrAccount) -> MerchantQrAccount:
    db.add(qr_account)
    db.flush()
    return qr_account
