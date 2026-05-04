import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import CallbackProcessingResult, CallbackType
from app.models.payment_transaction import PaymentTransaction
from app.models.refund_transaction import RefundTransaction
from smoke_payment_api import (
    create_payment,
    free_port,
    request_json,
    seed_merchant,
    signed_headers,
    wait_for_health,
)
from smoke_provider_callback_api import send_success_callback as send_payment_success_callback


def main() -> None:
    seed = seed_merchant()
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
        created_payment = create_payment(port, seed)
        payment_callback = send_payment_success_callback(port, created_payment)
        created_refund = create_refund(port, seed, created_payment)
        refund_callback = send_refund_success_callback(port, created_refund)
        by_transaction = get_refund(port, seed, f"/v1/refunds/{created_refund['refund_transaction_id']}")
        by_refund_id = get_refund(port, seed, f"/v1/refunds/by-refund-id/{created_refund['refund_id']}")
        db_row = get_refund_db_state(
            payment_transaction_id=created_payment["transaction_id"],
            refund_transaction_id=created_refund["refund_transaction_id"],
            expected_result=refund_callback["processing_result"],
        )
        print(
            json.dumps(
                {
                    "port": port,
                    "merchant_id": seed["merchant_id"],
                    "payment_transaction_id": created_payment["transaction_id"],
                    "payment_callback_result": payment_callback["processing_result"],
                    "refund_transaction_id": created_refund["refund_transaction_id"],
                    "refund_create_status": created_refund["refund_status"],
                    "refund_callback_result": refund_callback["processing_result"],
                    "refund_callback_status": refund_callback["refund_status"],
                    "refund_query_status": by_transaction["refund_status"],
                    "refund_by_refund_id_status": by_refund_id["refund_status"],
                    "db_payment_status": db_row["payment_status"],
                    "db_refund_status": db_row["refund_status"],
                    "db_callback_result": db_row["callback_result"],
                    "db_callback_type": db_row["callback_type"],
                    "db_callback_has_raw_payload": db_row["callback_has_raw_payload"],
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


def create_refund(port: int, seed: dict[str, str], created_payment: dict) -> dict:
    refund_id = f"REF-{created_payment['transaction_id'][-12:]}"
    body = json.dumps(
        {
            "original_transaction_id": created_payment["transaction_id"],
            "refund_id": refund_id,
            "refund_amount": "12345.00",
            "reason": "Phase 5 smoke refund",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    path = "/v1/refunds"
    return request_json(
        "POST",
        f"http://127.0.0.1:{port}{path}",
        path=path,
        body=body,
        headers=signed_headers("POST", path, body, seed, idempotency_key=f"refund-{refund_id}"),
    )


def get_refund(port: int, seed: dict[str, str], path: str) -> dict:
    return request_json(
        "GET",
        f"http://127.0.0.1:{port}{path}",
        path=path,
        body=b"",
        headers=signed_headers("GET", path, b"", seed),
    )


def send_refund_success_callback(port: int, created_refund: dict) -> dict:
    path = "/v1/provider/callbacks/refund"
    body = json.dumps(
        {
            "external_reference": f"bank-{created_refund['refund_transaction_id']}",
            "refund_transaction_id": created_refund["refund_transaction_id"],
            "status": "SUCCESS",
            "amount": "12345.00",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": {
                "provider": "SIMULATOR",
                "trace_id": f"refund-trace-{created_refund['refund_transaction_id']}",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise RuntimeError(f"POST {path} failed with {exc.code}: {payload}") from exc
    except URLError as exc:
        raise RuntimeError(f"POST {path} failed: {exc}") from exc


def get_refund_db_state(
    payment_transaction_id: str,
    refund_transaction_id: str,
    expected_result: str,
) -> dict[str, str | bool]:
    with SessionLocal() as db:
        payment = db.scalar(
            select(PaymentTransaction).where(PaymentTransaction.transaction_id == payment_transaction_id)
        )
        if payment is None:
            raise RuntimeError(f"Payment row not found: {payment_transaction_id}")

        refund = db.scalar(
            select(RefundTransaction).where(RefundTransaction.refund_transaction_id == refund_transaction_id)
        )
        if refund is None:
            raise RuntimeError(f"Refund row not found: {refund_transaction_id}")

        callback_log = db.scalar(
            select(BankCallbackLog)
            .where(
                BankCallbackLog.transaction_reference == refund_transaction_id,
                BankCallbackLog.callback_type == CallbackType.REFUND_RESULT,
            )
            .order_by(BankCallbackLog.created_at.desc())
            .limit(1)
        )
        if callback_log is None:
            raise RuntimeError(f"Refund callback log not found for refund: {refund_transaction_id}")
        if callback_log.processing_result != CallbackProcessingResult(expected_result):
            raise RuntimeError(
                "Unexpected refund callback result: "
                f"{callback_log.processing_result.value}, expected {expected_result}"
            )

        return {
            "payment_status": payment.status.value,
            "refund_status": refund.status.value,
            "callback_result": callback_log.processing_result.value,
            "callback_type": callback_log.callback_type.value,
            "callback_has_raw_payload": bool(callback_log.raw_payload_json),
        }


if __name__ == "__main__":
    main()
