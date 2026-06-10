import type {
  DashboardCharts,
  PaymentAmountChartPoint,
  PaymentStatusChartPoint,
  RefundCountChartPoint,
  WebhookStatusChartPoint,
} from "../common/api";
import { formatMoney } from "../common/format";

export type ChartTone = "good" | "warn" | "danger" | "muted" | "info";

export interface StackedChartSegment {
  key: string;
  label: string;
  value: number;
  percent: number;
  tone: ChartTone;
}

export interface StackedChartRow {
  date: string;
  label: string;
  total: number;
  segments: StackedChartSegment[];
}

export interface AmountTrendPoint {
  date: string;
  label: string;
  value: number;
  displayValue: string;
  ratio: number;
}

export interface AmountTrend {
  points: AmountTrendPoint[];
  maxValue: number;
  totalValue: number;
}

export interface VolumeChartPoint {
  date: string;
  label: string;
  value: number;
  ratio: number;
}

export interface VolumeChart {
  points: VolumeChartPoint[];
  maxValue: number;
  totalValue: number;
}

export interface WebhookHealthRow extends StackedChartRow {
  openCount: number;
}

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  timeZone: "UTC",
});

export function formatChartDateLabel(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return dateFormatter.format(date);
}

export function buildPaymentStatusBars(rows: PaymentStatusChartPoint[]): StackedChartRow[] {
  return rows.map((row) => {
    const total = row.pending + row.success + row.failed + row.expired;
    return {
      date: row.date,
      label: formatChartDateLabel(row.date),
      total,
      segments: [
        segment("success", "Success", row.success, total, "good"),
        segment("pending", "Pending", row.pending, total, "warn"),
        segment("failed", "Failed", row.failed, total, "danger"),
        segment("expired", "Expired", row.expired, total, "muted"),
      ],
    };
  });
}

export function buildAmountTrend(rows: PaymentAmountChartPoint[]): AmountTrend {
  const values = rows.map((row) => normalizeNumber(row.amount));
  const maxValue = max(values);
  const points = rows.map((row, index) => {
    const value = values[index] ?? 0;
    return {
      date: row.date,
      label: formatChartDateLabel(row.date),
      value,
      displayValue: formatMoney(value),
      ratio: maxValue > 0 ? value / maxValue : 0,
    };
  });

  return {
    points,
    maxValue,
    totalValue: values.reduce((total, value) => total + value, 0),
  };
}

export function buildRefundVolume(rows: RefundCountChartPoint[]): VolumeChart {
  const values = rows.map((row) => normalizeNumber(row.count));
  const maxValue = max(values);
  return {
    points: rows.map((row, index) => {
      const value = values[index] ?? 0;
      return {
        date: row.date,
        label: formatChartDateLabel(row.date),
        value,
        ratio: maxValue > 0 ? value / maxValue : 0,
      };
    }),
    maxValue,
    totalValue: values.reduce((total, value) => total + value, 0),
  };
}

export function buildWebhookHealth(rows: WebhookStatusChartPoint[]): WebhookHealthRow[] {
  return rows.map((row) => {
    const total = row.pending + row.delivered + row.failed;
    return {
      date: row.date,
      label: formatChartDateLabel(row.date),
      total,
      openCount: row.pending + row.failed,
      segments: [
        segment("delivered", "Delivered", row.delivered, total, "good"),
        segment("pending", "Pending", row.pending, total, "warn"),
        segment("failed", "Failed", row.failed, total, "danger"),
      ],
    };
  });
}

export function hasAnyDashboardChartData(charts: DashboardCharts) {
  const paymentTotal = buildPaymentStatusBars(charts.payment_status_by_day).reduce(
    (total, row) => total + row.total,
    0,
  );
  const amountTotal = buildAmountTrend(charts.successful_payment_amount_by_day).totalValue;
  const refundTotal = buildRefundVolume(charts.refund_count_by_day).totalValue;
  const webhookTotal = buildWebhookHealth(charts.webhook_status_by_day).reduce(
    (total, row) => total + row.total,
    0,
  );
  return paymentTotal + amountTotal + refundTotal + webhookTotal > 0;
}

function segment(
  key: string,
  label: string,
  value: number,
  total: number,
  tone: ChartTone,
): StackedChartSegment {
  return {
    key,
    label,
    value,
    percent: total > 0 ? (value / total) * 100 : 0,
    tone,
  };
}

function normalizeNumber(value: string | number) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) {
    return 0;
  }
  return numeric;
}

function max(values: number[]) {
  return values.reduce((current, value) => Math.max(current, value), 0);
}
