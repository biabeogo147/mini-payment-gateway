import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const APP_SOURCE = fs.readFileSync(
  new URL("../demo_merchant/static/app.js", import.meta.url),
  "utf8",
);

function createElement(id) {
  const paragraph = { textContent: "" };
  const strong = { textContent: "" };
  return {
    id,
    hidden: false,
    disabled: id === "create-order",
    value: "",
    textContent: "",
    className: "",
    src: "",
    listeners: {},
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    },
    querySelector(selector) {
      if (selector === "p") return paragraph;
      if (selector === "strong") return strong;
      return null;
    },
    paragraph,
    strong,
  };
}

function createHarness({ health = { status: "ok", configured: false, merchant_id: null } } = {}) {
  const ids = [
    "setup-form", "order-form", "merchant-id", "access-key", "secret-key",
    "create-order", "connection-state", "amount", "description", "ttl",
    "simulate-success", "simulate-failed", "new-order", "empty-checkout",
    "active-checkout", "order-id", "payment-amount", "qr-reference",
    "transaction-id", "qr-image", "payment-status", "bank-step", "webhook-step",
    "status-title", "status-message", "countdown", "toast",
    "demo-control-title", "demo-control-eyebrow",
  ];
  const elements = Object.fromEntries(ids.map((id) => [id, createElement(id)]));
  elements["active-checkout"].hidden = true;
  elements["new-order"].hidden = true;

  const context = vm.createContext({
    document: { getElementById: (id) => elements[id] },
    fetch: async (path) => ({
      ok: true,
      status: 200,
      json: async () => path === "/health" ? health : {},
    }),
    setInterval: () => 1,
    clearInterval: () => {},
    setTimeout: () => 1,
    console,
    Intl,
    Date,
    encodeURIComponent,
  });
  vm.runInContext(APP_SOURCE, context);

  return {
    elements,
    context,
    render(order) {
      vm.runInContext(`state.order = ${JSON.stringify(order)}; renderOrder();`, context);
    },
  };
}

function terminalOrder(status) {
  return {
    order_id: "DEMO-1001",
    transaction_id: "pay_demo_1001",
    amount: "100000",
    qr_reference: "PDEMO1001",
    qr_image_base64: "data:image/png;base64,UE5H",
    status,
    notification_state: "WEBHOOK_RECEIVED",
    webhook_event_id: `evt_${status.toLowerCase()}`,
    failed_reason: status === "FAILED" ? "Ngân hàng từ chối giao dịch." : null,
    expire_at: "2026-06-20T09:35:00Z",
  };
}

test("reload restores the in-memory merchant connection", async () => {
  const { elements } = createHarness({
    health: { status: "ok", configured: true, merchant_id: "m_demo" },
  });
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(elements["create-order"].disabled, false);
  assert.equal(elements["connection-state"].textContent, "Đã kết nối m_demo");
});

test("expired order states that no bank callback occurred", () => {
  const harness = createHarness();
  harness.render(terminalOrder("EXPIRED"));

  assert.equal(harness.elements["bank-step"].strong.textContent, "Không có callback ngân hàng");
  assert.equal(harness.elements["bank-step"].paragraph.textContent, "Payment hết hạn trước khi có phản hồi.");
  assert.match(harness.elements["bank-step"].className, /expired-step/);
  assert.equal(harness.elements["webhook-step"].strong.textContent, "Merchant nhận thông báo hết hạn");
});

test("failed order distinguishes a rejected payment from callback acceptance", () => {
  const harness = createHarness();
  harness.render(terminalOrder("FAILED"));

  assert.equal(harness.elements["bank-step"].strong.textContent, "Ngân hàng từ chối giao dịch");
  assert.equal(harness.elements["bank-step"].paragraph.textContent, "Callback FAILED đã được gateway xử lý.");
  assert.match(harness.elements["bank-step"].className, /failed-step/);
  assert.equal(harness.elements["webhook-step"].strong.textContent, "Merchant nhận kết quả thất bại");
});

test("new order action clears checkout but preserves merchant connection", () => {
  const harness = createHarness();
  vm.runInContext("state.configured = true", harness.context);
  harness.render(terminalOrder("SUCCESS"));

  const listener = harness.elements["new-order"].listeners.click;
  assert.equal(typeof listener, "function");
  listener();

  assert.equal(harness.elements["active-checkout"].hidden, true);
  assert.equal(harness.elements["empty-checkout"].hidden, false);
  assert.equal(harness.elements["create-order"].disabled, false);
  assert.equal(vm.runInContext("state.configured", harness.context), true);
  assert.equal(vm.runInContext("state.order", harness.context), null);
});
