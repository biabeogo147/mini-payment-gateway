import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getPaymentDetail, listPayments, type PaymentStatus } from "../common/api";
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

const statusOptions: Array<PaymentStatus | ""> = ["", "PENDING", "SUCCESS", "FAILED", "EXPIRED"];

interface PaymentFilters {
  transaction_id: string;
  order_id: string;
  status: PaymentStatus | "";
  date_from: string;
  date_to: string;
}

export function PaymentsPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<PaymentFilters>({
    transaction_id: searchParams.get("transaction_id") ?? "",
    order_id: searchParams.get("order_id") ?? "",
    status: (searchParams.get("status") as PaymentStatus | null) ?? "",
    date_from: searchParams.get("date_from") ?? "",
    date_to: searchParams.get("date_to") ?? "",
  });
  const [selectedTransactionId, setSelectedTransactionId] = useState(
    searchParams.get("transaction_id") ?? "",
  );

  const listQuery = useQuery({
    queryKey: ["payments", filters],
    queryFn: () => listPayments({ ...filters, limit: 100 }),
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
  const qrImageSource = paymentDetail?.qr_image_base64 ?? paymentDetail?.qr_image_url;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Payments"
        title="Payment Explorer"
        description="Search payments by transaction id, order id, status, and date range."
      />

      <ContentCard title="Filters">
        <div className="form-grid">
          <InlineField label="Transaction id">
            <input
              value={filters.transaction_id}
              onChange={(event) =>
                setFilters((current) => ({ ...current, transaction_id: event.target.value }))
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
          <InlineField label="Status">
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({ ...current, status: event.target.value as PaymentStatus | "" }))
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
        <ContentCard title="Payment list">
          {payments.length === 0 ? (
            <EmptyState title="No payments match" message="Change filters to inspect a different payment slice." />
          ) : (
            <div className="stack-list scrollable-list explorer-list" aria-label="Payment list">
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
                    <p>{payment.order_id}</p>
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
            <EmptyState title="Select a payment" message="Choose a row to inspect callbacks and refunds." />
          ) : detailQuery.isLoading ? (
            <EmptyState title="Loading payment" message="Fetching payment detail." />
          ) : detailQuery.error instanceof Error ? (
            <ErrorCard message={detailQuery.error.message} />
          ) : paymentDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Transaction id", value: paymentDetail.transaction_id },
                  { label: "Order id", value: paymentDetail.order_id },
                  { label: "Status", value: <StatusBadge value={paymentDetail.status} /> },
                  { label: "Amount", value: formatMoney(paymentDetail.amount) },
                  { label: "Paid at", value: formatDateTime(paymentDetail.paid_at) },
                  { label: "Expires at", value: formatDateTime(paymentDetail.expire_at) },
                ]}
              />
              <ContentCard title="QR payload">
                <div className={qrImageSource ? "qr-payload-grid" : "qr-payload-grid qr-payload-grid-single"}>
                  {qrImageSource ? (
                    <div className="qr-image-frame">
                      <img
                        className="qr-image"
                        src={qrImageSource}
                        alt={`QR code for ${paymentDetail.transaction_id}`}
                      />
                    </div>
                  ) : null}
                  <JsonBlock
                    value={{
                      qr_reference: paymentDetail.qr_reference,
                      qr_content: paymentDetail.qr_content,
                    }}
                  />
                </div>
              </ContentCard>
              <div className="panel-grid">
                <ContentCard title="Callback evidence">
                  {paymentDetail.callback_logs.length === 0 ? (
                    <EmptyState title="No callbacks" message="No provider callback evidence is attached." />
                  ) : (
                    <div
                      className="stack-list scrollable-list detail-list"
                      role="list"
                      aria-label="Payment callback evidence"
                    >
                      {paymentDetail.callback_logs.map((callback) => (
                        <article key={callback.callback_id} className="stack-row" role="listitem">
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
                <ContentCard title="Refund links">
                  {paymentDetail.refunds.length === 0 ? (
                    <EmptyState title="No refunds" message="No refund is linked to this payment." />
                  ) : (
                    <div
                      className="stack-list scrollable-list detail-list"
                      role="list"
                      aria-label="Payment refund links"
                    >
                      {paymentDetail.refunds.map((refund) => (
                        <article
                          key={refund.refund_transaction_id}
                          className="stack-row"
                          role="listitem"
                        >
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
              </div>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
