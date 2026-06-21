from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from demo_merchant.config import DemoMerchantSettings
from demo_merchant.security import build_merchant_headers, build_provider_headers, canonical_json_bytes
from demo_merchant.store import DemoOrder, MerchantIntegration


class GatewayClientError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class GatewayClient:
    def __init__(self, settings: DemoMerchantSettings, http_client=None) -> None:
        self.settings = settings
        self._http_client = http_client

    def verify_integration(self, *, integration: MerchantIntegration) -> dict:
        path = "/v1/merchant/auth/verify"
        body = b""
        headers = build_merchant_headers(
            merchant_id=integration.merchant_id,
            access_key=integration.access_key,
            secret=integration.secret_key,
            method="GET",
            path=path,
            body=body,
            now=_utc_now(),
        )
        return self._request("GET", path, body, headers)

    def create_payment(
        self,
        *,
        integration: MerchantIntegration,
        order_id: str,
        amount: Decimal,
        description: str,
        ttl_seconds: int,
    ) -> dict:
        path = "/v1/payments"
        payload = {
            "order_id": order_id,
            "amount": str(amount),
            "currency": "VND",
            "description": description,
            "ttl_seconds": ttl_seconds,
            "metadata": {"demo_checkout": True},
        }
        body = canonical_json_bytes(payload)
        headers = build_merchant_headers(
            merchant_id=integration.merchant_id,
            access_key=integration.access_key,
            secret=integration.secret_key,
            method="POST",
            path=path,
            body=body,
            now=_utc_now(),
        )
        return self._post(path, body, headers)

    def simulate_payment_result(self, *, order: DemoOrder, outcome: str) -> dict:
        path = "/v1/provider/callbacks/payment"
        now = _utc_now()
        is_success = outcome == "SUCCESS"
        payload = {
            "external_reference": f"bank_demo_{uuid4().hex[:12]}",
            "transaction_reference": order.transaction_id,
            "status": outcome,
            "amount": str(order.amount),
            "paid_at": _isoformat(now) if is_success else None,
            "failed_reason_code": None if is_success else "BANK_REJECTED",
            "failed_reason_message": None if is_success else "Ngân hàng từ chối giao dịch.",
            "source_type": "SIMULATOR",
            "raw_payload": {"demo": True, "provider_status": "00" if is_success else "05"},
        }
        body = canonical_json_bytes(payload)
        headers = build_provider_headers(
            provider_id=self.settings.provider_id,
            secret=self.settings.provider_callback_secret,
            method="POST",
            path=path,
            body=body,
            now=now,
        )
        return self._post(path, body, headers)

    def _post(self, path: str, body: bytes, headers: dict[str, str]) -> dict:
        return self._request("POST", path, body, headers)

    def _request(self, method: str, path: str, body: bytes, headers: dict[str, str]) -> dict:
        owns_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self.settings.request_timeout_seconds)
        try:
            response = client.request(
                method,
                f"{self.settings.gateway_base_url}{path}",
                content=body,
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise GatewayClientError(f"Gateway request failed: {exc}") from exc
        finally:
            if owns_client:
                client.close()
        if response.status_code < 200 or response.status_code >= 300:
            message = _error_message(response)
            raise GatewayClientError(message, status_code=response.status_code)
        return response.json()


def _error_message(response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Gateway returned HTTP {response.status_code}."
    return payload.get("message") or payload.get("detail") or f"Gateway returned HTTP {response.status_code}."


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
