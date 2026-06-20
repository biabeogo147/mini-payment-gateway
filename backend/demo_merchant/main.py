from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from demo_merchant.config import DemoMerchantSettings
from demo_merchant.gateway_client import GatewayClient, GatewayClientError
from demo_merchant.security import WebhookAuthError, verify_webhook_signature
from demo_merchant.store import DemoOrder, DemoOrderStore, MerchantIntegration

STATIC_DIR = Path(__file__).with_name("static")


class SetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    merchant_id: str = Field(min_length=1, max_length=64)
    access_key: str = Field(min_length=1, max_length=128)
    secret_key: str = Field(min_length=1)


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=255)
    ttl_seconds: int = Field(default=300, ge=60, le=1800)

    @field_validator("amount")
    @classmethod
    def require_whole_vnd(cls, value: Decimal) -> Decimal:
        if value != value.to_integral_value():
            raise ValueError("Demo payments require a whole VND amount.")
        return value


class SimulateResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["SUCCESS", "FAILED"]


def create_app(
    *,
    settings: DemoMerchantSettings | None = None,
    store: DemoOrderStore | None = None,
    gateway_client=None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    resolved_settings = settings or DemoMerchantSettings.from_env()
    resolved_store = store or DemoOrderStore()
    gateway = gateway_client or GatewayClient(resolved_settings)
    now = clock or _utc_now
    app = FastAPI(title="Demo Merchant Checkout")
    app.state.settings = resolved_settings
    app.state.store = resolved_store
    app.state.gateway_client = gateway
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="demo-static")

    @app.get("/", response_class=HTMLResponse)
    def checkout_page() -> HTMLResponse:
        return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "configured": resolved_store.integration() is not None}

    @app.put("/api/setup")
    def setup(request: SetupRequest) -> dict:
        resolved_store.set_integration(
            MerchantIntegration(
                merchant_id=request.merchant_id,
                access_key=request.access_key,
                secret_key=request.secret_key,
            )
        )
        return {"configured": True, "merchant_id": request.merchant_id}

    @app.post("/api/orders")
    def create_order(request: CreateOrderRequest) -> dict:
        integration = resolved_store.integration()
        if integration is None:
            raise HTTPException(status_code=409, detail="Demo merchant is not configured.")
        order_id = _new_order_id(now())
        try:
            payment = gateway.create_payment(
                integration=integration,
                order_id=order_id,
                amount=request.amount,
                description=request.description,
                ttl_seconds=request.ttl_seconds,
            )
        except GatewayClientError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        order = DemoOrder(
            order_id=order_id,
            transaction_id=payment["transaction_id"],
            amount=request.amount,
            description=request.description,
            qr_reference=payment.get("qr_reference"),
            qr_content=payment["qr_content"],
            qr_image_base64=payment.get("qr_image_base64") or payment.get("qr_image_url"),
            status=payment["status"],
            notification_state="WAITING_FOR_BANK",
            expire_at=_parse_datetime(payment["expire_at"]),
            updated_at=now(),
        )
        resolved_store.add_order(order)
        return order.as_dict()

    @app.get("/api/orders/{order_id}")
    def get_order(order_id: str) -> dict:
        order = resolved_store.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Demo order was not found.")
        return order.as_dict()

    @app.post("/api/orders/{order_id}/simulate-result")
    def simulate_result(order_id: str, request: SimulateResultRequest) -> dict:
        order = resolved_store.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Demo order was not found.")
        if order.status != "PENDING":
            raise HTTPException(status_code=409, detail="Only pending orders can be simulated.")
        try:
            gateway.simulate_payment_result(order=order, outcome=request.status)
        except GatewayClientError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        return resolved_store.mark_awaiting_webhook(order_id, now()).as_dict()

    @app.post("/webhooks/payment-gateway")
    async def payment_gateway_webhook(
        raw_request: Request,
        x_webhook_event_id: str | None = Header(default=None),
        x_webhook_timestamp: str | None = Header(default=None),
        x_webhook_signature: str | None = Header(default=None),
    ) -> dict:
        integration = resolved_store.integration()
        if integration is None:
            raise HTTPException(status_code=503, detail="Demo merchant is not configured.")
        body = await raw_request.body()
        try:
            verify_webhook_signature(
                secret=integration.secret_key,
                event_id=x_webhook_event_id,
                timestamp=x_webhook_timestamp,
                signature=x_webhook_signature,
                body=body,
                now=now(),
                max_age_seconds=resolved_settings.webhook_max_age_seconds,
            )
        except WebhookAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Webhook body is invalid JSON.") from exc
        if payload.get("merchant_id") != integration.merchant_id:
            raise HTTPException(status_code=403, detail="Webhook merchant does not match setup.")
        event_type = payload.get("event_type")
        if not isinstance(event_type, str) or not event_type.startswith("payment."):
            return {"accepted": True, "ignored": True}
        data = payload.get("data") or {}
        transaction_id = data.get("transaction_id")
        if not transaction_id:
            raise HTTPException(status_code=400, detail="Webhook transaction id is missing.")
        status = {
            "payment.succeeded": "SUCCESS",
            "payment.failed": "FAILED",
            "payment.expired": "EXPIRED",
        }.get(event_type)
        if status is None:
            return {"accepted": True, "ignored": True}
        order, duplicate = resolved_store.apply_payment_webhook(
            event_id=x_webhook_event_id or payload.get("event_id"),
            transaction_id=transaction_id,
            status=status,
            failed_reason=data.get("failed_reason_message"),
            updated_at=now(),
        )
        if order is None:
            raise HTTPException(status_code=404, detail="Webhook payment is unknown to demo merchant.")
        return {"accepted": True, "duplicate": duplicate}

    @app.post("/api/demo/reset")
    def reset_demo() -> dict:
        if not resolved_settings.demo_mode:
            raise HTTPException(status_code=404, detail="Not found.")
        resolved_store.reset()
        return {"configured": False}

    return app


def _new_order_id(now: datetime) -> str:
    return f"DEMO-{now.astimezone(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:6].upper()}"


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


app = create_app()
