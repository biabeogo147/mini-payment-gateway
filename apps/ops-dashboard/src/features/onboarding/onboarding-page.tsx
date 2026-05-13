import { PlaceholderPage } from "../common/placeholder-page";

export function OnboardingPage() {
  return (
    <PlaceholderPage
      title="Onboarding Queue"
      description="This page is reserved for the fast triage flow that Ops will use to review merchants, inspect onboarding context, and approve or reject cases."
      plannedItems={[
        "Queue of merchants in PENDING_REVIEW",
        "Inline readiness summary and review notes",
        "Approve and reject actions with reason capture",
        "Jump links into the full merchant detail page",
      ]}
    />
  );
}
