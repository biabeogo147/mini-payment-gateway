from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import EntityType, ReconciliationStatus
from app.models.reconciliation_record import ReconciliationRecord
from app.schemas.ops import OpsActorContext


class ReconciliationRecordResponse(BaseModel):
    record_id: str
    entity_type: EntityType
    entity_id: str
    internal_status: str
    external_status: str
    internal_amount: Decimal
    external_amount: Decimal
    match_result: ReconciliationStatus
    mismatch_reason_code: str | None = None
    mismatch_reason_message: str | None = None
    reviewed_by: UUID | None = None
    review_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("internal_amount", "external_amount")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @classmethod
    def from_record(cls, record: ReconciliationRecord) -> "ReconciliationRecordResponse":
        return cls(
            record_id=str(record.id),
            entity_type=record.entity_type,
            entity_id=str(record.entity_id),
            internal_status=record.internal_status,
            external_status=record.external_status,
            internal_amount=record.internal_amount,
            external_amount=record.external_amount,
            match_result=record.match_result,
            mismatch_reason_code=record.mismatch_reason_code,
            mismatch_reason_message=record.mismatch_reason_message,
            reviewed_by=record.reviewed_by,
            review_note=record.review_note,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ResolveReconciliationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: OpsActorContext
    reviewed_by: UUID | None = None
    review_note: str = Field(min_length=1)


class ReconciliationListResponse(BaseModel):
    records: list[ReconciliationRecordResponse]
