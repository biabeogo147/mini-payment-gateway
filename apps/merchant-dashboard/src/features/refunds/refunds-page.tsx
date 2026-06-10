import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getRefundDetail, listRefunds, type RefundStatus } from "../common/api";
import { formatDateTime, formatMoney } from "../common/format";
import {
  ContentCard,
  DetailGrid,
  EmptyState,
  ErrorCard,
  InlineField,
  PageHeader,
  StatusBadge,
} from "../common/ui";

const statusOptions: Array<RefundStatus | ""> = ["", "REFUND_PENDING", "REFUNDED", "REFUND_FAILED"];

interface RefundFilters {
  refund_transaction_id: string;
  refund_id: string;
  status: RefundStatus | "";
  date_from: string;
  date_to: string;
}

export function RefundsPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<RefundFilters>({
    refund_transaction_id: searchParams.get("refund_transaction_id") ?? "",
    refund_id: searchParams.get("refund_id") ?? "",
    status: (searchParams.get("status") as RefundStatus | null) ?? "",
    date_from: searchParams.get("date_from") ?? "",
    date_to: searchParams.get("date_to") ?? "",
  });
  const [selectedRefundTransactionId, setSelectedRefundTransactionId] = useState(
    searchParams.get("refund_transaction_id") ?? "",
  );

  const listQuery = useQuery({
    queryKey: ["refunds", filters],
    queryFn: () => listRefunds({ ...filters, limit: 100 }),
  });
  const detailQuery = useQuery({
    queryKey: ["refund-detail", selectedRefundTransactionId],
    queryFn: () => getRefundDetail(selectedRefundTransactionId),
    enabled: Boolean(selectedRefundTransactionId),
  });

  useEffect(() => {
    const firstId = listQuery.data?.refunds[0]?.refund_transaction_id;
    if (!selectedRefundTransactionId && firstId) {
      setSelectedRefundTransactionId(firstId);
    }
  }, [listQuery.data, selectedRefundTransactionId]);

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const refunds = listQuery.data?.refunds ?? [];
  const refundDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Refunds"
        title="Refund Explorer"
        description="Search refunds by gateway transaction, merchant refund id, status, and date range."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Refund transaction id">
            <input
              value={filters.refund_transaction_id}
              onChange={(event) =>
                setFilters((current) => ({ ...current, refund_transaction_id: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Refund id">
            <input
              value={filters.refund_id}
              onChange={(event) =>
                setFilters((current) => ({ ...current, refund_id: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Status">
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({ ...current, status: event.target.value as RefundStatus | "" }))
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
        <ContentCard title="Refund list">
          {refunds.length === 0 ? (
            <EmptyState title="No refunds match" message="Change filters to inspect a different refund slice." />
          ) : (
            <div className="stack-list">
              {refunds.map((refund) => (
                <button
                  type="button"
                  key={refund.refund_transaction_id}
                  className={
                    selectedRefundTransactionId === refund.refund_transaction_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedRefundTransactionId(refund.refund_transaction_id)}
                >
                  <div>
                    <strong>{refund.refund_transaction_id}</strong>
                    <p>{refund.refund_id}</p>
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
          {!selectedRefundTransactionId ? (
            <EmptyState title="Select a refund" message="Choose a row to inspect callback evidence." />
          ) : detailQuery.isLoading ? (
            <EmptyState title="Loading refund" message="Fetching refund detail." />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : refundDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Refund transaction id", value: refundDetail.refund_transaction_id },
                  { label: "Refund id", value: refundDetail.refund_id },
                  { label: "Original payment", value: refundDetail.original_transaction_id },
                  { label: "Status", value: <StatusBadge value={refundDetail.refund_status} /> },
                  { label: "Amount", value: formatMoney(refundDetail.refund_amount) },
                  { label: "Processed at", value: formatDateTime(refundDetail.processed_at) },
                ]}
              />
              <ContentCard title="Callback evidence">
                {refundDetail.callback_logs.length === 0 ? (
                  <EmptyState title="No callbacks" message="No provider callback evidence is attached." />
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
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
