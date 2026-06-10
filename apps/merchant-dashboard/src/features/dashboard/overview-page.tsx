import { useQuery } from "@tanstack/react-query";

import { getDashboardCharts, getDashboardSummary } from "../common/api";
import { formatMoney } from "../common/format";
import {
  ContentCard,
  EmptyState,
  ErrorCard,
  MetricCard,
  PageHeader,
} from "../common/ui";
import {
  buildAmountTrend,
  buildPaymentStatusBars,
  buildRefundVolume,
  buildWebhookHealth,
  hasAnyDashboardChartData,
} from "./chart-data";
import {
  AmountTrendChart,
  RefundVolumeChart,
  StackedStatusBars,
  WebhookHealthChart,
} from "./dashboard-visualizations";

export function OverviewPage() {
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
  });
  const chartsQuery = useQuery({
    queryKey: ["dashboard-charts"],
    queryFn: getDashboardCharts,
  });

  if (summaryQuery.isLoading || chartsQuery.isLoading) {
    return (
      <section className="page-stack">
        <PageHeader
          eyebrow="Merchant pulse"
          title="Overview"
          description="Daily view of payment volume, refunds, and webhook delivery health."
        />
        <ContentCard>
          <EmptyState
            title="Loading dashboard"
            message="Fetching merchant-scoped counters and charts."
          />
        </ContentCard>
      </section>
    );
  }

  if (summaryQuery.error instanceof Error) {
    return <ErrorCard message={summaryQuery.error.message} />;
  }
  if (chartsQuery.error instanceof Error) {
    return <ErrorCard message={chartsQuery.error.message} />;
  }

  const summary = summaryQuery.data;
  const charts = chartsQuery.data;
  if (!summary || !charts) {
    return <ErrorCard message="Dashboard data is unavailable." />;
  }

  const paymentStatusRows = buildPaymentStatusBars(charts.payment_status_by_day);
  const amountTrend = buildAmountTrend(charts.successful_payment_amount_by_day);
  const refundVolume = buildRefundVolume(charts.refund_count_by_day);
  const webhookHealth = buildWebhookHealth(charts.webhook_status_by_day);
  const paymentTotal = paymentStatusRows.reduce((total, row) => total + row.total, 0);
  const webhookOpenTotal = webhookHealth.reduce((total, row) => total + row.openCount, 0);

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Merchant pulse"
        title="Overview"
        description="Daily view of payment volume, refunds, and webhook delivery health."
      />

      <div className="metric-grid">
        <MetricCard
          label="Payments last 24h"
          value={summary.payments_last_24h}
          hint={`${paymentTotal} payments across chart range`}
        />
        <MetricCard
          label="Successful amount last 24h"
          value={formatMoney(summary.successful_payment_amount_last_24h)}
          hint={`${formatMoney(amountTrend.totalValue)} successful in chart range`}
        />
        <MetricCard
          label="Pending payments"
          value={summary.pending_payments}
          hint="Awaiting customer or provider completion"
        />
        <MetricCard
          label="Refunds last 24h"
          value={summary.refunds_last_24h}
          hint={`${refundVolume.totalValue} refunds across chart range`}
        />
        <MetricCard
          label="Open webhook events"
          value={summary.open_webhook_events}
          hint={`${webhookOpenTotal} pending or failed in chart range`}
        />
      </div>

      {hasAnyDashboardChartData(charts) ? (
        <div className="visualization-grid">
          <StackedStatusBars rows={paymentStatusRows} />
          <AmountTrendChart trend={amountTrend} />
          <RefundVolumeChart chart={refundVolume} />
          <WebhookHealthChart rows={webhookHealth} />
        </div>
      ) : (
        <ContentCard title="Seven-day visualization">
          <EmptyState
            title="No chart activity yet"
            message="Once payments, refunds, or webhook events arrive, seven-day visualizations will appear here."
          />
        </ContentCard>
      )}
    </section>
  );
}
