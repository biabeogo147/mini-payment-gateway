import type {
  AnalyticsDays,
  MerchantAnalyticsResponse,
  MerchantPaymentAnalyticsPoint,
  MerchantRefundAnalyticsPoint,
  MerchantWebhookAnalyticsPoint,
} from "../common/api";
import { formatMoney, formatPercent } from "../common/format";
import { formatChartDateLabel } from "../dashboard/chart-data";

export type AnalyticsDrilldownTarget = "payments" | "refunds" | "webhooks";

export interface PaymentAnalyticsRow extends MerchantPaymentAnalyticsPoint {
  label: string;
  successfulAmount: number;
  successfulAmountLabel: string;
  successRate: number;
  successRateLabel: string;
}

export interface RefundAnalyticsRow extends MerchantRefundAnalyticsPoint {
  label: string;
  amountValue: number;
  amountLabel: string;
}

export interface WebhookAnalyticsRow extends MerchantWebhookAnalyticsPoint {
  label: string;
  deliveryRate: number;
  deliveryRateLabel: string;
}

export interface AnalyticsAttentionItem {
  key: string;
  label: string;
  value: number;
  tone: "danger" | "warn" | "info";
  href: string;
  actionLabel: string;
}

export interface AnalyticsTopWebhookEventType {
  eventType: string;
  count: number;
  pending: number;
  failed: number;
  href: string;
}

export interface AnalyticsViewModel {
  days: AnalyticsDays;
  rangeLabel: string;
  hasActivity: boolean;
  totals: {
    paymentCount: number;
    successfulPaymentCount: number;
    successfulAmountLabel: string;
    successRateLabel: string;
    refundCount: number;
    refundedAmountLabel: string;
    webhookCount: number;
    webhookDeliveryRateLabel: string;
  };
  paymentSeries: PaymentAnalyticsRow[];
  refundSeries: RefundAnalyticsRow[];
  webhookSeries: WebhookAnalyticsRow[];
  attentionItems: AnalyticsAttentionItem[];
  topWebhookEventTypes: AnalyticsTopWebhookEventType[];
}

export function buildAnalyticsViewModel(response: MerchantAnalyticsResponse): AnalyticsViewModel {
  const paymentSeries = response.series.payment_by_day.map((row) => {
    const successfulAmount = normalizeNumber(row.successful_amount);
    return {
      ...row,
      label: formatChartDateLabel(row.date),
      successfulAmount,
      successfulAmountLabel: formatChartMoney(successfulAmount),
      successRate: normalizeNumber(row.success_rate),
      successRateLabel: formatPercent(normalizeNumber(row.success_rate)),
    };
  });

  const refundSeries = response.series.refund_by_day.map((row) => {
    const amountValue = normalizeNumber(row.amount);
    return {
      ...row,
      label: formatChartDateLabel(row.date),
      amountValue,
      amountLabel: formatChartMoney(amountValue),
    };
  });

  const webhookSeries = response.series.webhook_by_day.map((row) => ({
    ...row,
    label: formatChartDateLabel(row.date),
    deliveryRate: normalizeNumber(row.delivery_rate),
    deliveryRateLabel: formatPercent(normalizeNumber(row.delivery_rate)),
  }));

  const totals = {
    paymentCount: response.totals.payment_count,
    successfulPaymentCount: response.totals.successful_payment_count,
    successfulAmountLabel: formatChartMoney(response.totals.successful_payment_amount),
    successRateLabel: formatPercent(response.totals.success_rate),
    refundCount: response.totals.refund_count,
    refundedAmountLabel: formatChartMoney(response.totals.refunded_amount),
    webhookCount: response.totals.webhook_count,
    webhookDeliveryRateLabel: formatPercent(response.totals.webhook_delivery_rate),
  };

  const attentionItems: AnalyticsAttentionItem[] = [
    {
      key: "payments",
      label: "Failed or expired payments",
      value: response.attention.failed_or_expired_payments,
      tone: "danger",
      href: "/payments?status=FAILED",
      actionLabel: "Inspect failed payments",
    },
    {
      key: "refunds",
      label: "Refund failures",
      value: response.attention.refund_failures,
      tone: "warn",
      href: "/refunds?status=REFUND_FAILED",
      actionLabel: "Inspect failed refunds",
    },
    {
      key: "webhooks",
      label: "Open webhooks",
      value: response.attention.open_webhooks,
      tone: "info",
      href: "/webhooks?status=FAILED",
      actionLabel: "Inspect open webhooks",
    },
  ];
  const topWebhookEventTypes = response.attention.top_webhook_event_types.map((item) => ({
    eventType: item.event_type,
    count: item.count,
    pending: item.pending,
    failed: item.failed,
    href: `/webhooks?status=FAILED&event_type=${encodeURIComponent(item.event_type)}`,
  }));

  const hasActivity =
    totals.paymentCount +
      totals.refundCount +
      totals.webhookCount +
      attentionItems.reduce((sum, item) => sum + item.value, 0) >
    0;

  return {
    days: response.range.days,
    rangeLabel: `${formatChartDateLabel(response.range.start_date)} - ${formatChartDateLabel(
      response.range.end_date,
    )}`,
    hasActivity,
    totals,
    paymentSeries,
    refundSeries,
    webhookSeries,
    attentionItems,
    topWebhookEventTypes,
  };
}

export function buildDrilldownHref(
  target: AnalyticsDrilldownTarget,
  status: string,
  date: string,
  eventType?: string,
) {
  const params = new URLSearchParams();
  params.set("status", status);
  params.set("date_from", `${date}T00:00`);
  params.set("date_to", `${date}T23:59`);
  if (eventType) {
    params.set("event_type", eventType);
  }
  return `/${target}?${params.toString()}`;
}

export function formatChartMoney(value: string | number) {
  return formatMoney(value).replace(/\u00a0/g, " ");
}

function normalizeNumber(value: string | number) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) {
    return 0;
  }
  return numeric;
}
