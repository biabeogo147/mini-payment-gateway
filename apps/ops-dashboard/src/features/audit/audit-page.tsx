import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listAuditLogs, type ActorType, type EntityType } from "../common/api";
import { formatDateTime } from "../common/format";
import {
  ContentCard,
  EmptyState,
  ErrorCard,
  InlineField,
  JsonBlock,
  PageHeader,
  StatusBadge,
} from "../common/ui";

const actorTypeOptions: Array<ActorType | ""> = ["", "SYSTEM", "ADMIN", "OPS"];
const entityTypeOptions: Array<EntityType | ""> = [
  "",
  "PAYMENT",
  "REFUND",
  "MERCHANT",
  "MERCHANT_CREDENTIAL",
  "ONBOARDING_CASE",
  "WEBHOOK_EVENT",
  "RECONCILIATION",
  "INTERNAL_USER",
];

export function AuditPage() {
  const [filters, setFilters] = useState({
    actor_type: "" as ActorType | "",
    actor_id: "",
    entity_type: "" as EntityType | "",
    entity_id: "",
    event_type: "",
    date_from: "",
    date_to: "",
  });

  const auditQuery = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () =>
      listAuditLogs({
        ...filters,
        limit: 200,
      }),
  });

  if (auditQuery.error instanceof Error) {
    return <ErrorCard message={auditQuery.error.message} />;
  }

  const logs = auditQuery.data?.logs ?? [];

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Traceability"
        title="Audit"
        description="Filter operator and system activity across merchant lifecycle, credentials, webhook recovery, and reconciliation."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Actor type">
            <select
              value={filters.actor_type}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  actor_type: event.target.value as ActorType | "",
                }))
              }
            >
              {actorTypeOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Actor id">
            <input
              value={filters.actor_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  actor_id: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Entity type">
            <select
              value={filters.entity_type}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  entity_type: event.target.value as EntityType | "",
                }))
              }
            >
              {entityTypeOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Entity id">
            <input
              value={filters.entity_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  entity_id: event.target.value,
                }))
              }
            />
          </InlineField>
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

      <ContentCard title="Audit timeline">
        {logs.length === 0 ? (
          <EmptyState
            title="No audit rows"
            message="Change the current filters to inspect another audit slice."
          />
        ) : (
          <div className="stack-list">
            {logs.map((log) => (
              <article key={log.log_id} className="timeline-row">
                <div className="timeline-head">
                  <div>
                    <strong>{log.event_type}</strong>
                    <p>
                      {log.entity_type} · {log.entity_id}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={log.actor_type} />
                    <span>{formatDateTime(log.created_at)}</span>
                  </div>
                </div>
                <p className="timeline-reason">{log.reason ?? "No reason captured"}</p>
                <div className="timeline-grid">
                  <ContentCard title="Before">
                    <JsonBlock value={log.before_state_json ?? {}} />
                  </ContentCard>
                  <ContentCard title="After">
                    <JsonBlock value={log.after_state_json ?? {}} />
                  </ContentCard>
                </div>
              </article>
            ))}
          </div>
        )}
      </ContentCard>
    </section>
  );
}
