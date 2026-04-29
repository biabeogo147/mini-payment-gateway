from app.core.errors import AppError
from app.models.enums import MerchantStatus
from app.models.merchant import Merchant


def assert_can_create_payment(merchant: Merchant) -> None:
    _assert_active_for_merchant_api(merchant)


def assert_can_create_refund(merchant: Merchant) -> None:
    _assert_active_for_merchant_api(merchant)


def assert_can_receive_ops_update(merchant: Merchant) -> None:
    return None


def _assert_active_for_merchant_api(merchant: Merchant) -> None:
    if merchant.status == MerchantStatus.ACTIVE:
        return
    raise AppError(
        error_code="MERCHANT_NOT_ACTIVE",
        message="Merchant is not active.",
        status_code=403,
        details={"merchant_status": merchant.status.value},
    )
