import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getRefundDetail, listRefunds, type RefundStatus } from "../common/api";
import { formatDateTime, formatMoney } from "../common/format";
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

const refundStatusOptions: Array<RefundStatus | ""> = [
  "",
  "REFUND_PENDING",
  "REFUNDED",
  "REFUND_FAILED",
];

export function RefundsPage() {
  const [filters, setFilters] = useState({
    refund_transaction_id: "",
    refund_id: "",
    merchant_id: "",
    status: "" as RefundStatus | "",
    date_from: "",
    date_to: "",
  });
  const [selectedRefundId, setSelectedRefundId] = useState("");

  const listQuery = useQuery({
    queryKey: ["refunds", filters],
    queryFn: () =>
      listRefunds({
        ...filters,
        limit: 100,
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["refund-detail", selectedRefundId],
    queryFn: () => getRefundDetail(selectedRefundId),
    enabled: Boolean(selectedRefundId),
  });

  useEffect(() => {
    const firstRefundId = listQuery.data?.refunds[0]?.refund_transaction_id;
    if (!selectedRefundId && firstRefundId) {
      setSelectedRefundId(firstRefundId);
    }
  }, [listQuery.data, selectedRefundId]);

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const refunds = listQuery.data?.refunds ?? [];
  const refundDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Refund explorer"
        title="Refunds"
        description="Trace refund requests, inspect callback evidence, and confirm the link back to the original payment."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Refund transaction id">
            <input
              value={filters.refund_transaction_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  refund_transaction_id: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Refund id">
            <input
              value={filters.refund_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  refund_id: event.target.value,
                }))
              }
            />
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
          <InlineField label="Status">
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  status: event.target.value as RefundStatus | "",
                }))
              }
            >
              {refundStatusOptions.map((option) => (
                <option key={option || "ALL"} value={option}>
                  {option || "ALL"}
                </option>
              ))}
            </select>
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
              placeholder="2026-05-13T00:00:00Z"
            />
          </InlineField>
          <InlineField label="Date to (ISO)">
            <input
              value={filters.date_to}
              onChange={(event) =>
                setFilters((current) => ({ ...current, date_to: event.target.value }))
              }
              placeholder="2026-05-13T23:59:59Z"
            />
          </InlineField>
        </div>
      </ContentCard>

      <div className="panel-grid panel-grid-wide">
        <ContentCard title="Refund list">
          {refunds.length === 0 ? (
            <EmptyState
              title="No refunds match"
              message="Adjust the current filters to inspect a different refund slice."
            />
          ) : (
            <div className="stack-list">
              {refunds.map((refund) => (
                <button
                  type="button"
                  key={refund.refund_transaction_id}
                  className={
                    selectedRefundId === refund.refund_transaction_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedRefundId(refund.refund_transaction_id)}
                >
                  <div>
                    <strong>{refund.refund_transaction_id}</strong>
                    <p>
                      {refund.refund_id} · {refund.merchant_name}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={refund.refund_status} />
                    <span>{formatMoney(refund.refund_amount)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Refund detail">
          {!selectedRefundId ? (
            <EmptyState
              title="Select a refund"
              message="Choose a refund from the list to inspect detail."
            />
          ) : detailQuery.isLoading ? (
            <EmptyState
              title="Loading refund detail"
              message="Fetching refund callbacks, processing timestamps, and reconciliation."
            />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : refundDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Refund transaction id", value: refundDetail.refund_transaction_id },
                  { label: "Refund id", value: refundDetail.refund_id },
                  { label: "Original payment", value: refundDetail.original_transaction_id },
                  { label: "Merchant", value: refundDetail.merchant_name },
                  { label: "Status", value: <StatusBadge value={refundDetail.refund_status} /> },
                  { label: "Refund amount", value: formatMoney(refundDetail.refund_amount) },
                  { label: "Processed at", value: formatDateTime(refundDetail.processed_at) },
                  {
                    label: "Reconciliation",
                    value: refundDetail.reconciliation ? (
                      <StatusBadge value={refundDetail.reconciliation.match_result} />
                    ) : (
                      "None"
                    ),
                  },
                ]}
              />

              <div className="panel-grid">
                <ContentCard title="Callback evidence">
                  {refundDetail.callback_logs.length === 0 ? (
                    <EmptyState
                      title="No callbacks"
                      message="The refund has not received a provider callback yet."
                    />
                  ) : (
                    <div className="stack-list">
                      {refundDetail.callback_logs.map((callback) => (
                        <article key={callback.callback_id} className="stack-row">
                          <div>
                            <strong>{callback.source_type}</strong>
                            <p>{callback.normalized_status ?? "No normalized status"}</p>
                          </div>
                          <div className="stack-row-meta">
                            <span>{callback.processing_result}</span>
                            <span>{formatDateTime(callback.received_at)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>

                <ContentCard title="Failure hints">
                  <JsonBlock
                    value={{
                      failed_reason_code: refundDetail.failed_reason_code,
                      failed_reason_message: refundDetail.failed_reason_message,
                      external_reference: refundDetail.external_reference,
                      idempotency_key: refundDetail.idempotency_key,
                    }}
                  />
                </ContentCard>
              </div>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
