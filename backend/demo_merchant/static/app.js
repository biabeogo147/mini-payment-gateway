const state = { configured: false, order: null, pollTimer: null, countdownTimer: null };

const $ = (id) => document.getElementById(id);

$("setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/api/setup", {
      method: "PUT",
      body: {
        merchant_id: $("merchant-id").value.trim(),
        access_key: $("access-key").value.trim(),
        secret_key: $("secret-key").value,
      },
    });
    state.configured = true;
    $("secret-key").value = "";
    $("create-order").disabled = false;
    $("connection-state").textContent = `Đã kết nối ${result.merchant_id}`;
    $("connection-state").className = "status-pill success-state";
    toast("Đã lưu credential ở demo merchant backend.");
  } catch (error) {
    toast(error.message, true);
  }
});

$("order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  try {
    state.order = await api("/api/orders", {
      method: "POST",
      body: {
        amount: Number($("amount").value),
        description: $("description").value.trim(),
        ttl_seconds: Number($("ttl").value),
      },
    });
    renderOrder();
    startPolling();
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(false);
  }
});

$("simulate-success").addEventListener("click", () => simulate("SUCCESS"));
$("simulate-failed").addEventListener("click", () => simulate("FAILED"));

async function simulate(status) {
  if (!state.order) return;
  setSimulationBusy(true);
  try {
    state.order = await api(`/api/orders/${encodeURIComponent(state.order.order_id)}/simulate-result`, {
      method: "POST",
      body: { status },
    });
    renderOrder();
    toast("Ngân hàng đã gửi callback. Đang chờ gateway gửi webhook tới merchant.");
  } catch (error) {
    toast(error.message, true);
    setSimulationBusy(false);
  }
}

function startPolling() {
  clearInterval(state.pollTimer);
  clearInterval(state.countdownTimer);
  state.pollTimer = setInterval(refreshOrder, 1000);
  state.countdownTimer = setInterval(renderCountdown, 1000);
  renderCountdown();
}

async function refreshOrder() {
  if (!state.order) return;
  try {
    state.order = await api(`/api/orders/${encodeURIComponent(state.order.order_id)}`);
    renderOrder();
    if (["SUCCESS", "FAILED", "EXPIRED"].includes(state.order.status)) {
      clearInterval(state.pollTimer);
      clearInterval(state.countdownTimer);
    }
  } catch (error) {
    toast(error.message, true);
  }
}

function renderOrder() {
  const order = state.order;
  if (!order) return;
  $("empty-checkout").hidden = true;
  $("active-checkout").hidden = false;
  $("order-id").textContent = order.order_id;
  $("payment-amount").textContent = formatMoney(order.amount);
  $("qr-reference").textContent = order.qr_reference || "N/A";
  $("transaction-id").textContent = order.transaction_id;
  $("qr-image").src = order.qr_image_base64 || "";
  $("payment-status").textContent = order.status;
  $("payment-status").className = `status-pill ${order.status.toLowerCase()}`;

  const bankStep = $("bank-step");
  const webhookStep = $("webhook-step");
  if (order.notification_state === "AWAITING_WEBHOOK" || order.notification_state === "WEBHOOK_RECEIVED") {
    bankStep.className = "timeline-step done";
    bankStep.querySelector("p").textContent = "Callback đã được gateway chấp nhận.";
  }
  if (order.notification_state === "WEBHOOK_RECEIVED") {
    webhookStep.className = `timeline-step done ${order.status === "FAILED" ? "failed-step" : ""}`;
    webhookStep.querySelector("p").textContent = `Đã nhận ${order.webhook_event_id}.`;
  }

  const messages = {
    PENDING: [
      order.notification_state === "AWAITING_WEBHOOK" ? "Đang chờ gateway thông báo" : "Chờ thanh toán",
      order.notification_state === "AWAITING_WEBHOOK"
        ? "Ngân hàng đã phản hồi, đang chờ webhook tới merchant."
        : "Quét mã bằng ứng dụng ngân hàng.",
    ],
    SUCCESS: ["Thanh toán thành công", "Merchant đã nhận webhook xác nhận giao dịch."],
    FAILED: ["Thanh toán thất bại", order.failed_reason || "Ngân hàng từ chối giao dịch."],
    EXPIRED: ["Giao dịch đã hết hạn", "Vui lòng tạo payment mới."],
  };
  [$("status-title").textContent, $("status-message").textContent] = messages[order.status] || messages.PENDING;
  setSimulationBusy(order.notification_state === "AWAITING_WEBHOOK" || order.status !== "PENDING");
  renderCountdown();
}

function renderCountdown() {
  if (!state.order) return;
  const remaining = Math.max(0, Math.floor((new Date(state.order.expire_at).getTime() - Date.now()) / 1000));
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");
  $("countdown").textContent = `${minutes}:${seconds}`;
}

function setBusy(busy) {
  $("create-order").disabled = busy || !state.configured;
  $("create-order").textContent = busy ? "Đang tạo..." : "Tạo payment và QR";
}

function setSimulationBusy(busy) {
  $("simulate-success").disabled = busy;
  $("simulate-failed").disabled = busy;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

function formatMoney(value) {
  return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(Number(value));
}

function toast(message, isError = false) {
  const element = $("toast");
  element.textContent = message;
  element.className = `toast ${isError ? "toast-error" : ""}`;
  element.hidden = false;
  setTimeout(() => { element.hidden = true; }, 4500);
}
