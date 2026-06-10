import { describe, expect, it } from "vitest";

import type { DashboardCharts } from "../common/api";
import {
  buildAmountTrend,
  buildPaymentStatusBars,
  buildRefundVolume,
  buildWebhookHealth,
  formatChartDateLabel,
  hasAnyDashboardChartData,
} from "./chart-data";

const zeroCharts: DashboardCharts = {
  payment_status_by_day: [
    { date: "2026-06-03", pending: 0, success: 0, failed: 0, expired: 0 },
    { date: "2026-06-04", pending: 0, success: 0, failed: 0, expired: 0 },
  ],
  successful_payment_amount_by_day: [
    { date: "2026-06-03", amount: "0" },
    { date: "2026-06-04", amount: "0" },
  ],
  refund_count_by_day: [
    { date: "2026-06-03", count: 0 },
    { date: "2026-06-04", count: 0 },
  ],
  webhook_status_by_day: [
    { date: "2026-06-03", pending: 0, delivered: 0, failed: 0 },
    { date: "2026-06-04", pending: 0, delivered: 0, failed: 0 },
  ],
};

describe("merchant dashboard chart data", () => {
  it("formats API dates into compact day labels", () => {
    expect(formatChartDateLabel("2026-06-04")).toBe("04 Jun");
  });

  it("builds payment stacked totals and percentages without dropping statuses", () => {
    const rows = buildPaymentStatusBars([
      { date: "2026-06-04", pending: 1, success: 3, failed: 2, expired: 0 },
    ]);

    expect(rows[0].label).toBe("04 Jun");
    expect(rows[0].total).toBe(6);
    expect(rows[0].segments).toEqual([
      { key: "success", label: "Success", value: 3, percent: 50, tone: "good" },
      { key: "pending", label: "Pending", value: 1, percent: 16.666666666666664, tone: "warn" },
      { key: "failed", label: "Failed", value: 2, percent: 33.33333333333333, tone: "danger" },
      { key: "expired", label: "Expired", value: 0, percent: 0, tone: "muted" },
    ]);
  });

  it("normalizes amount strings and keeps zero max values safe", () => {
    const trend = buildAmountTrend([
      { date: "2026-06-03", amount: "bad-number" },
      { date: "2026-06-04", amount: "120000.50" },
    ]);

    expect(trend.maxValue).toBe(120000.5);
    expect(trend.points.map((point) => point.value)).toEqual([0, 120000.5]);
    expect(buildAmountTrend([{ date: "2026-06-04", amount: "0" }]).maxValue).toBe(0);
  });

  it("keeps refund and webhook transforms safe for empty series", () => {
    expect(buildRefundVolume(zeroCharts.refund_count_by_day).maxValue).toBe(0);

    const webhooks = buildWebhookHealth([
      { date: "2026-06-04", pending: 2, delivered: 5, failed: 1 },
    ]);
    expect(webhooks[0].total).toBe(8);
    expect(webhooks[0].openCount).toBe(3);
  });

  it("detects all-zero dashboard chart responses", () => {
    expect(hasAnyDashboardChartData(zeroCharts)).toBe(false);
    expect(
      hasAnyDashboardChartData({
        ...zeroCharts,
        successful_payment_amount_by_day: [{ date: "2026-06-04", amount: "1" }],
      }),
    ).toBe(true);
  });
});
