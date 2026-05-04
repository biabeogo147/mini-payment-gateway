from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CredentialStatus
from app.models.merchant_credential import MerchantCredential


def get_active_by_merchant_and_access_key(
    db: Session,
    merchant_db_id: UUID,
    access_key: str,
) -> MerchantCredential | None:
    return db.execute(
        select(MerchantCredential).where(
            MerchantCredential.merchant_db_id == merchant_db_id,
            MerchantCredential.access_key == access_key,
            MerchantCredential.status == CredentialStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def get_active_by_merchant(
    db: Session,
    merchant_db_id: UUID,
) -> MerchantCredential | None:
    return db.execute(
        select(MerchantCredential).where(
            MerchantCredential.merchant_db_id == merchant_db_id,
            MerchantCredential.status == CredentialStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def create(
    db: Session,
    merchant_db_id: UUID,
    access_key: str,
    secret_key: str,
    now=None,
) -> MerchantCredential:
    credential = MerchantCredential(
        merchant_db_id=merchant_db_id,
        access_key=access_key,
        secret_key_encrypted=secret_key,
        secret_key_last4=secret_key[-4:],
        status=CredentialStatus.ACTIVE,
    )
    db.add(credential)
    db.flush()
    return credential


def save(db: Session, credential: MerchantCredential) -> MerchantCredential:
    db.add(credential)
    db.flush()
    return credential
