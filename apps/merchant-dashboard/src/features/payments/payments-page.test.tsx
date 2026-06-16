import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { PaymentDetail, PaymentListItem } from "../common/api";
import { getPaymentDetail, listPayments } from "../common/api";
import { PaymentsPage } from "./payments-page";

vi.mock("../common/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../common/api")>();
  return {
    ...actual,
    getPaymentDetail: vi.fn(),
    listPayments: vi.fn(),
  };
});

const payment: PaymentListItem = {
  transaction_id: "pay_demo_001",
  merchant_id: "m_demo_dashboard",
  merchant_name: "Demo Merchant",
  order_id: "ORDER-DEMO-001",
  amount: "125000.00",
  currency: "VND",
  status: "PENDING",
  expire_at: "2026-06-16T10:00:00Z",
  paid_at: null,
  created_at: "2026-06-16T09:00:00Z",
};

const detailWithoutQrImage: PaymentDetail = {
  ...payment,
  description: "Legacy payment",
  qr_reference: null,
  qr_content: "DEMOQR|m_demo_dashboard|ORDER-DEMO-001|125000.00",
  qr_image_url: null,
  qr_image_base64: null,
  external_reference: null,
  idempotency_key: "demo-pay_demo_001",
  failed_reason_code: null,
  failed_reason_message: null,
  callback_logs: [],
  refunds: [],
};

describe("PaymentsPage QR payload", () => {
  it("uses a full-width payload layout when a legacy payment has no QR image", async () => {
    vi.mocked(listPayments).mockResolvedValue({ payments: [payment] });
    vi.mocked(getPaymentDetail).mockResolvedValue(detailWithoutQrImage);

    renderPayments();

    const payloadCard = (await screen.findByText("QR payload")).closest(".content-card") as HTMLElement;
    const payloadGrid = within(payloadCard).getByText(/DEMOQR/).closest(".qr-payload-grid") as HTMLElement;

    expect(payloadGrid.classList.contains("qr-payload-grid-single")).toBe(true);
    expect(within(payloadCard).queryByRole("img", { name: /QR code/ })).toBeNull();
  });
});

function renderPayments() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter
      initialEntries={["/payments"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <QueryClientProvider client={queryClient}>
        <PaymentsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
