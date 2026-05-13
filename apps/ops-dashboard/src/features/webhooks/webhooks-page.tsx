import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getWebhookDetail,
  listWebhooks,
  retryWebhook,
  type WebhookEventStatus,
} from "../common/api";
import { formatDateTime } from "../common/format";
import { invalidateOpsConsoleData } from "../common/query";
import {
  ContentCard,
  DetailGrid,
  EmptyState,
  ErrorCard,
  InlineField,
  JsonBlock,
  PageHeader,
  StatusBadge,
} from "../common/ui";

const webhookStatusOptions: Array<WebhookEventStatus | ""> = [
  "",
  "PENDING",
  "DELIVERED",
  "FAILED",
];

export function WebhooksPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    event_type: "",
    status: "" as WebhookEventStatus | "",
    merchant_id: "",
    date_from: "",
    date_to: "",
  });
  const [selectedEventId, setSelectedEventId] = useState("");
  const [retryReason, setRetryReason] = useState(
    "Manual retry from ops dashboard after inspection.",
  );

  const listQuery = useQuery({
    queryKey: ["webhooks", filters],
    queryFn: () =>
      listWebhooks({
        ...filters,
        limit: 100,
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["webhook-detail", selectedEventId],
    queryFn: () => getWebhookDetail(selectedEventId),
    enabled: Boolean(selectedEventId),
  });

  useEffect(() => {
    const firstEventId = listQuery.data?.events[0]?.event_id;
    if (!selectedEventId && firstEventId) {
      setSelectedEventId(firstEventId);
    }
  }, [listQuery.data, selectedEventId]);

  const retryMutation = useMutation({
    mutationFn: (eventId: string) => retryWebhook(eventId, retryReason),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const events = listQuery.data?.events ?? [];
  const webhookDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Delivery operations"
        title="Webhooks"
        description="Inspect webhook payloads, attempt history, and manual retries for merchant delivery failures."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Event type">
            <input
              value={filters.event_type}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  event_type: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Status">
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  status: event.target.value as WebhookEventStatus | "",
                }))
              }
            >
              {webhookStatusOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Merchant id">
            <input
              value={filters.merchant_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  merchant_id: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Date from (ISO)">
            <input
              value={filters.date_from}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  date_from: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Date to (ISO)">
            <input
              value={filters.date_to}
              onChange={(event) =>
                setFilters((current) => ({ ...current, date_to: event.target.value }))
              }
            />
          </InlineField>
        </div>
      </ContentCard>

      <div className="panel-grid panel-grid-wide">
        <ContentCard title="Webhook list">
          {events.length === 0 ? (
            <EmptyState
              title="No webhook events match"
              message="Adjust the filters to inspect another set of events."
            />
          ) : (
            <div className="stack-list">
              {events.map((event) => (
                <button
                  type="button"
                  key={event.event_id}
                  className={
                    selectedEventId === event.event_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedEventId(event.event_id)}
                >
                  <div>
                    <strong>{event.event_type}</strong>
                    <p>
                      {event.merchant_name} · {event.event_id}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={event.status} />
                    <span>{event.attempt_count} attempts</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Webhook detail">
          {!selectedEventId ? (
            <EmptyState
              title="Select an event"
              message="Choose a webhook event from the list to inspect its payload and attempts."
            />
          ) : detailQuery.isLoading ? (
            <EmptyState
              title="Loading webhook detail"
              message="Fetching payload, signature, latest failure reason, and attempts."
            />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : webhookDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Event id", value: webhookDetail.event_id },
                  { label: "Merchant", value: webhookDetail.merchant_name },
                  { label: "Event type", value: webhookDetail.event_type },
                  { label: "Entity", value: webhookDetail.entity_type },
                  { label: "Status", value: <StatusBadge value={webhookDetail.status} /> },
                  { label: "Attempt count", value: webhookDetail.attempt_count },
                  {
                    label: "Latest failure",
                    value: webhookDetail.latest_failure_reason ?? "N/A",
                  },
                ]}
              />

              <div className="form-grid">
                <InlineField label="Retry reason">
                  <input
                    value={retryReason}
                    onChange={(event) => setRetryReason(event.target.value)}
                  />
                </InlineField>
              </div>
              <div className="inline-actions">
                <button
                  type="button"
                  className="primary-button"
                  disabled={retryMutation.isPending || !retryReason}
                  onClick={() => retryMutation.mutate(webhookDetail.event_id)}
                >
                  {retryMutation.isPending ? "Retrying..." : "Manual retry"}
                </button>
                {retryMutation.error instanceof Error ? (
                  <span className="feedback feedback-danger">
                    {retryMutation.error.message}
                  </span>
                ) : null}
              </div>

              <div className="panel-grid">
                <ContentCard title="Payload JSON">
                  <JsonBlock value={webhookDetail.payload_json} />
                </ContentCard>
                <ContentCard title="Attempt history">
                  {webhookDetail.attempts.length === 0 ? (
                    <EmptyState
                      title="No attempts yet"
                      message="This event has not been attempted yet."
                    />
                  ) : (
                    <div className="stack-list">
                      {webhookDetail.attempts.map((attempt) => (
                        <article key={attempt.attempt_id} className="stack-row">
                          <div>
                            <strong>Attempt #{attempt.attempt_no}</strong>
                            <p>{attempt.request_url}</p>
                          </div>
                          <div className="stack-row-meta">
                            <StatusBadge value={attempt.result} />
                            <span>{formatDateTime(attempt.started_at)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>
              </div>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
