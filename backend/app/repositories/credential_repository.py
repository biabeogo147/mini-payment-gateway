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
