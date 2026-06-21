from dataclasses import dataclass

from pydantic import BaseModel

from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential


@dataclass(frozen=True)
class AuthenticatedMerchant:
    merchant: Merchant
    credential: MerchantCredential
    merchant_id: str


class MerchantApiAuthVerificationResponse(BaseModel):
    authenticated: bool
    merchant_id: str
