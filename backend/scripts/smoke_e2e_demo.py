from __future__ import annotations

import argparse
import json
import os
import time
from uuid import uuid4

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the visual payment demo through real HTTP services.")
    parser.add_argument("--outcome", choices=("success", "failed"), default="success")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    gateway_url = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    demo_url = os.getenv("DEMO_MERCHANT_BASE_URL", "http://127.0.0.1:8100").rstrip("/")
    admin_email = os.getenv("DEMO_ADMIN_EMAIL", "postman.admin@example.com")
    admin_password = os.getenv("DEMO_ADMIN_PASSWORD", "PostmanAdmin123!")
    suffix = uuid4().hex[:8]
    merchant_id = f"m_e2e_{suffix}"
    access_key = f"ak_e2e_{suffix}"
    merchant_secret = f"merchant-e2e-secret-{suffix}"
    portal_email = f"merchant-{suffix}@example.com"
    ops_email = f"ops-{suffix}@example.com"
    ops_password = f"OpsDemo-{suffix}-123!"
    actor = {"actor_type": "OPS", "actor_id": None, "reason": "E2E visual demo smoke."}

    with httpx.Client(timeout=10, follow_redirects=True) as ops:
        _require_ok(ops.get(f"{gateway_url}/health"), "gateway health")
        _require_ok(httpx.get(f"{demo_url}/health", timeout=10), "demo merchant health")
        bootstrap = _require_ok(
            ops.get(f"{gateway_url}/v1/internal/auth/bootstrap-status"),
            "bootstrap status",
        )
        if bootstrap["bootstrap_required"]:
            _require_ok(
                ops.post(
                    f"{gateway_url}/v1/internal/auth/bootstrap",
                    json={
                        "email": admin_email,
                        "full_name": "E2E Demo Admin",
                        "password": admin_password,
                    },
                ),
                "bootstrap first admin",
            )
        else:
            _require_ok(
                ops.post(
                    f"{gateway_url}/v1/internal/auth/login",
                    json={"email": admin_email, "password": admin_password},
                ),
                "internal admin login",
            )

        _require_ok(
            ops.post(
                f"{gateway_url}/v1/internal/users",
                json={
                    "email": ops_email,
                    "full_name": "E2E Demo Ops",
                    "role": "OPS",
                    "password": ops_password,
                    "status": "ACTIVE",
                },
            ),
            "create internal ops user",
        )
        _require_ok(
            ops.post(f"{gateway_url}/v1/internal/auth/logout"),
            "internal admin logout",
        )
        _require_ok(
            ops.post(
                f"{gateway_url}/v1/internal/auth/login",
                json={"email": ops_email, "password": ops_password},
            ),
            "internal ops login",
        )

        _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants",
                json={
                    "actor": actor,
                    "merchant_id": merchant_id,
                    "merchant_name": f"E2E Demo Shop {suffix}",
                    "legal_name": "E2E Demo Shop Company",
                    "contact_name": "Demo Merchant",
                    "contact_email": portal_email,
                    "contact_phone": "0900000000",
                    "webhook_url": f"{demo_url}/webhooks/payment-gateway",
                    "settlement_account_name": "E2E DEMO SHOP",
                    "settlement_account_number": "9704000000000001",
                    "settlement_bank_code": "VCB",
                },
            ),
            "create merchant",
        )
        _require_ok(
            ops.put(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/onboarding-case",
                json={
                    "actor": actor,
                    "domain_or_app_name": "E2E Demo Checkout",
                    "submitted_profile_json": {"business_type": "online_shop"},
                    "documents_json": {"business_license": "demo-license.pdf"},
                    "review_checks_json": {"risk_level": "LOW"},
                },
            ),
            "submit onboarding",
        )
        _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/onboarding-case/approve",
                json={"actor": actor, "reviewed_by": None, "decision_note": "Approved for E2E demo."},
            ),
            "approve onboarding",
        )
        _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/credentials",
                json={"actor": actor, "access_key": access_key, "secret_key": merchant_secret},
            ),
            "create credential",
        )
        _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/qr-accounts",
                json={
                    "actor": actor,
                    "provider": "VIETQR",
                    "bank_code": "VCB",
                    "bank_bin": "970436",
                    "account_number": "9704000000000001",
                    "account_name": "E2E DEMO SHOP",
                    "template": "compact",
                    "status": "ACTIVE",
                },
            ),
            "create QR account",
        )
        portal_user = _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/portal-users",
                json={
                    "email": portal_email,
                    "full_name": "E2E Merchant Admin",
                    "role": "MERCHANT_ADMIN",
                    "status": "ACTIVE",
                },
            ),
            "create merchant portal user",
        )
        _require_ok(
            ops.post(
                f"{gateway_url}/v1/ops/merchants/{merchant_id}/activate",
                json={"actor": actor},
            ),
            "activate merchant",
        )

    with httpx.Client(timeout=10) as demo:
        _require_ok(demo.post(f"{demo_url}/api/demo/reset"), "reset demo merchant")
        _require_ok(
            demo.put(
                f"{demo_url}/api/setup",
                json={
                    "merchant_id": merchant_id,
                    "access_key": access_key,
                    "secret_key": merchant_secret,
                },
            ),
            "configure demo merchant",
        )
        created = _require_ok(
            demo.post(
                f"{demo_url}/api/orders",
                json={
                    "amount": 100000,
                    "description": "Thanh toán đơn hàng smoke demo",
                    "ttl_seconds": 300,
                },
            ),
            "create demo payment",
        )
        if created["status"] != "PENDING":
            raise RuntimeError(f"Expected PENDING payment, received {created['status']}")
        if not created.get("qr_content", "").startswith("000201"):
            raise RuntimeError("Gateway did not return a VietQR payload.")
        if not created.get("qr_image_base64", "").startswith("data:image/png;base64,"):
            raise RuntimeError("Gateway did not return a PNG QR data URL.")

        target = "SUCCESS" if args.outcome == "success" else "FAILED"
        simulated = _require_ok(
            demo.post(
                f"{demo_url}/api/orders/{created['order_id']}/simulate-result",
                json={"status": target},
            ),
            "simulate provider callback",
        )
        if simulated["status"] != "PENDING" or simulated["notification_state"] != "AWAITING_WEBHOOK":
            raise RuntimeError("Simulator changed merchant state before webhook delivery.")

        deadline = time.monotonic() + args.timeout
        final = simulated
        while time.monotonic() < deadline:
            final = _require_ok(
                demo.get(f"{demo_url}/api/orders/{created['order_id']}"),
                "poll demo order",
            )
            if final["status"] == target and final["notification_state"] == "WEBHOOK_RECEIVED":
                break
            time.sleep(0.5)
        else:
            raise TimeoutError(f"Merchant did not receive {target} webhook within {args.timeout}s: {final}")
        if target == "FAILED" and not final.get("failed_reason"):
            raise RuntimeError("Failed payment webhook did not expose a merchant failure reason.")

    with httpx.Client(timeout=10, follow_redirects=True) as portal:
        _require_ok(
            portal.post(
                f"{gateway_url}/v1/merchant-portal/auth/login",
                json={
                    "merchant_id": merchant_id,
                    "email": portal_email,
                    "password": portal_user["generated_password"],
                },
            ),
            "merchant portal login",
        )
        portal_payment = _require_ok(
            portal.get(f"{gateway_url}/v1/merchant-portal/payments/{created['transaction_id']}"),
            "merchant portal payment detail",
        )
        if portal_payment["status"] != target:
            raise RuntimeError("Merchant Portal does not show the finalized payment status.")

    print(
        json.dumps(
            {
                "merchant_id": merchant_id,
                "ops_email": ops_email,
                "portal_email": portal_email,
                "portal_user_provisioned_by": "OPS",
                "order_id": created["order_id"],
                "transaction_id": created["transaction_id"],
                "qr_reference": created["qr_reference"],
                "final_status": final["status"],
                "notification_state": final["notification_state"],
                "failed_reason": final.get("failed_reason"),
                "webhook_event_id": final["webhook_event_id"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _require_ok(response: httpx.Response, label: str) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {"body": response.text}
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed with HTTP {response.status_code}: {payload}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
