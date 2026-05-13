import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getReconciliationRecord,
  listReconciliationRecords,
  resolveReconciliationRecord,
  type EntityType,
  type ReconciliationStatus,
} from "../common/api";
import { formatDateTime, formatMoney } from "../common/format";
import { invalidateOpsConsoleData } from "../common/query";
import {
  ContentCard,
  DetailGrid,
  EmptyState,
  ErrorCard,
  InlineField,
  PageHeader,
  StatusBadge,
} from "../common/ui";

const statusOptions: Array<ReconciliationStatus | ""> = [
  "",
  "MATCHED",
  "MISMATCHED",
  "PENDING_REVIEW",
  "RESOLVED",
];

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

export function ReconciliationPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    match_result: "" as ReconciliationStatus | "",
    entity_type: "" as EntityType | "",
    entity_id: "",
  });
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [resolveReason, setResolveReason] = useState(
    "Resolve reconciliation record from ops dashboard.",
  );
  const [reviewNote, setReviewNote] = useState("");

  const listQuery = useQuery({
    queryKey: ["reconciliation", filters],
    queryFn: () =>
      listReconciliationRecords({
        ...filters,
        limit: 100,
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["reconciliation-detail", selectedRecordId],
    queryFn: () => getReconciliationRecord(selectedRecordId),
    enabled: Boolean(selectedRecordId),
  });

  useEffect(() => {
    const firstRecordId = listQuery.data?.records[0]?.record_id;
    if (!selectedRecordId && firstRecordId) {
      setSelectedRecordId(firstRecordId);
    }
  }, [listQuery.data, selectedRecordId]);

  const resolveMutation = useMutation({
    mutationFn: (recordId: string) =>
      resolveReconciliationRecord(recordId, {
        reason: resolveReason,
        review_note: reviewNote,
      }),
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setReviewNote("");
    },
  });

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const records = listQuery.data?.records ?? [];
  const recordDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Mismatch workbench"
        title="Reconciliation"
        description="Review open mismatch records, inspect evidence fields, and resolve records with an audit note."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Match result">
            <select
              value={filters.match_result}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  match_result: event.target.value as ReconciliationStatus | "",
                }))
              }
            >
              {statusOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
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
        </div>
      </ContentCard>

      <div className="panel-grid panel-grid-wide">
        <ContentCard title="Record list">
          {records.length === 0 ? (
            <EmptyState
              title="No records match"
              message="Adjust the current filters to inspect another reconciliation slice."
            />
          ) : (
            <div className="stack-list">
              {records.map((record) => (
                <button
                  type="button"
                  key={record.record_id}
                  className={
                    selectedRecordId === record.record_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedRecordId(record.record_id)}
                >
                  <div>
                    <strong>{record.entity_type}</strong>
                    <p>{record.record_id}</p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={record.match_result} />
                    <span>{formatMoney(record.internal_amount)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Record detail">
          {!selectedRecordId ? (
            <EmptyState
              title="Select a record"
              message="Choose a record from the list to inspect mismatch evidence."
            />
          ) : detailQuery.isLoading ? (
            <EmptyState
              title="Loading record detail"
              message="Fetching current internal and external values for this record."
            />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : recordDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Record id", value: recordDetail.record_id },
                  { label: "Entity type", value: recordDetail.entity_type },
                  { label: "Entity id", value: recordDetail.entity_id },
                  {
                    label: "Match result",
                    value: <StatusBadge value={recordDetail.match_result} />,
                  },
                  { label: "Internal status", value: recordDetail.internal_status },
                  { label: "External status", value: recordDetail.external_status },
                  { label: "Internal amount", value: formatMoney(recordDetail.internal_amount) },
                  { label: "External amount", value: formatMoney(recordDetail.external_amount) },
                  {
                    label: "Mismatch code",
                    value: recordDetail.mismatch_reason_code ?? "N/A",
                  },
                  {
                    label: "Last review note",
                    value: recordDetail.review_note ?? "N/A",
                  },
                ]}
              />

              <div className="form-grid">
                <InlineField label="Resolve reason">
                  <input
                    value={resolveReason}
                    onChange={(event) => setResolveReason(event.target.value)}
                  />
                </InlineField>
                <label className="field field-span-two">
                  <span>Review note</span>
                  <textarea
                    value={reviewNote}
                    onChange={(event) => setReviewNote(event.target.value)}
                    rows={5}
                  />
                </label>
              </div>
              <div className="inline-actions">
                <button
                  type="button"
                  className="primary-button"
                  disabled={resolveMutation.isPending || !resolveReason || !reviewNote}
                  onClick={() => resolveMutation.mutate(recordDetail.record_id)}
                >
                  {resolveMutation.isPending ? "Resolving..." : "Resolve record"}
                </button>
                {resolveMutation.error instanceof Error ? (
                  <span className="feedback feedback-danger">
                    {resolveMutation.error.message}
                  </span>
                ) : null}
              </div>
              <p className="section-copy">
                Created {formatDateTime(recordDetail.created_at)} · Updated{" "}
                {formatDateTime(recordDetail.updated_at)}
              </p>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
