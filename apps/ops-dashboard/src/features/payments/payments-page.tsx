import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  getPaymentDetail,
  listPayments,
  type PaymentStatus,
} from "../common/api";
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

const paymentStatusOptions: Array<PaymentStatus | ""> = [
  "",
  "PENDING",
  "SUCCESS",
  "FAILED",
  "EXPIRED",
];

export function PaymentsPage() {
  const [filters, setFilters] = useState({
    transaction_id: "",
    order_id: "",
    merchant_id: "",
    status: "" as PaymentStatus | "",
    date_from: "",
    date_to: "",
  });
  const [selectedTransactionId, setSelectedTransactionId] = useState("");

  const listQuery = useQuery({
    queryKey: ["payments", filters],
    queryFn: () =>
      listPayments({
        ...filters,
        limit: 100,
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["payment-detail", selectedTransactionId],
    queryFn: () => getPaymentDetail(selectedTransactionId),
    enabled: Boolean(selectedTransactionId),
  });

  useEffect(() => {
    const firstTransactionId = listQuery.data?.payments[0]?.transaction_id;
    if (!selectedTransactionId && firstTransactionId) {
      setSelectedTransactionId(firstTransactionId);
    }
  }, [listQuery.data, selectedTransactionId]);

  if (listQuery.error instanceof Error) {
    return <ErrorCard message={listQuery.error.message} />;
  }

  const payments = listQuery.data?.payments ?? [];
  const paymentDetail = detailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Transaction explorer"
        title="Payments"
        description="Search live payment traffic by transaction, order, merchant, and status, then inspect callback evidence and linked refunds."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Transaction id">
            <input
              value={filters.transaction_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  transaction_id: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Order id">
            <input
              value={filters.order_id}
              onChange={(event) =>
                setFilters((current) => ({ ...current, order_id: event.target.value }))
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
                  status: event.target.value as PaymentStatus | "",
                }))
              }
            >
              {paymentStatusOptions.map((option) => (
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
        <ContentCard title="Payment list">
          {payments.length === 0 ? (
            <EmptyState
              title="No payments match"
              message="Change the current filters to inspect a different slice of traffic."
            />
          ) : (
            <div className="stack-list">
              {payments.map((payment) => (
                <button
                  type="button"
                  key={payment.transaction_id}
                  className={
                    selectedTransactionId === payment.transaction_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedTransactionId(payment.transaction_id)}
                >
                  <div>
                    <strong>{payment.transaction_id}</strong>
                    <p>
                      {payment.order_id} · {payment.merchant_name}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={payment.status} />
                    <span>{formatMoney(payment.amount)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Payment detail">
          {!selectedTransactionId ? (
            <EmptyState
              title="Select a payment"
              message="Choose a payment from the list to inspect callback evidence and refund linkage."
            />
          ) : detailQuery.isLoading ? (
            <EmptyState
              title="Loading payment detail"
              message="Fetching the payment record, callbacks, reconciliation, and refunds."
            />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : paymentDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Transaction id", value: paymentDetail.transaction_id },
                  { label: "Order id", value: paymentDetail.order_id },
                  { label: "Merchant", value: paymentDetail.merchant_name },
                  { label: "Status", value: <StatusBadge value={paymentDetail.status} /> },
                  { label: "Amount", value: formatMoney(paymentDetail.amount) },
                  { label: "Paid at", value: formatDateTime(paymentDetail.paid_at) },
                  { label: "Expires at", value: formatDateTime(paymentDetail.expire_at) },
                  {
                    label: "Reconciliation",
                    value: paymentDetail.reconciliation ? (
                      <StatusBadge value={paymentDetail.reconciliation.match_result} />
                    ) : (
                      "None"
                    ),
                  },
                ]}
              />

              <ContentCard title="QR content">
                <JsonBlock value={{ qr_content: paymentDetail.qr_content }} />
              </ContentCard>

              <div className="panel-grid">
                <ContentCard title="Refund links">
                  {paymentDetail.refunds.length === 0 ? (
                    <EmptyState title="No refunds" message="No refund has been linked to this payment." />
                  ) : (
                    <div className="stack-list">
                      {paymentDetail.refunds.map((refund) => (
                        <article key={refund.refund_transaction_id} className="stack-row">
                          <div>
                            <strong>{refund.refund_transaction_id}</strong>
                            <p>{refund.refund_id}</p>
                          </div>
                          <div className="stack-row-meta">
                            <StatusBadge value={refund.refund_status} />
                            <span>{formatMoney(refund.refund_amount)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>

                <ContentCard title="Callback evidence">
                  {paymentDetail.callback_logs.length === 0 ? (
                    <EmptyState
                      title="No callbacks"
                      message="The payment has not received a provider callback yet."
                    />
                  ) : (
                    <div className="stack-list">
                      {paymentDetail.callback_logs.map((callback) => (
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
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
