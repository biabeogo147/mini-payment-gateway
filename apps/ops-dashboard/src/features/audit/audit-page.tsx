import { PlaceholderPage } from "../common/placeholder-page";

export function AuditPage() {
  return (
    <PlaceholderPage
      title="Audit Log"
      description="This route anchors the future audit explorer so Ops and Admin can trace actions without dropping to raw database inspection."
      plannedItems={[
        "Filters by actor, entity type, entity id, and event type",
        "Date range filtering",
        "Before and after state review",
        "Masked secret handling for sensitive fields",
      ]}
    />
  );
}
