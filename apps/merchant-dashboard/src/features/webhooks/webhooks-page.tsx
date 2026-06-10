import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getWebhookDetail, listWebhooks, type WebhookEventStatus } from "../common/api";
import { formatDateTime } from "../common/format";
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

const statusOptions: Array<WebhookEventStatus | ""> = ["", "PENDING", "DELIVERED", "FAILED"];

interface WebhookFilters {
  event_type: string;
  status: WebhookEventStatus | "";
  date_from: string;
  date_to: string;
}

export function WebhooksPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<WebhookFilters>({
    event_type: searchParams.get("event_type") ?? "",
    status: (searchParams.get("status") as WebhookEventStatus | null) ?? "",
    date_from: searchParams.get("date_from") ?? "",
    date_to: searchParams.get("date_to") ?? "",
  });
  const [selectedEventId, setSelectedEventId] = useState("");

  const listQuery = useQuery({
    queryKey: ["webhooks", filters],
    queryFn: () => listWebhooks({ ...filters, limit: 100 }),
  });
  const detailQuery = useQuery({
    queryKey: ["webhook-detail", selectedEventId],
    queryFn: () => getWebhookDetail(selectedEventId),
    enabled: Boolean(selectedEventId),
  });

  useEffect(() => {
    const firstId = listQuery.data?.events[0]?.event_id;
    if (!selectedEventId && firstId) {
      setSelectedEventId(firstId);
    }
  }, [listQuery.data, selectedEventId]);

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const events = listQuery.data?.events ?? [];
  const eventDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Webhooks"
        title="Webhook Explorer"
        description="Inspect outbound event payloads and delivery attempts."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Event type">
            <input
              value={filters.event_type}
              onChange={(event) =>
                setFilters((current) => ({ ...current, event_type: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Status">
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({ ...current, status: event.target.value as WebhookEventStatus | "" }))
              }
            >
              {statusOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Date from">
            <input
              type="datetime-local"
              value={filters.date_from}
              onChange={(event) =>
                setFilters((current) => ({ ...current, date_from: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Date to">
            <input
              type="datetime-local"
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
            <EmptyState title="No webhooks match" message="Change filters to inspect another event slice." />
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
                    <p>{event.event_id}</p>
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
            <EmptyState title="Select a webhook" message="Choose a row to inspect payload and attempts." />
          ) : detailQuery.isLoading ? (
            <EmptyState title="Loading webhook" message="Fetching webhook detail." />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : eventDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Event id", value: eventDetail.event_id },
                  { label: "Event type", value: eventDetail.event_type },
                  { label: "Status", value: <StatusBadge value={eventDetail.status} /> },
                  { label: "Attempts", value: eventDetail.attempt_count },
                  { label: "Last attempt", value: formatDateTime(eventDetail.last_attempt_at) },
                  { label: "Next retry", value: formatDateTime(eventDetail.next_retry_at) },
                ]}
              />
              <ContentCard title="Payload">
                <JsonBlock value={eventDetail.payload_json} />
              </ContentCard>
              <ContentCard title="Delivery attempts">
                {eventDetail.attempts.length === 0 ? (
                  <EmptyState title="No attempts" message="No delivery attempts recorded yet." />
                ) : (
                  <div className="stack-list">
                    {eventDetail.attempts.map((attempt) => (
                      <article key={attempt.attempt_id} className="stack-row">
                        <div>
                          <strong>Attempt {attempt.attempt_no}</strong>
                          <p>{attempt.error_message ?? attempt.response_body_snippet ?? "No error captured"}</p>
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
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
