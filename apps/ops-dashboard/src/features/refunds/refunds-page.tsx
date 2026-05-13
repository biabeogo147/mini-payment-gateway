import { PlaceholderPage } from "../common/placeholder-page";

export function RefundsPage() {
  return (
    <PlaceholderPage
      title="Refunds Explorer"
      description="Refund support and investigation will land here with the same list-detail pattern as payments, tuned for refund identifiers and callback evidence."
      plannedItems={[
        "Lookup by refund transaction id and refund id",
        "Merchant, status, and date filters",
        "Original payment linkage",
        "Callback evidence and reconciliation visibility",
      ]}
    />
  );
}
