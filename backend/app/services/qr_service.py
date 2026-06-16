import base64
import re
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

import qrcode
from vietnam_qr_pay import FieldID, QRPay, QRProviderGUID, VietQRService

from app.models.merchant_qr_account import MerchantQrAccount


@dataclass(frozen=True)
class GeneratedQr:
    qr_content: str
    qr_image_base64: str


def generate_qr_content(
    merchant_id: str,
    transaction_id: str,
    amount: Decimal,
    currency: str,
) -> str:
    normalized_amount = amount.quantize(Decimal("0.01"))
    return (
        "MINI_GATEWAY"
        f"|merchant_id={merchant_id}"
        f"|transaction_id={transaction_id}"
        f"|amount={normalized_amount}"
        f"|currency={currency}"
    )


def generate_qr_reference(transaction_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]", "", transaction_id).upper()
    if normalized.startswith("PAY"):
        normalized = normalized[3:]
    return f"P{normalized[:12]}"


def generate_vietqr_payment_qr(
    *,
    qr_account: MerchantQrAccount,
    amount: Decimal,
    qr_reference: str,
) -> GeneratedQr:
    qr = QRPay()
    qr.provider.field_id = FieldID.VIETQR.value
    qr.provider.guid = QRProviderGUID.VIETQR.value
    qr.provider.service = VietQRService.BY_ACCOUNT_NUMBER.value
    qr.consumer.bank_bin = qr_account.bank_bin
    qr.consumer.bank_number = qr_account.account_number
    qr.amount = str(int(amount))
    qr.currency = "704"
    qr.nation = "VN"
    qr.additional_data.purpose = qr_reference
    qr_content = qr.build()
    return GeneratedQr(
        qr_content=qr_content,
        qr_image_base64=_png_data_url(qr_content),
    )


def _png_data_url(qr_content: str) -> str:
    image = qrcode.make(qr_content)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
