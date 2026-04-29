from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PaymentStatus
from app.models.payment_transaction import PaymentTransaction


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="VND", min_length=3, max_length=3)
    description: str = Field(min_length=1)
    expire_at: datetime | None = None
    ttl_seconds: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_single_expiration_strategy(self) -> "CreatePaymentRequest":
        has_expire_at = self.expire_at is not None
        has_ttl = self.ttl_seconds is not None
        if has_expire_at == has_ttl:
            raise ValueError("Exactly one of expire_at or ttl_seconds is required.")
        return self

    def resolve_expire_at(self, now: datetime) -> datetime:
        if self.expire_at is not None:
            return _ensure_timezone(self.expire_at)
        normalized_now = _ensure_timezone(now)
        return normalized_now + timedelta(seconds=self.ttl_seconds or 0)


class PaymentResponse(BaseModel):
    transaction_id: str
    order_id: str
    merchant_id: str
    qr_content: str
    qr_image_url: str | None = None
    qr_image_base64: str | None = None
    status: PaymentStatus
    expire_at: datetime

    @classmethod
    def from_payment(cls, payment: PaymentTransaction, merchant_id: str) -> "PaymentResponse":
        return cls(
            transaction_id=payment.transaction_id,
            order_id=payment.order_id,
            merchant_id=merchant_id,
            qr_content=payment.qr_content,
            qr_image_url=payment.qr_image_url,
            qr_image_base64=payment.qr_image_base64,
            status=payment.status,
            expire_at=payment.expire_at,
        )


class PaymentStatusResponse(PaymentResponse):
    pass


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
