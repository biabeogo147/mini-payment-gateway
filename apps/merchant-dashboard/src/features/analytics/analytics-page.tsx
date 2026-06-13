import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getMerchantAnalytics, type AnalyticsDays } from "../common/api";
import {
  ContentCard,
  EmptyState,
  ErrorCard,
  MetricCard,
  PageHeader,
} from "../common/ui";
import {
  buildAnalyticsViewModel,
  buildDrilldownHref,
  formatChartMoney,
  type AnalyticsViewModel,
  type PaymentAnalyticsRow,
  type RefundAnalyticsRow,
  type WebhookAnalyticsRow,
} from "./analytics-data";

const ranges: AnalyticsDays[] = [7, 30, 90];
const responsiveInitialDimension = { width: 640, height: 320 };

export function AnalyticsPage() {
  const [days, setDays] = useState<AnalyticsDays>(30);
  const analyticsQuery = useQuery({
    queryKey: ["merchant-analytics", days],
    queryFn: () => getMerchantAnalytics(days),
  });

  if (analyticsQuery.isLoading) {
    return (
      <section className="page-stack">
        <PageHeader
          eyebrow="Merchant analytics"
          title="Analytics"
          description="Interactive view of revenue, payment outcomes, refunds, and webhook delivery."
        />
        <ContentCard>
          <EmptyState
            title="Loading analytics"
            message="Preparing merchant-scoped chart data."
          />
        </ContentCard>
      </section>
    );
  }

  if (analyticsQuery.error instanceof Error) {
    return <ErrorCard title="Analytics unavailable" message={analyticsQuery.error.message} />;
  }

  const analytics = analyticsQuery.data;
  if (!analytics) {
    return <ErrorCard message="Analytics data is unavailable." />;
  }

  const viewModel = buildAnalyticsViewModel(analytics);

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Merchant analytics"
        title="Analytics"
        description="Interactive view of revenue, payment outcomes, refunds, and webhook delivery."
      />

      <div className="analytics-toolbar">
        <div>
          <span className="eyebrow">Range</span>
          <strong>{viewModel.rangeLabel}</strong>
        </div>
        <div className="segmented-control" aria-label="Analytics date range">
          {ranges.map((range) => (
            <button
              key={range}
              type="button"
              className={days === range ? "segmented-option segmented-option-active" : "segmented-option"}
              aria-pressed={days === range}
              onClick={() => setDays(range)}
            >
              {range}d
            </button>
          ))}
        </div>
      </div>

      <div className="metric-grid">
        <MetricCard
          label="Successful amount"
          value={viewModel.totals.successfulAmountLabel}
          hint={`${viewModel.totals.successfulPaymentCount} successful of ${viewModel.totals.paymentCount} payments`}
        />
        <MetricCard
          label="Payment success rate"
          value={viewModel.totals.successRateLabel}
          hint="Successful payments divided by total payments"
        />
        <MetricCard
          label="Refunded amount"
          value={viewModel.totals.refundedAmountLabel}
          hint={`${viewModel.totals.refundCount} refund records in range`}
        />
        <MetricCard
          label="Webhook delivery"
          value={viewModel.totals.webhookDeliveryRateLabel}
          hint={`${viewModel.totals.webhookCount} webhook events in range`}
        />
      </div>

      {!viewModel.hasActivity ? (
        <ContentCard title="Analytics activity">
          <EmptyState
            title="No analytics activity yet"
            message="Payments, refunds, and webhook events will appear here once this merchant has traffic."
          />
        </ContentCard>
      ) : null}

      <div className="analytics-grid">
        <SuccessfulAmountCard viewModel={viewModel} />
        <PaymentStatusCard rows={viewModel.paymentSeries} />
        <PaymentSuccessRateCard rows={viewModel.paymentSeries} />
        <RefundCard rows={viewModel.refundSeries} />
        <WebhookHealthCard rows={viewModel.webhookSeries} />
        <AttentionCard viewModel={viewModel} />
      </div>
    </section>
  );
}

function SuccessfulAmountCard(props: { viewModel: AnalyticsViewModel }) {
  return (
    <AnalyticsChartCard
      title="Successful amount trend"
      summary={props.viewModel.totals.successfulAmountLabel}
      tableHeaders={["Date", "Successful amount", "Success rate"]}
      tableRows={props.viewModel.paymentSeries.map((row) => [
        row.label,
        row.successfulAmountLabel,
        row.successRateLabel,
      ])}
    >
      <div className="recharts-panel" aria-label="Successful amount trend chart">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={1}
          minHeight={1}
          initialDimension={responsiveInitialDimension}
        >
          <AreaChart data={props.viewModel.paymentSeries}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" />
            <YAxis tickFormatter={(value) => formatCompactMoney(Number(value))} />
            <Tooltip
              formatter={(value) => [formatChartMoney(Number(value)), "Successful amount"]}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Area
              type="monotone"
              dataKey="successfulAmount"
              stroke="#23694b"
              fill="#dff1e7"
              strokeWidth={2}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </AnalyticsChartCard>
  );
}

function PaymentStatusCard(props: { rows: PaymentAnalyticsRow[] }) {
  const navigate = useNavigate();
  return (
    <AnalyticsChartCard
      title="Payment status by day"
      summary={`${props.rows.reduce((sum, row) => sum + row.total, 0)} payments`}
      tableHeaders={["Date", "Success", "Pending", "Failed", "Expired", "Total"]}
      tableRows={props.rows.map((row) => [
        row.label,
        row.success,
        row.pending,
        row.failed,
        row.expired,
        row.total,
      ])}
    >
      <div className="recharts-panel" aria-label="Payment status by day chart">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={1}
          minHeight={1}
          initialDimension={responsiveInitialDimension}
        >
          <ComposedChart data={props.rows}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar
              dataKey="success"
              name="Success"
              stackId="payments"
              fill="#23694b"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("payments", "SUCCESS", point.payload.date));
                }
              }}
            />
            <Bar
              dataKey="pending"
              name="Pending"
              stackId="payments"
              fill="#b6832d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("payments", "PENDING", point.payload.date));
                }
              }}
            />
            <Bar
              dataKey="failed"
              name="Failed"
              stackId="payments"
              fill="#b5483d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("payments", "FAILED", point.payload.date));
                }
              }}
            />
            <Bar
              dataKey="expired"
              name="Expired"
              stackId="payments"
              fill="#87919f"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("payments", "EXPIRED", point.payload.date));
                }
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </AnalyticsChartCard>
  );
}

function PaymentSuccessRateCard(props: { rows: PaymentAnalyticsRow[] }) {
  return (
    <AnalyticsChartCard
      title="Payment success rate"
      summary={`${latest(props.rows)?.successRateLabel ?? "0%"}`}
      tableHeaders={["Date", "Success rate", "Successful", "Total"]}
      tableRows={props.rows.map((row) => [
        row.label,
        row.successRateLabel,
        row.success,
        row.total,
      ])}
    >
      <div className="recharts-panel" aria-label="Payment success rate chart">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={1}
          minHeight={1}
          initialDimension={responsiveInitialDimension}
        >
          <LineChart data={props.rows}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" />
            <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
            <Tooltip formatter={(value) => [`${Math.round(Number(value))}%`, "Success rate"]} />
            <Line
              type="monotone"
              dataKey="successRate"
              name="Success rate"
              stroke="#315d92"
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </AnalyticsChartCard>
  );
}

function RefundCard(props: { rows: RefundAnalyticsRow[] }) {
  const navigate = useNavigate();
  return (
    <AnalyticsChartCard
      title="Refund count and amount"
      summary={`${props.rows.reduce((sum, row) => sum + row.count, 0)} refunds`}
      tableHeaders={["Date", "Refunded amount", "Refunded", "Pending", "Failed"]}
      tableRows={props.rows.map((row) => [
        row.label,
        row.amountLabel,
        row.refunded,
        row.pending,
        row.failed,
      ])}
    >
      <div className="recharts-panel" aria-label="Refund count and amount chart">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={1}
          minHeight={1}
          initialDimension={responsiveInitialDimension}
        >
          <ComposedChart data={props.rows}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" />
            <YAxis yAxisId="count" allowDecimals={false} />
            <YAxis
              yAxisId="amount"
              orientation="right"
              tickFormatter={(value) => formatCompactMoney(Number(value))}
            />
            <Tooltip
              formatter={(value, name) =>
                name === "Refunded amount"
                  ? [formatChartMoney(Number(value)), name]
                  : [value, name]
              }
            />
            <Legend />
            <Bar
              yAxisId="count"
              dataKey="refunded"
              name="Refunded"
              fill="#23694b"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("refunds", "REFUNDED", point.payload.date));
                }
              }}
            />
            <Bar
              yAxisId="count"
              dataKey="pending"
              name="Pending"
              fill="#b6832d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("refunds", "PENDING", point.payload.date));
                }
              }}
            />
            <Bar
              yAxisId="count"
              dataKey="failed"
              name="Failed"
              fill="#b5483d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("refunds", "REFUND_FAILED", point.payload.date));
                }
              }}
            />
            <Line
              yAxisId="amount"
              type="monotone"
              dataKey="amountValue"
              name="Refunded amount"
              stroke="#315d92"
              strokeWidth={2}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </AnalyticsChartCard>
  );
}

function WebhookHealthCard(props: { rows: WebhookAnalyticsRow[] }) {
  const navigate = useNavigate();
  return (
    <AnalyticsChartCard
      title="Webhook delivery health"
      summary={`${latest(props.rows)?.deliveryRateLabel ?? "0%"} latest`}
      tableHeaders={["Date", "Delivery rate", "Delivered", "Pending", "Failed", "Total"]}
      tableRows={props.rows.map((row) => [
        row.label,
        row.deliveryRateLabel,
        row.delivered,
        row.pending,
        row.failed,
        row.total,
      ])}
    >
      <div className="recharts-panel" aria-label="Webhook delivery health chart">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={1}
          minHeight={1}
          initialDimension={responsiveInitialDimension}
        >
          <BarChart data={props.rows}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar
              dataKey="delivered"
              name="Delivered"
              stackId="webhooks"
              fill="#23694b"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("webhooks", "DELIVERED", point.payload.date));
                }
              }}
            />
            <Bar
              dataKey="pending"
              name="Pending"
              stackId="webhooks"
              fill="#b6832d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("webhooks", "PENDING", point.payload.date));
                }
              }}
            />
            <Bar
              dataKey="failed"
              name="Failed"
              stackId="webhooks"
              fill="#b5483d"
              cursor="pointer"
              onClick={(point) => {
                if (point?.payload?.date) {
                  navigate(buildDrilldownHref("webhooks", "FAILED", point.payload.date));
                }
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </AnalyticsChartCard>
  );
}

function AttentionCard(props: { viewModel: AnalyticsViewModel }) {
  const attentionTotal = props.viewModel.attentionItems.reduce(
    (sum, item) => sum + item.value,
    0,
  );
  return (
    <ContentCard
      title="Attention breakdown"
      action={<span className="visual-card-summary">{attentionTotal} items</span>}
    >
      <div className="attention-grid">
        {props.viewModel.attentionItems.map((item) => (
          <article key={item.key} className={`attention-item attention-${item.tone}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <Link to={item.href}>{item.actionLabel}</Link>
          </article>
        ))}
      </div>
      <div className="chart-data-panel">
        <h5>Top webhook event types</h5>
        {props.viewModel.topWebhookEventTypes.length > 0 ? (
          <div
            className="stack-list scrollable-list attention-event-list"
            role="list"
            aria-label="Top webhook event types"
          >
            {props.viewModel.topWebhookEventTypes.map((item) => (
              <article key={item.eventType} className="stack-row" role="listitem">
                <div>
                  <strong>{item.eventType}</strong>
                  <p>
                    {item.failed} failed, {item.pending} pending
                  </p>
                </div>
                <div className="stack-row-meta">
                  <span>{item.count} events</span>
                  <Link className="attention-link" to={item.href}>
                    Inspect
                  </Link>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <span className="section-copy">No webhook event type concentration in this range.</span>
        )}
      </div>
    </ContentCard>
  );
}

function AnalyticsChartCard(props: {
  title: string;
  summary: string;
  children: ReactNode;
  tableHeaders: string[];
  tableRows: Array<Array<string | number>>;
}) {
  const [showData, setShowData] = useState(false);
  return (
    <ContentCard
      title={props.title}
      action={<span className="visual-card-summary">{props.summary}</span>}
    >
      {props.children}
      <button
        type="button"
        className="secondary-button chart-data-toggle"
        onClick={() => setShowData((current) => !current)}
      >
        {showData ? "Hide data" : "View data"}
      </button>
      {showData ? (
        <DataTable headers={props.tableHeaders} rows={props.tableRows} />
      ) : null}
    </ContentCard>
  );
}

function DataTable(props: {
  headers: string[];
  rows: Array<Array<string | number>>;
}) {
  return (
    <div className="chart-data-table-wrap">
      <table className="chart-data-table">
        <thead>
          <tr>
            {props.headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row, rowIndex) => (
            <tr key={`${row[0]}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${row[0]}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function latest<T>(rows: T[]) {
  return rows.length > 0 ? rows[rows.length - 1] : undefined;
}

function formatCompactMoney(value: number) {
  if (value >= 1_000_000) {
    return `${Math.round(value / 1_000_000)}m`;
  }
  if (value >= 1_000) {
    return `${Math.round(value / 1_000)}k`;
  }
  return `${value}`;
}
