import copy
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "postman" / "mini-payment-gateway.collection.json"
ENV_PATH = ROOT / "postman" / "mini-payment-gateway.sandbox.environment.json"
SCENARIO_DIR = ROOT / "postman" / "scenarios"
SCENARIO_DIR.mkdir(parents=True, exist_ok=True)


with MASTER_PATH.open("r", encoding="utf-8") as f:
    master = json.load(f)
with ENV_PATH.open("r", encoding="utf-8") as f:
    env = json.load(f)


def iter_requests(items):
    for item in items:
        if "request" in item:
            yield item
        for child in iter_requests(item.get("item", [])):
            yield child


MASTER_REQUESTS = {item["name"]: item for item in iter_requests(master["item"])}
SHARED_EVENT = copy.deepcopy(master["event"])


def clone_request(name: str, new_name: str | None = None) -> dict:
    item = copy.deepcopy(MASTER_REQUESTS[name])
    if new_name is not None:
        item["name"] = new_name
    return item


def add_event(item: dict, listen: str, lines: list[str]) -> dict:
    item.setdefault("event", [])
    item["event"].append(
        {
            "listen": listen,
            "script": {
                "type": "text/javascript",
                "exec": lines,
            },
        }
    )
    return item


def content_json_header() -> list[dict]:
    return [{"key": "Content-Type", "value": "application/json"}]


def request_item(
    name: str,
    method: str,
    url: str,
    description: str,
    body: str | None = None,
    headers: list[dict] | None = None,
    tests: list[str] | None = None,
    prerequest: list[str] | None = None,
) -> dict:
    item = {
        "name": name,
        "request": {
            "method": method,
            "description": description,
            "url": url,
        },
    }
    if headers:
        item["request"]["header"] = headers
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": body}
    if prerequest:
        add_event(item, "prerequest", prerequest)
    if tests:
        add_event(item, "test", tests)
    return item


def folder(name: str, items: list[dict], description: str | None = None) -> dict:
    result = {"name": name, "item": items}
    if description:
        result["description"] = description
    return result


def collection(name: str, description: str, items: list[dict]) -> dict:
    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "event": copy.deepcopy(SHARED_EVENT),
        "item": items,
    }


def error_tests(error_code: str, status_code: int | None = None) -> list[str]:
    tests = []
    if status_code is None:
        tests.append("pm.test('Status is 4xx', function () { pm.expect(pm.response.code).to.be.within(400, 499); });")
    else:
        tests.append(f"pm.test('Status is {status_code}', function () {{ pm.response.to.have.status({status_code}); }});")
    tests.append("const data = pm.response.json();")
    tests.append(f"pm.test('Error code is {error_code}', function () {{ pm.expect(data.error_code).to.eql('{error_code}'); }});")
    return tests


SIGN_PREFIX = [
    "const path = '/' + pm.variables.replaceIn(pm.request.url.getPath()).replace(/^\\/+/, '');",
    "const method = pm.request.method.toUpperCase();",
    "let rawBody = '';",
    "if (pm.request.body && pm.request.body.mode === 'raw') { rawBody = pm.variables.replaceIn(pm.request.body.raw || ''); }",
    "const bodyHash = CryptoJS.SHA256(CryptoJS.enc.Utf8.parse(rawBody)).toString(CryptoJS.enc.Hex);",
]


def sign_with(secret_expr: str, merchant_expr: str, access_expr: str, timestamp_expr: str) -> list[str]:
    return SIGN_PREFIX + [
        f"const timestamp = {timestamp_expr};",
        "const signingString = `${timestamp}.${method}.${path}.${bodyHash}`;",
        f"const signature = CryptoJS.HmacSHA256(signingString, {secret_expr}).toString(CryptoJS.enc.Hex);",
        f"pm.request.headers.upsert({{ key: 'X-Merchant-Id', value: {merchant_expr} }});",
        f"pm.request.headers.upsert({{ key: 'X-Access-Key', value: {access_expr} }});",
        "pm.request.headers.upsert({ key: 'X-Timestamp', value: timestamp });",
        "pm.request.headers.upsert({ key: 'X-Signature', value: signature });",
    ]


def make_payment_body(order_id: str, amount: str = "{{payment_amount}}", description: str = "{{payment_description}}", ttl: str = "{{payment_ttl_seconds}}") -> str:
    return json.dumps(
        {
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "ttl_seconds": ttl,
            "metadata": {"customer_ref": "CUST-1"},
        }
    )


def make_create_payment(name: str, note: str, order_id: str = "{{order_id}}", amount: str = "{{payment_amount}}", ttl: str = "{{payment_ttl_seconds}}") -> dict:
    return request_item(
        name,
        "POST",
        "{{baseUrl}}/v1/payments",
        note,
        body=make_payment_body(order_id=order_id, amount=amount, ttl=ttl),
        headers=content_json_header(),
        tests=[
            "pm.test('Payment create returns 200', function () { pm.response.to.have.status(200); });",
            "const data = pm.response.json();",
            "if (data.transaction_id) { pm.environment.set('payment_transaction_id', data.transaction_id); }",
            "if (data.order_id) { pm.environment.set('order_id', data.order_id); }",
        ],
    )


def set_order(prefix: str) -> list[str]:
    return [f"pm.environment.set('order_id', `{prefix}-${{Date.now()}}`);"]


SETUP_ACTIVE_MERCHANT = [
    clone_request("Create Merchant"),
    clone_request("Submit Onboarding Case"),
    clone_request("Approve Onboarding Case"),
    clone_request("Create Credential"),
    clone_request("Activate Merchant"),
]


# Auth
auth_missing = clone_request("Create Payment", "AUTH-01 Missing Signature Header")
add_event(auth_missing, "prerequest", ["pm.request.headers.remove('X-Signature');"])
auth_missing["request"]["description"] = "AUTH-01. Removes X-Signature after the collection-level HMAC helper runs."
auth_missing["event"] = [e for e in auth_missing.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_MISSING_HEADER")}}
]

auth_invalid = clone_request("Create Payment", "AUTH-02 Invalid HMAC Signature")
add_event(auth_invalid, "prerequest", ["pm.request.headers.upsert({ key: 'X-Signature', value: 'tampered-signature' });"])
auth_invalid["request"]["description"] = "AUTH-02. Replaces the computed signature with a tampered value."
auth_invalid["event"] = [e for e in auth_invalid.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_INVALID_SIGNATURE")}}
]

auth_expired = clone_request("Create Payment", "AUTH-03 Expired Timestamp")
add_event(
    auth_expired,
    "prerequest",
    sign_with(
        "pm.environment.get('merchant_secret') || ''",
        "pm.environment.get('merchant_id') || ''",
        "pm.environment.get('access_key') || ''",
        "new Date(Date.now() - 20 * 60 * 1000).toISOString()",
    ),
)
auth_expired["request"]["description"] = "AUTH-03. Re-signs the request with an expired timestamp."
auth_expired["event"] = [e for e in auth_expired.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_TIMESTAMP_EXPIRED")}}
]

auth_unknown = clone_request("Create Payment", "AUTH-04 Unknown Merchant")
add_event(auth_unknown, "prerequest", ["pm.environment.set('unknown_merchant_id', `m_unknown_${Date.now()}`);"] + sign_with(
    "pm.environment.get('merchant_secret') || ''",
    "pm.environment.get('unknown_merchant_id') || ''",
    "pm.environment.get('access_key') || ''",
    "new Date().toISOString()",
))
auth_unknown["request"]["description"] = "AUTH-04. Uses an unknown merchant id and expects the same opaque auth failure."
auth_unknown["event"] = [e for e in auth_unknown.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_INVALID_SIGNATURE")}}
]

rotate_preserve = clone_request("Rotate Credential", "Prepare Inactive Credential Via Rotation")
add_event(
    rotate_preserve,
    "prerequest",
    [
        "pm.environment.set('inactive_access_key', pm.environment.get('access_key') || '');",
        "pm.environment.set('inactive_merchant_secret', pm.environment.get('merchant_secret') || '');",
    ],
)
rotate_preserve["request"]["description"] = "AUTH-05 setup. Rotates the active credential and preserves the previous values."

inactive_request = clone_request("Create Payment", "AUTH-05 Rotated Credential Fails")
add_event(
    inactive_request,
    "prerequest",
    sign_with(
        "pm.environment.get('inactive_merchant_secret') || ''",
        "pm.environment.get('merchant_id') || ''",
        "pm.environment.get('inactive_access_key') || ''",
        "new Date().toISOString()",
    ),
)
inactive_request["request"]["description"] = "AUTH-05. Uses the rotated-out credential after rotation."
inactive_request["event"] = [e for e in inactive_request.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_INVALID_SIGNATURE")}}
]

auth_collection = collection(
    "Mini Payment Gateway - Auth Scenarios",
    "Companion for docs/testing/scenarios/auth.md.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("Baseline", [clone_request("Create Payment", "Baseline Valid Merchant Payment")]),
        folder("AUTH-01 Missing Auth Header Fails", [auth_missing]),
        folder("AUTH-02 Invalid HMAC Signature Fails", [auth_invalid]),
        folder("AUTH-03 Expired Timestamp Fails", [auth_expired]),
        folder("AUTH-04 Unknown Merchant Fails", [auth_unknown]),
        folder("AUTH-05 Inactive Credential Fails", [rotate_preserve, inactive_request]),
    ],
)


# Merchant
create_credential_pending = clone_request("Create Credential", "Create Credential While Merchant Is Still Pending")
blocked_payment = clone_request("Create Payment", "MER-02 Pending Merchant Payment Blocked")
blocked_payment["request"]["description"] = "MER-02. Merchant has a valid credential but is not ACTIVE."
blocked_payment["event"] = [e for e in blocked_payment.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("MERCHANT_NOT_ACTIVE", 403)}}
]
blocked_refund = request_item(
    "MER-02 Pending Merchant Refund Blocked",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "MER-02. Readiness fails before refund lookup.",
    body=json.dumps(
        {
            "original_transaction_id": "pay_placeholder",
            "refund_id": "{{refund_id}}",
            "refund_amount": "{{refund_amount}}",
            "reason": "Blocked while merchant is pending",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("MERCHANT_NOT_ACTIVE", 403),
)
merchant_collection = collection(
    "Mini Payment Gateway - Merchant Scenarios",
    "Companion for docs/testing/scenarios/merchant.md.",
    [
        clone_request("Health"),
        folder("ONB-01 Ops Registers Merchant", [clone_request("Create Merchant")]),
        folder("ONB-02 Ops Submits Onboarding Case", [clone_request("Submit Onboarding Case")]),
        folder("ONB-03 Ops Approves Onboarding Case", [clone_request("Approve Onboarding Case")]),
        folder("MER-02 Non-Active Merchant Cannot Use Entry Points", [create_credential_pending, blocked_payment, blocked_refund]),
        folder("ONB-04 Ops Activates Merchant", [clone_request("Activate Merchant")]),
        folder(
            "MER-01 Active Merchant Can Use Payment And Refund Entry Points",
            [
                clone_request("Create Payment", "MER-01 Active Merchant Can Create Payment"),
                clone_request("Payment Callback Success", "Finalize Payment For Refund Entry Smoke"),
                clone_request("Create Refund", "MER-01 Active Merchant Can Create Refund"),
            ],
        ),
    ],
)


# Payment
duplicate_same = clone_request("Create Payment", "PAY-04 Duplicate Pending Payment With Identical Request")
duplicate_diff = clone_request("Create Payment", "PAY-05 Duplicate Pending Payment With Different Amount")
duplicate_diff["request"]["body"]["raw"] = make_payment_body(order_id="{{order_id}}", amount="99999.00")
duplicate_diff["event"] = [e for e in duplicate_diff.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("PAYMENT_PENDING_EXISTS", 409)}}
]

failed_create = make_create_payment("PAY-06 Create Payment For Failed Retry", "PAY-06 setup.")
add_event(failed_create, "prerequest", set_order("ORDER-PAY-FAIL"))
failed_callback = request_item(
    "PAY-06 Provider Callback Failed",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/payment",
    "PAY-06 setup. Moves the payment to FAILED.",
    body=json.dumps(
        {
            "external_reference": "bank-fail-{{now_iso}}",
            "transaction_reference": "{{payment_transaction_id}}",
            "status": "FAILED",
            "amount": "{{payment_amount}}",
            "failed_reason_code": "BANK_DECLINED",
            "failed_reason_message": "Simulated bank decline",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "trace-fail-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=[
        "pm.test('Failed callback returns 200', function () { pm.response.to.have.status(200); });",
        "const data = pm.response.json();",
        "pm.test('Payment is failed', function () { pm.expect(data.status).to.eql('FAILED'); });",
    ],
)
expired_create = make_create_payment("PAY-07 Create Short-TTL Payment", "PAY-07 setup.", ttl="1")
add_event(expired_create, "prerequest", set_order("ORDER-PAY-EXP"))
expired_retry = clone_request("Create Payment", "PAY-07 Retry Same Order After Expiration (Template)")
expired_retry["request"]["description"] = "PAY-07 template. Run only after the payment has been expired by the internal worker."
success_create = make_create_payment("PAY-08 Create Payment For Success Lock", "PAY-08 setup.")
add_event(success_create, "prerequest", set_order("ORDER-PAY-SUCCESS"))
success_retry = clone_request("Create Payment", "PAY-08 Retry Same Order After Success")
success_retry["event"] = [e for e in success_retry.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("PAYMENT_ALREADY_SUCCESS", 409)}}
]

create_second_merchant = request_item(
    "Create Second Merchant For PAY-09/PAY-10",
    "POST",
    "{{baseUrl}}/v1/ops/merchants",
    "Setup second merchant.",
    body=json.dumps(
        {
            "actor": {"actor_type": "OPS", "actor_id": None, "reason": "{{ops_reason}}"},
            "merchant_id": "{{other_merchant_id}}",
            "merchant_name": "QA Other Merchant",
            "legal_name": "QA Other Merchant LLC",
            "contact_name": "QA Other Ops",
            "contact_email": "other_{{now_iso}}@example.com",
            "contact_phone": "+84000000001",
            "webhook_url": "{{webhook_url}}",
            "settlement_account_name": "QA Other Merchant LLC",
            "settlement_account_number": "987654321",
            "settlement_bank_code": "DEMO",
        }
    ),
    headers=content_json_header(),
    prerequest=[
        "if (!pm.environment.get('other_merchant_id')) { pm.environment.set('other_merchant_id', `m_other_${Date.now()}`); }",
        "if (!pm.environment.get('other_access_key')) { pm.environment.set('other_access_key', `ak_other_${Date.now()}`); }",
        "if (!pm.environment.get('other_merchant_secret')) { pm.environment.set('other_merchant_secret', `other-secret-${Date.now()}`); }",
    ],
    tests=["pm.test('Second merchant created', function () { pm.response.to.have.status(200); });"],
)
submit_second = request_item(
    "Submit Second Merchant Onboarding",
    "PUT",
    "{{baseUrl}}/v1/ops/merchants/{{other_merchant_id}}/onboarding-case",
    "Submit second merchant onboarding.",
    body=json.dumps(
        {
            "actor": {"actor_type": "OPS", "actor_id": None, "reason": "{{ops_reason}}"},
            "domain_or_app_name": "Other Demo Shop",
            "submitted_profile_json": {"business_type": "online_shop"},
            "documents_json": {"business_license": "other-license.pdf"},
            "review_checks_json": {"risk_level": "LOW"},
        }
    ),
    headers=content_json_header(),
    tests=["pm.test('Second onboarding submitted', function () { pm.response.to.have.status(200); });"],
)
approve_second = request_item(
    "Approve Second Merchant Onboarding",
    "POST",
    "{{baseUrl}}/v1/ops/merchants/{{other_merchant_id}}/onboarding-case/approve",
    "Approve second merchant onboarding.",
    body=json.dumps(
        {
            "actor": {"actor_type": "OPS", "actor_id": None, "reason": "{{ops_reason}}"},
            "reviewed_by": None,
            "decision_note": "Approved for cross-merchant query scenario.",
        }
    ),
    headers=content_json_header(),
    tests=["pm.test('Second onboarding approved', function () { pm.response.to.have.status(200); });"],
)
second_credential = request_item(
    "Create Second Merchant Credential",
    "POST",
    "{{baseUrl}}/v1/ops/merchants/{{other_merchant_id}}/credentials",
    "Create second merchant credential.",
    body=json.dumps(
        {
            "actor": {"actor_type": "OPS", "actor_id": None, "reason": "{{ops_reason}}"},
            "access_key": "{{other_access_key}}",
            "secret_key": "{{other_merchant_secret}}",
        }
    ),
    headers=content_json_header(),
    tests=["pm.test('Second credential created', function () { pm.response.to.have.status(200); });"],
)
blocked_second_payment = request_item(
    "PAY-10 Pending Second Merchant Cannot Create Payment",
    "POST",
    "{{baseUrl}}/v1/payments",
    "PAY-10.",
    body=make_payment_body(order_id="ORDER-PAY-BLOCK-{{now_iso}}"),
    headers=content_json_header(),
    prerequest=sign_with(
        "pm.environment.get('other_merchant_secret') || ''",
        "pm.environment.get('other_merchant_id') || ''",
        "pm.environment.get('other_access_key') || ''",
        "new Date().toISOString()",
    ),
    tests=error_tests("MERCHANT_NOT_ACTIVE", 403),
)
activate_second = request_item(
    "Activate Second Merchant",
    "POST",
    "{{baseUrl}}/v1/ops/merchants/{{other_merchant_id}}/activate",
    "Activate second merchant.",
    body=json.dumps({"actor": {"actor_type": "OPS", "actor_id": None, "reason": "{{ops_reason}}"}}),
    headers=content_json_header(),
    tests=["pm.test('Second merchant activated', function () { pm.response.to.have.status(200); });"],
)
query_other = request_item(
    "PAY-09 Query First Merchant Payment As Second Merchant",
    "GET",
    "{{baseUrl}}/v1/payments/{{payment_transaction_id}}",
    "PAY-09.",
    prerequest=sign_with(
        "pm.environment.get('other_merchant_secret') || ''",
        "pm.environment.get('other_merchant_id') || ''",
        "pm.environment.get('other_access_key') || ''",
        "new Date().toISOString()",
    ),
    tests=error_tests("PAYMENT_NOT_FOUND", 404),
)

payment_collection = collection(
    "Mini Payment Gateway - Payment Scenarios",
    "Companion for docs/testing/scenarios/payment.md.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("PAY-01 PAY-02 PAY-03 Core Payment Flow", [clone_request("Create Payment"), clone_request("Get Payment By Transaction"), clone_request("Get Payment By Order")]),
        folder("PAY-04 PAY-05 Duplicate Pending Paths", [duplicate_same, duplicate_diff]),
        folder("PAY-06 Previous Failed Payment Allows New Attempt", [failed_create, failed_callback, clone_request("Create Payment", "PAY-06 Retry Same Order After Failed Payment")]),
        folder("PAY-07 Previous Expired Payment Allows New Attempt", [expired_create, expired_retry]),
        folder("PAY-08 Previous Successful Payment Rejects New Attempt", [success_create, clone_request("Payment Callback Success", "PAY-08 Provider Callback Success"), success_retry]),
        folder("PAY-09 Query Another Merchant Payment And PAY-10 Non-Active Merchant", [create_second_merchant, submit_second, approve_second, second_credential, blocked_second_payment, activate_second, query_other]),
    ],
)


# Callback
cb_failed_create = make_create_payment("CB-02 Create Payment For Failed Callback", "CB-02 setup.")
add_event(cb_failed_create, "prerequest", set_order("ORDER-CB-FAIL"))
cb_failed = request_item(
    "CB-02 Payment Failed Callback",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/payment",
    "CB-02.",
    body=json.dumps(
        {
            "external_reference": "bank-fail-{{now_iso}}",
            "transaction_reference": "{{payment_transaction_id}}",
            "status": "FAILED",
            "amount": "{{payment_amount}}",
            "failed_reason_code": "BANK_DECLINED",
            "failed_reason_message": "Simulated failure",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "trace-fail-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=[
        "pm.test('Failed callback returns 200', function () { pm.response.to.have.status(200); });",
        "const data = pm.response.json();",
        "pm.test('Payment status becomes FAILED', function () { pm.expect(data.status).to.eql('FAILED'); });",
    ],
)
cb_unknown = request_item(
    "CB-03 Unknown Transaction Callback",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/payment",
    "CB-03.",
    body=json.dumps(
        {
            "external_reference": "bank-unknown-{{now_iso}}",
            "transaction_reference": "pay_unknown_{{now_iso}}",
            "status": "SUCCESS",
            "amount": "{{payment_amount}}",
            "paid_at": "{{now_iso}}",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "trace-unknown-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=["pm.test('Unknown callback stays controlled', function () { pm.response.to.have.status(200); });"],
)
cb_duplicate = clone_request("Payment Callback Success", "CB-04 Duplicate Provider Callback Replay")
cb_expire_create = make_create_payment("EXP-01 Create Short-TTL Payment", "EXP-01 setup.", ttl="1")
add_event(cb_expire_create, "prerequest", set_order("ORDER-CB-EXP"))
cb_late_success = clone_request("Payment Callback Success", "EXP-01 Late Success Callback After Expiration (Template)")
cb_late_success["request"]["description"] = "EXP-01 template. Run after the payment is already EXPIRED."

callback_collection = collection(
    "Mini Payment Gateway - Callback Scenarios",
    "Companion for docs/testing/scenarios/callback.md.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("CB-01 Payment Success Callback", [clone_request("Create Payment"), clone_request("Payment Callback Success")]),
        folder("CB-02 Payment Failed Callback", [cb_failed_create, cb_failed]),
        folder("CB-03 Unknown Transaction Callback", [cb_unknown]),
        folder("CB-04 Duplicate Provider Callback", [cb_duplicate]),
        folder("EXP-01 Expire Overdue Payment And Late Success Callback", [cb_expire_create, cb_late_success]),
    ],
)


# Refund
refund_failed_payment = make_create_payment("REF-05 Create Payment For Failed Refund Callback", "REF-05 setup.")
add_event(refund_failed_payment, "prerequest", set_order("ORDER-REF-FAIL"))
refund_failed_callback = request_item(
    "REF-05 Provider Refund Failed Callback",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/refund",
    "REF-05.",
    body=json.dumps(
        {
            "external_reference": "bank-refund-fail-{{now_iso}}",
            "refund_transaction_id": "{{refund_transaction_id}}",
            "status": "FAILED",
            "amount": "{{refund_amount}}",
            "failed_reason_code": "BANK_REFUND_DECLINED",
            "failed_reason_message": "Simulated refund failure",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "refund-fail-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=[
        "pm.test('Refund failed callback returns 200', function () { pm.response.to.have.status(200); });",
        "const data = pm.response.json();",
        "pm.test('Refund status becomes REFUND_FAILED', function () { pm.expect(data.refund_status).to.eql('REFUND_FAILED'); });",
    ],
)
partial_payment = make_create_payment("REF-06 Create Payment For Partial Refund Reject", "REF-06 setup.")
add_event(partial_payment, "prerequest", set_order("ORDER-REF-PARTIAL"))
partial_refund = request_item(
    "REF-06 Partial Refund Rejects",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "REF-06.",
    body=json.dumps(
        {
            "original_transaction_id": "{{payment_transaction_id}}",
            "refund_id": "{{refund_id}}",
            "refund_amount": "1.00",
            "reason": "Partial refund should fail",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("REFUND_AMOUNT_NOT_FULL", 409),
)
window_template = request_item(
    "REF-07 Refund After 7-Day Window (Template)",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "REF-07 template. Requires a payment already older than 7 days.",
    body=json.dumps(
        {
            "original_transaction_id": "{{payment_transaction_id}}",
            "refund_id": "{{refund_id}}",
            "refund_amount": "{{refund_amount}}",
            "reason": "Refund window expiry template",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("REFUND_WINDOW_EXPIRED", 409),
)
dup_payment = make_create_payment("REF-08 Create Payment For Duplicate Refund Id", "REF-08 setup.")
add_event(dup_payment, "prerequest", ["pm.environment.set('refund_id', `REF-DUP-${Date.now()}`);"] + set_order("ORDER-REF-DUP"))
dup_refund_conflict = request_item(
    "REF-08 Duplicate Refund Id With Different Reason Rejects",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "REF-08 conflicting duplicate.",
    body=json.dumps(
        {
            "original_transaction_id": "{{payment_transaction_id}}",
            "refund_id": "{{refund_id}}",
            "refund_amount": "{{refund_amount}}",
            "reason": "Different reason for same refund id",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("REFUND_NOT_ALLOWED", 409),
)
pending_refund_payment = make_create_payment("REF-09 Create Pending Payment", "REF-09 setup.")
add_event(pending_refund_payment, "prerequest", set_order("ORDER-REF-PENDING"))
pending_refund_reject = clone_request("Create Refund", "REF-09 Refund Against Non-Success Payment Rejects")
pending_refund_reject["event"] = [e for e in pending_refund_reject.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("PAYMENT_NOT_REFUNDABLE", 409)}}
]

refund_collection = collection(
    "Mini Payment Gateway - Refund Scenarios",
    "Companion for docs/testing/scenarios/refund.md.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("REF-01 REF-02 REF-03 REF-04 Core Refund Flow", [clone_request("Create Payment"), clone_request("Payment Callback Success"), clone_request("Create Refund"), clone_request("Get Refund By Transaction"), clone_request("Get Refund By Refund Id"), clone_request("Refund Callback Success")]),
        folder("REF-05 Provider Refund Failed Callback", [refund_failed_payment, clone_request("Payment Callback Success", "REF-05 Finalize Payment Success"), clone_request("Create Refund", "REF-05 Create Refund Before Failed Callback"), refund_failed_callback]),
        folder("REF-06 Partial Refund Rejects", [partial_payment, clone_request("Payment Callback Success", "REF-06 Finalize Payment Success"), partial_refund]),
        folder("REF-07 Refund After 7-Day Window Rejects", [window_template]),
        folder("REF-08 Duplicate Refund Id Rules", [dup_payment, clone_request("Payment Callback Success", "REF-08 Finalize Payment Success"), clone_request("Create Refund", "REF-08 Create Initial Refund"), clone_request("Create Refund", "REF-08 Duplicate Refund Id Returns Existing Refund"), dup_refund_conflict]),
        folder("REF-09 Refund Against Non-Success Payment Rejects", [pending_refund_payment, pending_refund_reject]),
    ],
)


# Ops
ops_rotate = clone_request("Rotate Credential", "OPS-03 Rotate Credential")
add_event(
    ops_rotate,
    "prerequest",
    [
        "pm.environment.set('inactive_access_key', pm.environment.get('access_key') || '');",
        "pm.environment.set('inactive_merchant_secret', pm.environment.get('merchant_secret') || '');",
    ],
)
old_credential_payment = clone_request("Create Payment", "OPS-03 Old Credential No Longer Works")
add_event(
    old_credential_payment,
    "prerequest",
    sign_with(
        "pm.environment.get('inactive_merchant_secret') || ''",
        "pm.environment.get('merchant_id') || ''",
        "pm.environment.get('inactive_access_key') || ''",
        "new Date().toISOString()",
    ),
)
old_credential_payment["event"] = [e for e in old_credential_payment.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_INVALID_SIGNATURE")}}
]
ops_block_payment = clone_request("Create Payment", "OPS-01 Suspended Merchant Payment Blocked")
ops_block_payment["event"] = [e for e in ops_block_payment.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("MERCHANT_NOT_ACTIVE", 403)}}
]
ops_block_refund = request_item(
    "OPS-02 Disabled Merchant Refund Blocked",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "OPS-02.",
    body=json.dumps(
        {
            "original_transaction_id": "pay_placeholder",
            "refund_id": "{{refund_id}}",
            "refund_amount": "{{refund_amount}}",
            "reason": "Blocked while merchant is disabled",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("MERCHANT_NOT_ACTIVE", 403),
)

ops_collection = collection(
    "Mini Payment Gateway - Ops Scenarios",
    "Companion for docs/testing/scenarios/ops.md. Audit assertions still require log or DB inspection.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("OPS-01 Suspend Merchant", [clone_request("Suspend Merchant", "OPS-01 Suspend Merchant"), ops_block_payment]),
        folder("OPS-02 Disable Merchant", [clone_request("Disable Merchant", "OPS-02 Disable Merchant"), ops_block_refund]),
        folder("OPS-03 Credential Rotation", [ops_rotate, clone_request("Create Payment", "OPS-03 New Credential Still Works"), old_credential_payment]),
    ],
)


# Reconciliation
refund_mismatch_payment = make_create_payment("REC-02R Create Payment For Refund Mismatch", "REC-02R setup.")
add_event(refund_mismatch_payment, "prerequest", set_order("ORDER-REC-REFUND"))
refund_mismatch_callback = request_item(
    "REC-02R Refund Callback Amount Mismatch",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/refund",
    "REC-02R.",
    body=json.dumps(
        {
            "external_reference": "bank-refund-rec-{{now_iso}}",
            "refund_transaction_id": "{{refund_transaction_id}}",
            "status": "SUCCESS",
            "amount": "{{reconciliation_mismatch_amount}}",
            "processed_at": "{{now_iso}}",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "refund-rec-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=[
        "pm.test('Refund mismatch callback returns 200', function () { pm.response.to.have.status(200); });",
        "const data = pm.response.json();",
        "if (data.reconciliation_record_id) { pm.environment.set('reconciliation_record_id', data.reconciliation_record_id); }",
    ],
)
rec_late_payment = make_create_payment("REC-01 Create Short-TTL Payment", "REC-01 setup.", ttl="1")
add_event(rec_late_payment, "prerequest", set_order("ORDER-REC-LATE"))
rec_late_callback = clone_request("Payment Callback Success", "REC-01 Late Success Callback After Expiration (Template)")
rec_late_callback["request"]["description"] = "REC-01 template. Run after the payment is already EXPIRED."

reconciliation_collection = collection(
    "Mini Payment Gateway - Reconciliation Scenarios",
    "Companion for docs/testing/scenarios/reconciliation.md.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT),
        folder("REC-02 Payment Callback Amount Mismatch", [clone_request("Create Payment For Reconciliation Scenario", "REC-02 Create Payment For Amount Mismatch"), clone_request("Payment Callback Mismatch", "REC-02 Payment Callback Amount Mismatch"), clone_request("List Reconciliation Records", "REC-02 List Reconciliation Records"), clone_request("Get Reconciliation Record", "REC-02 Get Reconciliation Record"), clone_request("Resolve Reconciliation Record", "REC-05 Resolve Reconciliation Record")]),
        folder("REC-02R Refund Callback Amount Mismatch", [refund_mismatch_payment, clone_request("Payment Callback Success", "REC-02R Finalize Payment Success"), clone_request("Create Refund", "REC-02R Create Refund"), refund_mismatch_callback, clone_request("List Reconciliation Records", "REC-02R List Reconciliation Records"), clone_request("Get Reconciliation Record", "REC-02R Get Reconciliation Record"), clone_request("Resolve Reconciliation Record", "REC-02R Resolve Reconciliation Record")]),
        folder("REC-01 Late Success Callback After Expiration", [rec_late_payment, rec_late_callback, clone_request("List Reconciliation Records", "REC-01 List Reconciliation Records"), clone_request("Get Reconciliation Record", "REC-01 Get Reconciliation Record"), clone_request("Resolve Reconciliation Record", "REC-01 Resolve Reconciliation Record")]),
    ],
)


# Webhook
webhook_failed = request_item(
    "WH-02 Payment Failure Creates Webhook Event",
    "POST",
    "{{baseUrl}}/v1/provider/callbacks/payment",
    "WH-02.",
    body=json.dumps(
        {
            "external_reference": "bank-fail-{{now_iso}}",
            "transaction_reference": "{{payment_transaction_id}}",
            "status": "FAILED",
            "amount": "{{payment_amount}}",
            "failed_reason_code": "BANK_DECLINED",
            "failed_reason_message": "Simulated failure",
            "raw_payload": {"provider": "SIMULATOR", "trace_id": "webhook-fail-{{now_iso}}"},
            "source_type": "{{provider_source_type}}",
        }
    ),
    headers=content_json_header(),
    tests=["pm.test('Payment failure callback returns 200', function () { pm.response.to.have.status(200); });"],
)
webhook_expire = make_create_payment("WH-03 Create Short-TTL Payment", "WH-03 setup.", ttl="1")
add_event(webhook_expire, "prerequest", set_order("ORDER-WH-EXP"))
webhook_refund_payment = make_create_payment("WH-04 Create Payment For Refund Webhook", "WH-04 setup.")
add_event(webhook_refund_payment, "prerequest", set_order("ORDER-WH-REFUND"))
wh02_create = make_create_payment("WH-02 Create Payment For Failure Event", "WH-02 setup.")
add_event(wh02_create, "prerequest", set_order("ORDER-WH-FAIL"))
retry_path_create = clone_request("Create Payment", "Webhook Retry Path Create Payment")
add_event(retry_path_create, "prerequest", set_order("ORDER-WH-RETRY"))

webhook_collection = collection(
    "Mini Payment Gateway - Webhook Scenarios",
    "Companion for docs/testing/scenarios/webhook.md. Configure webhook_url before setup.",
    [
        clone_request("Health"),
        folder("Setup Active Merchant", SETUP_ACTIVE_MERCHANT, "Set webhook_url to a target that matches the delivery behavior you want to test."),
        folder("WH-01 Payment Success Creates Webhook Event And WH-05 2xx Delivery", [clone_request("Create Payment"), clone_request("Payment Callback Success", "WH-01 Payment Success Creates Webhook Event")]),
        folder("WH-02 Payment Failure Creates Webhook Event", [wh02_create, webhook_failed]),
        folder("WH-03 Payment Expiration Creates Webhook Event", [webhook_expire]),
        folder("WH-04 Refund Success Creates Webhook Event", [webhook_refund_payment, clone_request("Payment Callback Success", "WH-04 Finalize Payment Success"), clone_request("Create Refund", "WH-04 Create Refund"), clone_request("Refund Callback Success", "WH-04 Refund Success Creates Webhook Event")]),
        folder("WH-06 WH-07 WH-08 WH-09 Retry Behaviour", [retry_path_create, clone_request("Payment Callback Success", "Webhook Retry Path Callback Success")], "Use a failing, timeout, or unreachable webhook_url before setup."),
        folder("WH-10 Manual Retry", [clone_request("Manual Retry Failed Webhook Event", "WH-10 Manual Retry Failed Webhook Event")]),
    ],
)


# Happy path
hp_bad_sig = clone_request("Create Payment", "E2E-02 Invalid Signature During Duplicate Flow")
add_event(hp_bad_sig, "prerequest", ["pm.request.headers.upsert({ key: 'X-Signature', value: 'tampered-signature' });"])
hp_bad_sig["event"] = [e for e in hp_bad_sig.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("AUTH_INVALID_SIGNATURE")}}
]
hp_late_payment = make_create_payment("E2E-03 Create Short-TTL Payment", "E2E-03 setup.", ttl="1")
add_event(hp_late_payment, "prerequest", set_order("ORDER-E2E-LATE"))
hp_late_callback = clone_request("Payment Callback Success", "E2E-03 Late Success Callback (Template)")
hp_late_callback["request"]["description"] = "E2E-03 template. Send only after the payment is already EXPIRED."
hp_block_payment = clone_request("Create Payment", "E2E-04 Suspended Merchant Payment Blocked")
hp_block_payment["event"] = [e for e in hp_block_payment.get("event", []) if e["listen"] != "test"] + [
    {"listen": "test", "script": {"type": "text/javascript", "exec": error_tests("MERCHANT_NOT_ACTIVE", 403)}}
]
hp_block_refund = request_item(
    "E2E-04 Suspended Merchant Refund Blocked",
    "POST",
    "{{baseUrl}}/v1/refunds",
    "E2E-04.",
    body=json.dumps(
        {
            "original_transaction_id": "{{payment_transaction_id}}",
            "refund_id": "{{refund_id}}",
            "refund_amount": "{{refund_amount}}",
            "reason": "Blocked after suspend",
        }
    ),
    headers=content_json_header(),
    tests=error_tests("MERCHANT_NOT_ACTIVE", 403),
)

happy_collection = collection(
    "Mini Payment Gateway - Happy Path Scenarios",
    "Companion for docs/testing/scenarios/happy-path.md.",
    [
        clone_request("Health"),
        folder("E2E-01 Merchant Onboarding To Successful Payment And Refund", SETUP_ACTIVE_MERCHANT + [clone_request("Create Payment"), clone_request("Get Payment By Transaction"), clone_request("Get Payment By Order"), clone_request("Payment Callback Success"), clone_request("Create Refund"), clone_request("Get Refund By Transaction"), clone_request("Get Refund By Refund Id"), clone_request("Refund Callback Success"), clone_request("List Reconciliation Records", "List Reconciliation Records (Optional Ops Review)")]),
        folder("E2E-02 Duplicate And Idempotency Path", [make_create_payment("E2E-02 Create Payment", "E2E-02 setup."), clone_request("Create Payment", "E2E-02 Duplicate Identical Request"), copy.deepcopy(duplicate_diff) | {"name": "E2E-02 Duplicate Different Amount"}, hp_bad_sig, clone_request("Payment Callback Success", "E2E-02 Finalize Payment Success"), success_retry]),
        folder("E2E-03 Late Callback Reconciliation Path", [hp_late_payment, hp_late_callback, clone_request("List Reconciliation Records", "E2E-03 List Reconciliation Records"), clone_request("Get Reconciliation Record", "E2E-03 Get Reconciliation Record"), clone_request("Resolve Reconciliation Record", "E2E-03 Resolve Reconciliation Record")]),
        folder("E2E-04 Webhook Retry And Manual Retry Path", [clone_request("Manual Retry Failed Webhook Event", "E2E-04 Manual Retry Failed Webhook Event"), clone_request("Suspend Merchant", "E2E-04 Suspend Merchant"), hp_block_payment, hp_block_refund]),
    ],
)


COLLECTIONS = {
    "auth.collection.json": auth_collection,
    "callback.collection.json": callback_collection,
    "happy-path.collection.json": happy_collection,
    "merchant.collection.json": merchant_collection,
    "ops.collection.json": ops_collection,
    "payment.collection.json": payment_collection,
    "reconciliation.collection.json": reconciliation_collection,
    "refund.collection.json": refund_collection,
    "webhook.collection.json": webhook_collection,
}


for filename, payload in COLLECTIONS.items():
    with (SCENARIO_DIR / filename).open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


existing_keys = {value["key"] for value in env["values"]}
for key, value, value_type in [
    ("inactive_access_key", "", "default"),
    ("inactive_merchant_secret", "", "secret"),
    ("other_merchant_id", "", "default"),
    ("other_access_key", "", "default"),
    ("other_merchant_secret", "", "secret"),
    ("unknown_merchant_id", "", "default"),
]:
    if key not in existing_keys:
        env["values"].append({"key": key, "value": value, "type": value_type, "enabled": True})

with ENV_PATH.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(env, f, indent=2, ensure_ascii=False)
    f.write("\n")


print("Generated", ", ".join(sorted(COLLECTIONS)))
