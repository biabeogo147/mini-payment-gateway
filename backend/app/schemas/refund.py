from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RefundStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.refund_transaction import RefundTransaction


class CreateRefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_transaction_id: str | None = Field(default=None, min_length=1, max_length=64)
    order_id: str | None = Field(default=None, min_length=1, max_length=128)
    refund_id: str = Field(min_length=1, max_length=128)
    refund_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_single_payment_selector(self) -> "CreateRefundRequest":
        has_transaction = self.original_transaction_id is not None
        has_order = self.order_id is not None
        if has_transaction == has_order:
            raise ValueError("Exactly one of original_transaction_id or order_id is required.")
        return self


class RefundResponse(BaseModel):
    refund_transaction_id: str
    original_transaction_id: str
    refund_id: str
    refund_amount: Decimal
    refund_status: RefundStatus

    @classmethod
    def from_refund(
        cls,
        refund: RefundTransaction,
        original_payment: PaymentTransaction,
    ) -> "RefundResponse":
        return cls(
            refund_transaction_id=refund.refund_transaction_id,
            original_transaction_id=original_payment.transaction_id,
            refund_id=refund.refund_id,
            refund_amount=refund.refund_amount,
            refund_status=refund.status,
        )


class RefundStatusResponse(RefundResponse):
    pass
