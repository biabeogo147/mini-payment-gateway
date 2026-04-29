from dataclasses import dataclass

from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential


@dataclass(frozen=True)
class AuthenticatedMerchant:
    merchant: Merchant
    credential: MerchantCredential
    merchant_id: str
