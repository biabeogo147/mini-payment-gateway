import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import CallbackProcessingResult
from app.models.payment_transaction import PaymentTransaction
from smoke_payment_api import create_payment, free_port, get_payment, seed_merchant, wait_for_health


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
        created = create_payment(port, seed)
        callback = send_success_callback(port, created)
        by_transaction = get_payment(port, seed, f"/v1/payments/{created['transaction_id']}")
        db_row = get_callback_db_state(created["transaction_id"], callback["processing_result"])
        print(
            json.dumps(
                {
                    "port": port,
                    "merchant_id": seed["merchant_id"],
                    "transaction_id": created["transaction_id"],
                    "callback_processing_result": callback["processing_result"],
                    "callback_status": callback["status"],
                    "payment_query_status": by_transaction["status"],
                    "db_payment_status": db_row["payment_status"],
                    "db_callback_result": db_row["callback_result"],
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


def send_success_callback(port: int, created_payment: dict) -> dict:
    path = "/v1/provider/callbacks/payment"
    body = json.dumps(
        {
            "external_reference": f"bank-{created_payment['transaction_id']}",
            "transaction_reference": created_payment["transaction_id"],
            "status": "SUCCESS",
            "amount": "12345.00",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": {
                "provider": "SIMULATOR",
                "trace_id": f"trace-{created_payment['transaction_id']}",
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


def get_callback_db_state(transaction_id: str, expected_result: str) -> dict[str, str | bool]:
    with SessionLocal() as db:
        payment = db.scalar(select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id))
        if payment is None:
            raise RuntimeError(f"Payment row not found: {transaction_id}")
        callback_log = db.scalar(
            select(BankCallbackLog)
            .where(BankCallbackLog.transaction_reference == transaction_id)
            .order_by(BankCallbackLog.created_at.desc())
            .limit(1)
        )
        if callback_log is None:
            raise RuntimeError(f"Callback log not found for transaction: {transaction_id}")
        if callback_log.processing_result != CallbackProcessingResult(expected_result):
            raise RuntimeError(
                "Unexpected callback result: "
                f"{callback_log.processing_result.value}, expected {expected_result}"
            )
        return {
            "payment_status": payment.status.value,
            "callback_result": callback_log.processing_result.value,
            "callback_has_raw_payload": bool(callback_log.raw_payload_json),
        }


if __name__ == "__main__":
    main()
