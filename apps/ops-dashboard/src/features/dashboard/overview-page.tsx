import { useQuery } from "@tanstack/react-query";

import { getDashboardCharts, getDashboardSummary } from "../common/api";
import { formatDateTime, formatMoney } from "../common/format";
import {
  ChartStrip,
  ContentCard,
  EmptyState,
  ErrorCard,
  MetricCard,
  PageHeader,
  StatusBadge,
} from "../common/ui";

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
          eyebrow="Operations pulse"
          title="Overview"
          description="Daily control tower for internal ops: queues, recent failures, and traffic trends."
        />
        <ContentCard>
          <EmptyState
            title="Loading dashboard"
            message="Fetching summary counters and seven-day charts from the backend."
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

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Operations pulse"
        title="Overview"
        description="Daily control tower for internal ops: queues, recent failures, and traffic trends."
      />

      <div className="metric-grid">
        <MetricCard
          label="Merchants pending review"
          value={summary.merchants_pending_review}
        />
        <MetricCard
          label="Active merchants"
          value={summary.merchants_active}
        />
        <MetricCard
          label="Payments in last 24h"
          value={summary.payments_last_24h}
        />
        <MetricCard
          label="Successful amount in last 24h"
          value={formatMoney(summary.successful_payment_amount_last_24h)}
        />
        <MetricCard label="Refunds in last 24h" value={summary.refunds_last_24h} />
        <MetricCard
          label="Open webhook failures"
          value={summary.failed_webhook_events_open}
        />
        <MetricCard
          label="Open reconciliation records"
          value={summary.reconciliation_open}
        />
      </div>

      <div className="panel-grid">
        <ContentCard title="Onboarding queue">
          {summary.onboarding_queue.length === 0 ? (
            <EmptyState
              title="No merchants waiting"
              message="The onboarding queue is currently clear."
            />
          ) : (
            <div className="stack-list">
              {summary.onboarding_queue.map((item) => (
                <article key={item.merchant_id} className="stack-row">
                  <div>
                    <strong>{item.merchant_name}</strong>
                    <p>{item.merchant_id}</p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={item.onboarding_status} />
                    <span>{formatDateTime(item.updated_at)}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Failed webhook queue">
          {summary.failed_webhooks.length === 0 ? (
            <EmptyState
              title="Delivery queue is healthy"
              message="No webhook events are sitting in FAILED status right now."
            />
          ) : (
            <div className="stack-list">
              {summary.failed_webhooks.map((item) => (
                <article key={item.event_id} className="stack-row">
                  <div>
                    <strong>{item.event_type}</strong>
                    <p>
                      {item.merchant_name} · {item.merchant_id}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={item.status} />
                    <span>{item.attempt_count} attempts</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Open reconciliation">
          {summary.reconciliation_queue.length === 0 ? (
            <EmptyState
              title="No open records"
              message="Everything is currently matched or already resolved."
            />
          ) : (
            <div className="stack-list">
              {summary.reconciliation_queue.map((item) => (
                <article key={item.record_id} className="stack-row">
                  <div>
                    <strong>{item.entity_type}</strong>
                    <p>{item.record_id}</p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={item.match_result} />
                    <span>{item.mismatch_reason_code ?? "No code"}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </ContentCard>
      </div>

      <div className="panel-grid">
        <ChartStrip
          title="Payment success trend (7 days)"
          rows={charts.payment_status_by_day.map((item) => ({
            label: item.date,
            value: item.success,
          }))}
        />
        <ChartStrip
          title="Refund trend (7 days)"
          rows={charts.refund_count_by_day.map((item) => ({
            label: item.date,
            value: item.count,
            tone: "tone-warm",
          }))}
        />
        <ChartStrip
          title="Webhook failure trend (7 days)"
          rows={charts.webhook_status_by_day.map((item) => ({
            label: item.date,
            value: item.failed,
            tone: "tone-danger",
          }))}
        />
        <ChartStrip
          title="Reconciliation resolved (7 days)"
          rows={charts.reconciliation_by_day.map((item) => ({
            label: item.date,
            value: item.resolved,
            tone: "tone-good",
          }))}
        />
      </div>
    </section>
  );
}
