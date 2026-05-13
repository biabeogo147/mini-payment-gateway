import { PlaceholderPage } from "../common/placeholder-page";

export function WebhooksPage() {
  return (
    <PlaceholderPage
      title="Webhooks Explorer"
      description="Webhook delivery monitoring and manual retry will live here, with the detail view centered on payload, attempt history, and last failure reason."
      plannedItems={[
        "List and filter webhook events by type, status, merchant, and date",
        "Delivery attempt history",
        "Failure reason visibility",
        "Manual retry entry point for eligible events",
      ]}
    />
  );
}
