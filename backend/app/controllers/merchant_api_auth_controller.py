from fastapi import APIRouter, Depends

from app.controllers.deps import get_authenticated_merchant
from app.schemas.auth import AuthenticatedMerchant, MerchantApiAuthVerificationResponse

router = APIRouter(prefix="/v1/merchant/auth", tags=["merchant-api-auth"])


@router.get("/verify", response_model=MerchantApiAuthVerificationResponse)
def verify_merchant_api_auth(
    authenticated_merchant: AuthenticatedMerchant = Depends(get_authenticated_merchant),
) -> MerchantApiAuthVerificationResponse:
    return MerchantApiAuthVerificationResponse(
        authenticated=True,
        merchant_id=authenticated_merchant.merchant_id,
    )
