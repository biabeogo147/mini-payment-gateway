import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { MerchantAnalyticsResponse } from "../common/api";
import { getMerchantAnalytics } from "../common/api";
import { AnalyticsPage } from "./analytics-page";

vi.mock("../common/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../common/api")>();
  return {
    ...actual,
    getMerchantAnalytics: vi.fn(),
  };
});

const analytics: MerchantAnalyticsResponse = {
  range: { days: 30, start_date: "2026-05-12", end_date: "2026-06-10" },
  totals: {
    payment_count: 6,
    successful_payment_count: 3,
    successful_payment_amount: "575000",
    success_rate: 50,
    refund_count: 2,
    refunded_amount: "125000",
    webhook_count: 4,
    webhook_delivery_rate: 50,
  },
  series: {
    payment_by_day: [
      {
        date: "2026-06-04",
        pending: 1,
        success: 2,
        failed: 1,
        expired: 0,
        total: 4,
        successful_amount: "450000",
        success_rate: 50,
      },
      {
        date: "2026-06-05",
        pending: 0,
        success: 1,
        failed: 0,
        expired: 1,
        total: 2,
        successful_amount: "125000",
        success_rate: 50,
      },
    ],
    refund_by_day: [
      { date: "2026-06-04", pending: 0, refunded: 1, failed: 0, count: 1, amount: "125000" },
      { date: "2026-06-05", pending: 0, refunded: 0, failed: 1, count: 1, amount: "0" },
    ],
    webhook_by_day: [
      { date: "2026-06-04", pending: 0, delivered: 2, failed: 0, total: 2, delivery_rate: 100 },
      { date: "2026-06-05", pending: 1, delivered: 0, failed: 1, total: 2, delivery_rate: 0 },
    ],
  },
  attention: {
    failed_or_expired_payments: 2,
    refund_failures: 1,
    open_webhooks: 2,
    top_webhook_event_types: [{ event_type: "payment.expired", count: 2, pending: 1, failed: 1 }],
  },
};

describe("AnalyticsPage", () => {
  it("renders six interactive chart cards and readable data tables", async () => {
    vi.mocked(getMerchantAnalytics).mockResolvedValue(analytics);

    renderAnalytics();

    expect(await screen.findByText("Successful amount trend")).toBeTruthy();
    expect(screen.getByText("Payment status by day")).toBeTruthy();
    expect(screen.getAllByText("Payment success rate").length).toBeGreaterThan(0);
    expect(screen.getByText("Refund count and amount")).toBeTruthy();
    expect(screen.getByText("Webhook delivery health")).toBeTruthy();
    expect(screen.getByText("Attention breakdown")).toBeTruthy();

    const amountCard = screen.getByText("Successful amount trend").closest(".content-card") as HTMLElement;
    fireEvent.click(within(amountCard).getByRole("button", { name: "View data" }));
    expect(within(amountCard).getByText("450.000 ₫")).toBeTruthy();
  });

  it("uses 30 days by default and refetches when the range changes", async () => {
    vi.mocked(getMerchantAnalytics).mockResolvedValue(analytics);

    renderAnalytics();

    expect(await screen.findByText("12 May - 10 Jun")).toBeTruthy();
    expect(vi.mocked(getMerchantAnalytics).mock.calls[0][0]).toBe(30);
    expect(screen.getByRole("button", { name: "30d" }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "7d" }));

    const calls = vi.mocked(getMerchantAnalytics).mock.calls;
    expect(calls[calls.length - 1]?.[0]).toBe(7);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "7d" }).getAttribute("aria-pressed")).toBe("true");
    });
  });

  it("renders loading, error, and drill-down links", async () => {
    vi.mocked(getMerchantAnalytics).mockImplementation(() => new Promise(() => undefined));

    const { unmount } = renderAnalytics();
    expect(screen.getByText("Loading analytics")).toBeTruthy();
    unmount();

    vi.mocked(getMerchantAnalytics).mockRejectedValue(new Error("analytics failed"));
    const failedRender = renderAnalytics();
    expect(await screen.findByText("analytics failed")).toBeTruthy();
    failedRender.unmount();

    vi.mocked(getMerchantAnalytics).mockResolvedValue(analytics);
    renderAnalytics();

    const failedPayments = await screen.findByRole("link", { name: "Inspect failed payments" });
    expect(failedPayments.getAttribute("href")).toContain("/payments?status=FAILED");
  });
});

function renderAnalytics() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter
      initialEntries={["/analytics"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <QueryClientProvider client={queryClient}>
        <AnalyticsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
