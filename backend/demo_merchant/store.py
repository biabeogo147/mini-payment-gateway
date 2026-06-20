from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import RLock


@dataclass(frozen=True)
class MerchantIntegration:
    merchant_id: str
    access_key: str
    secret_key: str


@dataclass
class DemoOrder:
    order_id: str
    transaction_id: str
    amount: Decimal
    description: str
    qr_reference: str | None
    qr_content: str
    qr_image_base64: str | None
    status: str
    notification_state: str
    expire_at: datetime
    updated_at: datetime
    failed_reason: str | None = None
    webhook_event_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "description": self.description,
            "qr_reference": self.qr_reference,
            "qr_content": self.qr_content,
            "qr_image_base64": self.qr_image_base64,
            "status": self.status,
            "notification_state": self.notification_state,
            "failed_reason": self.failed_reason,
            "expire_at": self.expire_at.isoformat().replace("+00:00", "Z"),
            "updated_at": self.updated_at.isoformat().replace("+00:00", "Z"),
            "webhook_event_id": self.webhook_event_id,
        }


class DemoOrderStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._integration: MerchantIntegration | None = None
        self._orders: dict[str, DemoOrder] = {}
        self._orders_by_transaction: dict[str, str] = {}
        self.processed_event_ids: set[str] = set()

    def set_integration(self, integration: MerchantIntegration) -> None:
        with self._lock:
            self._integration = integration

    def integration(self) -> MerchantIntegration | None:
        with self._lock:
            return self._integration

    def add_order(self, order: DemoOrder) -> None:
        with self._lock:
            self._orders[order.order_id] = order
            self._orders_by_transaction[order.transaction_id] = order.order_id

    def get_order(self, order_id: str) -> DemoOrder | None:
        with self._lock:
            return self._orders.get(order_id)

    def get_by_transaction(self, transaction_id: str) -> DemoOrder | None:
        with self._lock:
            order_id = self._orders_by_transaction.get(transaction_id)
            return self._orders.get(order_id) if order_id else None

    def mark_awaiting_webhook(self, order_id: str, updated_at: datetime) -> DemoOrder:
        with self._lock:
            order = self._orders[order_id]
            order.notification_state = "AWAITING_WEBHOOK"
            order.updated_at = updated_at
            return order

    def apply_payment_webhook(
        self,
        *,
        event_id: str,
        transaction_id: str,
        status: str,
        failed_reason: str | None,
        updated_at: datetime,
    ) -> tuple[DemoOrder | None, bool]:
        with self._lock:
            if event_id in self.processed_event_ids:
                return self.get_by_transaction(transaction_id), True
            order = self.get_by_transaction(transaction_id)
            if order is None:
                return None, False
            order.status = status
            order.notification_state = "WEBHOOK_RECEIVED"
            order.failed_reason = failed_reason
            order.webhook_event_id = event_id
            order.updated_at = updated_at
            self.processed_event_ids.add(event_id)
            return order, False

    def reset(self) -> None:
        with self._lock:
            self._integration = None
            self._orders.clear()
            self._orders_by_transaction.clear()
            self.processed_event_ids.clear()
