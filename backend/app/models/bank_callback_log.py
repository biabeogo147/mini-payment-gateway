from datetime import datetime

from sqlalchemy import DateTime, Enum, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import CallbackProcessingResult, CallbackSourceType, CallbackType


class BankCallbackLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Raw and normalized callback log from bank/provider/simulator.

    Field meanings:
    - id: internal UUID primary key.
    - source_type: callback source system.
    - external_reference: provider-side reference.
    - transaction_reference: gateway transaction/refund reference from callback.
    - callback_type: payment or refund callback category.
    - raw_payload_json: original callback payload.
    - normalized_status: mapped internal status value.
    - received_at/processed_at: callback processing timestamps.
    - processing_result: processing outcome after normalization.
    - error_message: processing error detail if any.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "bank_callback_logs"

    source_type: Mapped[CallbackSourceType] = mapped_column(
        Enum(CallbackSourceType, name="callback_source_type"),
        nullable=False,
    )
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transaction_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    callback_type: Mapped[CallbackType] = mapped_column(
        Enum(CallbackType, name="callback_type"),
        nullable=False,
    )
    raw_payload_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    normalized_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_result: Mapped[CallbackProcessingResult] = mapped_column(
        Enum(CallbackProcessingResult, name="callback_processing_result"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
