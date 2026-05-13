import { PlaceholderPage } from "../common/placeholder-page";

export function ReconciliationPage() {
  return (
    <PlaceholderPage
      title="Reconciliation"
      description="The reconciliation queue will give operators a focused place to inspect mismatches, compare internal and provider evidence, and record review decisions."
      plannedItems={[
        "Filters for MATCHED, MISMATCHED, PENDING_REVIEW, and RESOLVED",
        "Entity type and date filters",
        "Mismatch reason, evidence, and reviewer metadata",
        "Resolve flow with review note capture",
      ]}
    />
  );
}
