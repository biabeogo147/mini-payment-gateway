import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.enums import ReconciliationStatus
from app.models.reconciliation_record import ReconciliationRecord
from smoke_payment_api import create_payment, free_port, request_json, wait_for_health


def main() -> None:
    suffix = uuid4().hex[:8]
    seed = {
        "merchant_id": f"m_phase7_{suffix}",
        "access_key": f"ak_phase7_{suffix}",
        "secret": f"phase7-secret-{suffix}",
        "order_id": f"ORDER-PHASE7-{suffix}",
    }
    port = free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_health(port, process)
        merchant = create_ops_merchant(port, seed)
        onboarding = submit_onboarding_case(port, seed)
        approval = approve_onboarding_case(port, seed)
        credential = create_ops_credential(port, seed)
        activation = activate_merchant(port, seed)
        payment = create_payment(port, seed)
        mismatch_callback = send_mismatch_callback(port, payment)
        reconciliation_list = list_reconciliation_records(port, mismatch_callback["reconciliation_record_id"])
        resolution = resolve_reconciliation_record(port, mismatch_callback["reconciliation_record_id"])
        db_state = verify_db_state(mismatch_callback["reconciliation_record_id"])
        print(
            json.dumps(
                {
                    "port": port,
                    "merchant_id": merchant["merchant_id"],
                    "onboarding_status": onboarding["status"],
                    "approval_status": approval["status"],
                    "credential_access_key": credential["access_key"],
                    "activation_status": activation["status"],
                    "payment_transaction_id": payment["transaction_id"],
                    "callback_processing_result": mismatch_callback["processing_result"],
                    "reconciliation_record_id": mismatch_callback["reconciliation_record_id"],
                    "listed_reconciliation_count": len(reconciliation_list["records"]),
                    "resolution_status": resolution["match_result"],
                    "db_reconciliation_status": db_state["reconciliation_status"],
                    "audit_events": db_state["audit_events"],
                },
                sort_keys=True,
            )
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def create_ops_merchant(port: int, seed: dict[str, str]) -> dict:
    path = "/v1/ops/merchants"
    body = _json_body(
        {
            "actor": _actor("Register phase 07 smoke merchant."),
            "merchant_id": seed["merchant_id"],
            "merchant_name": "Phase 7 Smoke Merchant",
            "legal_name": "Phase 7 Smoke Merchant LLC",
            "contact_name": "Phase 7 Ops",
            "contact_email": f"{seed['merchant_id']}@example.com",
            "contact_phone": "+84000000000",
            "webhook_url": "https://merchant.example.com/webhooks/payment-gateway",
            "settlement_account_name": "Phase 7 Smoke Merchant LLC",
            "settlement_account_number": "123456789",
            "settlement_bank_code": "DEMO",
        }
    )
    return request_json("POST", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def submit_onboarding_case(port: int, seed: dict[str, str]) -> dict:
    path = f"/v1/ops/merchants/{seed['merchant_id']}/onboarding-case"
    body = _json_body(
        {
            "actor": _actor("Submit phase 07 onboarding evidence."),
            "domain_or_app_name": "Phase 7 Demo Shop",
            "submitted_profile_json": {"business_type": "online_shop"},
            "documents_json": {"business_license": "phase7-license.pdf"},
            "review_checks_json": {"risk_level": "LOW"},
        }
    )
    return request_json("PUT", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def approve_onboarding_case(port: int, seed: dict[str, str]) -> dict:
    path = f"/v1/ops/merchants/{seed['merchant_id']}/onboarding-case/approve"
    body = _json_body(
        {
            "actor": _actor("Approve phase 07 onboarding."),
            "decision_note": "Documents verified for phase 07 smoke.",
        }
    )
    return request_json("POST", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def create_ops_credential(port: int, seed: dict[str, str]) -> dict:
    path = f"/v1/ops/merchants/{seed['merchant_id']}/credentials"
    body = _json_body(
        {
            "actor": _actor("Create active phase 07 credential."),
            "access_key": seed["access_key"],
            "secret_key": seed["secret"],
        }
    )
    return request_json("POST", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def activate_merchant(port: int, seed: dict[str, str]) -> dict:
    path = f"/v1/ops/merchants/{seed['merchant_id']}/activate"
    body = _json_body({"actor": _actor("Activate approved phase 07 merchant.")})
    return request_json("POST", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def send_mismatch_callback(port: int, created_payment: dict) -> dict:
    path = "/v1/provider/callbacks/payment"
    body = _json_body(
        {
            "external_reference": f"bank-{created_payment['transaction_id']}",
            "transaction_reference": created_payment["transaction_id"],
            "status": "SUCCESS",
            "amount": "99999.00",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": {
                "provider": "SIMULATOR",
                "trace_id": f"mismatch-{created_payment['transaction_id']}",
            },
        }
    )
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def list_reconciliation_records(port: int, record_id: str) -> dict:
    path = "/v1/ops/reconciliation?match_result=MISMATCHED&entity_type=PAYMENT&limit=25"
    response = request_json("GET", f"http://127.0.0.1:{port}{path}", path=path, body=b"", headers={})
    if record_id not in {record["record_id"] for record in response["records"]}:
        raise RuntimeError(f"Reconciliation record {record_id} not found in list response.")
    return response


def resolve_reconciliation_record(port: int, record_id: str) -> dict:
    path = f"/v1/ops/reconciliation/{record_id}/resolve"
    body = _json_body(
        {
            "actor": _actor("Resolve phase 07 mismatch after review."),
            "review_note": "Provider evidence reviewed and accepted for smoke.",
        }
    )
    return request_json("POST", f"http://127.0.0.1:{port}{path}", path=path, body=body, headers={})


def verify_db_state(record_id: str) -> dict[str, list[str] | str]:
    expected_events = {
        "MERCHANT_CREATED",
        "ONBOARDING_CASE_SUBMITTED",
        "ONBOARDING_CASE_APPROVED",
        "CREDENTIAL_CREATED",
        "MERCHANT_ACTIVATED",
        "RECONCILIATION_RESOLVED",
    }
    with SessionLocal() as db:
        record = db.scalar(select(ReconciliationRecord).where(ReconciliationRecord.id == UUID(record_id)))
        if record is None:
            raise RuntimeError(f"Reconciliation record not found: {record_id}")
        if record.match_result != ReconciliationStatus.RESOLVED:
            raise RuntimeError(f"Unexpected reconciliation status: {record.match_result.value}")

        audit_events = set(db.scalars(select(AuditLog.event_type)).all())
        missing = expected_events.difference(audit_events)
        if missing:
            raise RuntimeError(f"Missing audit events: {sorted(missing)}")
        return {
            "reconciliation_status": record.match_result.value,
            "audit_events": sorted(expected_events),
        }


def _actor(reason: str) -> dict[str, str | None]:
    return {
        "actor_type": "OPS",
        "actor_id": None,
        "reason": reason,
    }


def _json_body(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


if __name__ == "__main__":
    main()
