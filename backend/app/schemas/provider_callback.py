import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CallbackProcessingResult, CallbackSourceType, PaymentStatus, RefundStatus


class PaymentCallbackStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_reference: str | None = Field(default=None, max_length=128)
    transaction_reference: str = Field(min_length=1, max_length=128)
    status: PaymentCallbackStatus
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    paid_at: datetime | None = None
    failed_reason_code: str | None = Field(default=None, max_length=64)
    failed_reason_message: str | None = None
    raw_payload: dict
    source_type: CallbackSourceType = CallbackSourceType.SIMULATOR

    @model_validator(mode="after")
    def require_success_paid_at(self) -> "PaymentCallbackRequest":
        if self.status == PaymentCallbackStatus.SUCCESS and self.paid_at is None:
            raise ValueError("paid_at is required for successful payment callbacks.")
        return self


class PaymentCallbackResponse(BaseModel):
    transaction_id: str | None
    status: PaymentStatus | None
    processing_result: CallbackProcessingResult
    reconciliation_record_id: str | None = None


class RefundCallbackStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RefundCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_reference: str | None = Field(default=None, max_length=128)
    refund_transaction_id: str = Field(min_length=1, max_length=128)
    status: RefundCallbackStatus
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    processed_at: datetime | None = None
    failed_reason_code: str | None = Field(default=None, max_length=64)
    failed_reason_message: str | None = None
    raw_payload: dict
    source_type: CallbackSourceType = CallbackSourceType.SIMULATOR

    @model_validator(mode="after")
    def require_success_processed_at(self) -> "RefundCallbackRequest":
        if self.status == RefundCallbackStatus.SUCCESS and self.processed_at is None:
            raise ValueError("processed_at is required for successful refund callbacks.")
        return self


class RefundCallbackResponse(BaseModel):
    refund_transaction_id: str | None
    refund_status: RefundStatus | None
    processing_result: CallbackProcessingResult
    reconciliation_record_id: str | None = None
