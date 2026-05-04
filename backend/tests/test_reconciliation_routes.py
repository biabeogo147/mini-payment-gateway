import unittest
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import EntityType, ReconciliationStatus
from app.schemas.reconciliation import ReconciliationRecordResponse


class ReconciliationRouteTest(unittest.TestCase):
    def test_list_route_passes_filters_to_service(self) -> None:
        from app.controllers import ops_reconciliation_controller
        from app.main import app

        db = object()
        entity_id = uuid4()
        record = _response(entity_id=entity_id, match_result=ReconciliationStatus.MISMATCHED)
        self._override_db(app, db)

        try:
            with patch.object(
                ops_reconciliation_controller.reconciliation_service,
                "list_records",
                return_value=[record],
            ) as service:
                response = TestClient(app).get(
                    "/v1/ops/reconciliation",
                    params={
                        "match_result": "MISMATCHED",
                        "entity_type": "PAYMENT",
                        "entity_id": str(entity_id),
                        "limit": "25",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["records"][0]["match_result"], "MISMATCHED")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["match_result"], ReconciliationStatus.MISMATCHED)
        self.assertEqual(kwargs["entity_type"], EntityType.PAYMENT)
        self.assertEqual(kwargs["entity_id"], entity_id)
        self.assertEqual(kwargs["limit"], 25)

    def test_detail_route_calls_service_with_record_id(self) -> None:
        from app.controllers import ops_reconciliation_controller
        from app.main import app

        db = object()
        record_id = uuid4()
        self._override_db(app, db)

        try:
            with patch.object(
                ops_reconciliation_controller.reconciliation_service,
                "get_record",
                return_value=_response(record_id=record_id),
            ) as service:
                response = TestClient(app).get(f"/v1/ops/reconciliation/{record_id}")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["record_id"], str(record_id))
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["record_id"], record_id)

    def test_resolve_route_calls_service_with_request_actor_and_record_id(self) -> None:
        from app.controllers import ops_reconciliation_controller
        from app.main import app

        db = object()
        record_id = uuid4()
        self._override_db(app, db)

        try:
            with patch.object(
                ops_reconciliation_controller.reconciliation_service,
                "resolve_record",
                return_value=_response(record_id=record_id, match_result=ReconciliationStatus.RESOLVED),
            ) as service:
                response = TestClient(app).post(
                    f"/v1/ops/reconciliation/{record_id}/resolve",
                    json={
                        "actor": {
                            "actor_type": "OPS",
                            "actor_id": None,
                            "reason": "Provider evidence accepted.",
                        },
                        "review_note": "Provider evidence accepted.",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["match_result"], "RESOLVED")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["record_id"], record_id)
        self.assertEqual(kwargs["request"].review_note, "Provider evidence accepted.")
        self.assertEqual(kwargs["actor"].actor_type.value, "OPS")

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


def _response(
    record_id=None,
    entity_id=None,
    match_result=ReconciliationStatus.PENDING_REVIEW,
) -> ReconciliationRecordResponse:
    return ReconciliationRecordResponse(
        record_id=str(record_id or uuid4()),
        entity_type=EntityType.PAYMENT,
        entity_id=str(entity_id or uuid4()),
        internal_status="PENDING",
        external_status="SUCCESS",
        internal_amount=Decimal("100000.00"),
        external_amount=Decimal("100000.00"),
        match_result=match_result,
        mismatch_reason_code=None,
        mismatch_reason_message=None,
        reviewed_by=None,
        review_note=None,
    )


if __name__ == "__main__":
    unittest.main()
