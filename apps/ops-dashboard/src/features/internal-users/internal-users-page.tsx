import { PlaceholderPage } from "../common/placeholder-page";

export function InternalUsersPage() {
  return (
    <PlaceholderPage
      title="Internal Users"
      description="Admin-only account management will be implemented here after internal auth lands. The scaffold already reserves the route and primary use cases."
      plannedItems={[
        "Internal user list",
        "Role assignment for ADMIN and OPS",
        "Activate and deactivate actions",
        "Password reset flow",
      ]}
    />
  );
}
