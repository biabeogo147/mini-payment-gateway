from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.models.enums import EntityType, ReconciliationStatus
from app.schemas.reconciliation import (
    ReconciliationListResponse,
    ReconciliationRecordResponse,
    ResolveReconciliationRequest,
)
from app.services import reconciliation_service

router = APIRouter(prefix="/v1/ops/reconciliation", tags=["ops-reconciliation"])


@router.get("", response_model=ReconciliationListResponse)
def list_reconciliation_records(
    match_result: ReconciliationStatus | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    limit: int = Query(default=100, gt=0, le=500),
    db: Session = Depends(get_db),
) -> ReconciliationListResponse:
    records = reconciliation_service.list_records(
        db=db,
        match_result=match_result,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return ReconciliationListResponse(records=records)


@router.get("/{record_id}", response_model=ReconciliationRecordResponse)
def get_reconciliation_record(
    record_id: UUID,
    db: Session = Depends(get_db),
) -> ReconciliationRecordResponse:
    return reconciliation_service.get_record(db=db, record_id=record_id)


@router.post("/{record_id}/resolve", response_model=ReconciliationRecordResponse)
def resolve_reconciliation_record(
    record_id: UUID,
    request: ResolveReconciliationRequest,
    db: Session = Depends(get_db),
) -> ReconciliationRecordResponse:
    return reconciliation_service.resolve_record(
        db=db,
        record_id=record_id,
        request=request,
        actor=request.actor,
    )
