from decimal import Decimal


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
