import { PlaceholderPage } from "../common/placeholder-page";

export function PaymentsPage() {
  return (
    <PlaceholderPage
      title="Payments Explorer"
      description="The payments explorer will become the fastest way for operators to answer transaction questions without using Postman or database queries."
      plannedItems={[
        "Lookup by transaction id and order id",
        "Merchant, status, and date filters",
        "Payment detail with QR payload and callback evidence",
        "Links to refunds and reconciliation records when present",
      ]}
    />
  );
}
