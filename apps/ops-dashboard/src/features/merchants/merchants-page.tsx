import { PlaceholderPage } from "../common/placeholder-page";

export function MerchantsPage() {
  return (
    <PlaceholderPage
      title="Merchants"
      description="The merchant workspace will be the main operating surface for profile review, onboarding decisions, credential metadata, and quick operational actions."
      plannedItems={[
        "Merchant search by id, name, and contact email",
        "Status and onboarding filters",
        "Merchant detail with recent payments, refunds, and webhook failures",
        "Action bar for activation, suspension, disablement, and credential flows",
      ]}
    />
  );
}
