import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DashboardCharts, DashboardSummary } from "../common/api";
import { getDashboardCharts, getDashboardSummary } from "../common/api";
import { OverviewPage } from "./overview-page";

vi.mock("recharts", () => {
  throw new Error("Overview must not import Recharts; Analytics owns the heavy chart bundle.");
});

vi.mock("../common/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../common/api")>();
  return {
    ...actual,
    getDashboardCharts: vi.fn(),
    getDashboardSummary: vi.fn(),
  };
});

const summary: DashboardSummary = {
  payments_last_24h: 6,
  successful_payment_amount_last_24h: "450000",
  pending_payments: 2,
  refunds_last_24h: 1,
  open_webhook_events: 3,
};

const charts: DashboardCharts = {
  payment_status_by_day: [
    { date: "2026-06-03", pending: 1, success: 2, failed: 0, expired: 0 },
    { date: "2026-06-04", pending: 0, success: 4, failed: 1, expired: 1 },
  ],
  successful_payment_amount_by_day: [
    { date: "2026-06-03", amount: "125000" },
    { date: "2026-06-04", amount: "450000" },
  ],
  refund_count_by_day: [
    { date: "2026-06-03", count: 0 },
    { date: "2026-06-04", count: 1 },
  ],
  webhook_status_by_day: [
    { date: "2026-06-03", pending: 0, delivered: 2, failed: 0 },
    { date: "2026-06-04", pending: 2, delivered: 5, failed: 1 },
  ],
};

describe("OverviewPage visualizations", () => {
  it("renders the four visualization cards with accessible chart labels", async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(summary);
    vi.mocked(getDashboardCharts).mockResolvedValue(charts);

    renderOverview();

    expect(await screen.findByText("Payment status mix")).toBeTruthy();
    expect(screen.getByText("Successful amount trend")).toBeTruthy();
    expect(screen.getByText("Refund volume")).toBeTruthy();
    expect(screen.getByText("Webhook delivery health")).toBeTruthy();

    const amountCard = screen.getByText("Successful amount trend").closest(".content-card") as HTMLElement;
    expect(within(amountCard).getByText("450.000 ₫")).toBeTruthy();
    expect(within(amountCard).getByRole("button", { name: "View data" })).toBeTruthy();
  });

  it("renders loading and error states", async () => {
    vi.mocked(getDashboardSummary).mockImplementation(() => new Promise(() => undefined));
    vi.mocked(getDashboardCharts).mockImplementation(() => new Promise(() => undefined));

    const { unmount } = renderOverview();
    expect(screen.getByText("Loading dashboard")).toBeTruthy();
    unmount();

    vi.mocked(getDashboardSummary).mockRejectedValue(new Error("summary failed"));
    vi.mocked(getDashboardCharts).mockResolvedValue(charts);
    renderOverview();

    expect(await screen.findByText("summary failed")).toBeTruthy();
  });

  it("renders an explicit empty state when all chart series are zero", async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(summary);
    vi.mocked(getDashboardCharts).mockResolvedValue({
      payment_status_by_day: [{ date: "2026-06-04", pending: 0, success: 0, failed: 0, expired: 0 }],
      successful_payment_amount_by_day: [{ date: "2026-06-04", amount: "0" }],
      refund_count_by_day: [{ date: "2026-06-04", count: 0 }],
      webhook_status_by_day: [{ date: "2026-06-04", pending: 0, delivered: 0, failed: 0 }],
    });

    renderOverview();

    const emptyCard = await screen.findByText("No chart activity yet");
    expect(within(emptyCard.closest(".content-card") as HTMLElement).getByText(/Once payments/)).toBeTruthy();
  });
});

function renderOverview() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <OverviewPage />
    </QueryClientProvider>,
  );
}
