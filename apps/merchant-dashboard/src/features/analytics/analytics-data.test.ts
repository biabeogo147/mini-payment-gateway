import { describe, expect, it } from "vitest";

import type { MerchantAnalyticsResponse } from "../common/api";
import { buildAnalyticsViewModel, buildDrilldownHref } from "./analytics-data";

const response: MerchantAnalyticsResponse = {
  range: {
    days: 7,
    start_date: "2026-06-04",
    end_date: "2026-06-10",
  },
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
      {
        date: "2026-06-04",
        pending: 0,
        refunded: 1,
        failed: 0,
        count: 1,
        amount: "125000",
      },
      {
        date: "2026-06-05",
        pending: 0,
        refunded: 0,
        failed: 1,
        count: 1,
        amount: "0",
      },
    ],
    webhook_by_day: [
      {
        date: "2026-06-04",
        pending: 0,
        delivered: 2,
        failed: 0,
        total: 2,
        delivery_rate: 100,
      },
      {
        date: "2026-06-05",
        pending: 1,
        delivered: 0,
        failed: 1,
        total: 2,
        delivery_rate: 0,
      },
    ],
  },
  attention: {
    failed_or_expired_payments: 2,
    refund_failures: 1,
    open_webhooks: 2,
    top_webhook_event_types: [
      { event_type: "payment.expired", count: 2, pending: 1, failed: 1 },
    ],
  },
};

describe("merchant analytics data", () => {
  it("builds chart-ready rows with formatted labels and numeric amounts", () => {
    const viewModel = buildAnalyticsViewModel(response);

    expect(viewModel.rangeLabel).toBe("04 Jun - 10 Jun");
    expect(viewModel.hasActivity).toBe(true);
    expect(viewModel.paymentSeries[0]).toMatchObject({
      label: "04 Jun",
      successfulAmount: 450000,
      successfulAmountLabel: "450.000 ₫",
      successRate: 50,
    });
    expect(viewModel.refundSeries[0].amountLabel).toBe("125.000 ₫");
    expect(viewModel.webhookSeries[1].deliveryRateLabel).toBe("0%");
    expect(viewModel.attentionItems.map((item) => item.value)).toEqual([2, 1, 2]);
  });

  it("detects empty analytics responses", () => {
    const empty = buildAnalyticsViewModel({
      ...response,
      totals: {
        payment_count: 0,
        successful_payment_count: 0,
        successful_payment_amount: "0",
        success_rate: 0,
        refund_count: 0,
        refunded_amount: "0",
        webhook_count: 0,
        webhook_delivery_rate: 0,
      },
      attention: {
        failed_or_expired_payments: 0,
        refund_failures: 0,
        open_webhooks: 0,
        top_webhook_event_types: [],
      },
      series: {
        payment_by_day: [],
        refund_by_day: [],
        webhook_by_day: [],
      },
    });

    expect(empty.hasActivity).toBe(false);
  });

  it("builds explorer drill-down hrefs with full-day date boundaries", () => {
    expect(buildDrilldownHref("payments", "FAILED", "2026-06-04")).toBe(
      "/payments?status=FAILED&date_from=2026-06-04T00%3A00&date_to=2026-06-04T23%3A59",
    );
    expect(buildDrilldownHref("webhooks", "FAILED", "2026-06-04", "payment.expired")).toBe(
      "/webhooks?status=FAILED&date_from=2026-06-04T00%3A00&date_to=2026-06-04T23%3A59&event_type=payment.expired",
    );
  });
});
