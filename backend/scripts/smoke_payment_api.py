import hashlib
import hmac
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import CredentialStatus, MerchantStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.payment_transaction import PaymentTransaction


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
        by_transaction = get_payment(port, seed, f"/v1/payments/{created['transaction_id']}")
        by_order = get_payment(port, seed, f"/v1/payments/by-order/{seed['order_id']}")
        db_row = get_payment_db_row(created["transaction_id"])
        print(
            json.dumps(
                {
                    "port": port,
                    "merchant_id": seed["merchant_id"],
                    "created_transaction": created["transaction_id"],
                    "created_status": created["status"],
                    "by_transaction_status": by_transaction["status"],
                    "by_order_transaction": by_order["transaction_id"],
                    "db_status": db_row["status"],
                    "db_amount": db_row["amount"],
                    "db_qr_has_transaction_id": db_row["qr_has_transaction_id"],
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


def seed_merchant() -> dict[str, str]:
    suffix = uuid4().hex[:8]
    merchant_id = f"m_phase3_{suffix}"
    access_key = f"ak_phase3_{suffix}"
    secret = f"phase3-secret-{suffix}"
    with SessionLocal() as db:
        merchant = Merchant(
            merchant_id=merchant_id,
            merchant_name="Phase 3 Smoke Merchant",
            contact_email=f"phase3-{suffix}@example.com",
            status=MerchantStatus.ACTIVE,
        )
        db.add(merchant)
        db.flush()
        credential = MerchantCredential(
            merchant_db_id=merchant.id,
            access_key=access_key,
            secret_key_encrypted=secret,
            secret_key_last4=secret[-4:],
            status=CredentialStatus.ACTIVE,
        )
        db.add(credential)
        db.commit()
    return {
        "merchant_id": merchant_id,
        "access_key": access_key,
        "secret": secret,
        "order_id": f"ORDER-PHASE3-{suffix}",
    }


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"Uvicorn exited early.\nstdout={stdout}\nstderr={stderr}")
        try:
            request_json("GET", f"http://127.0.0.1:{port}/health", path="/health", body=b"", headers={})
            return
        except (URLError, RuntimeError):
            time.sleep(0.25)
    raise TimeoutError("Uvicorn did not become healthy within 15 seconds.")


def create_payment(port: int, seed: dict[str, str]) -> dict:
    body = json.dumps(
        {
            "order_id": seed["order_id"],
            "amount": "12345.00",
            "description": "Phase 3 smoke payment",
            "ttl_seconds": 900,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    path = "/v1/payments"
    return request_json(
        "POST",
        f"http://127.0.0.1:{port}{path}",
        path=path,
        body=body,
        headers=signed_headers("POST", path, body, seed, idempotency_key="phase3-smoke-1"),
    )


def get_payment(port: int, seed: dict[str, str], path: str) -> dict:
    return request_json(
        "GET",
        f"http://127.0.0.1:{port}{path}",
        path=path,
        body=b"",
        headers=signed_headers("GET", path, b"", seed),
    )


def request_json(method: str, url: str, path: str, body: bytes, headers: dict[str, str]) -> dict:
    request = Request(
        url,
        data=body if method != "GET" else None,
        method=method,
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {payload}") from exc


def signed_headers(
    method: str,
    path: str,
    body: bytes,
    seed: dict[str, str],
    idempotency_key: str | None = None,
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body_hash = hashlib.sha256(body).hexdigest()
    signing_string = f"{timestamp}.{method}.{path}.{body_hash}"
    signature = hmac.new(seed["secret"].encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "X-Merchant-Id": seed["merchant_id"],
        "X-Access-Key": seed["access_key"],
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    }
    if idempotency_key is not None:
        headers["X-Idempotency-Key"] = idempotency_key
    return headers


def get_payment_db_row(transaction_id: str) -> dict[str, str | bool]:
    with SessionLocal() as db:
        payment = db.scalar(select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id))
        if payment is None:
            raise RuntimeError(f"Payment row not found: {transaction_id}")
        return {
            "transaction_id": payment.transaction_id,
            "order_id": payment.order_id,
            "status": payment.status.value,
            "amount": str(payment.amount),
            "qr_has_transaction_id": transaction_id in payment.qr_content,
        }


if __name__ == "__main__":
    main()
