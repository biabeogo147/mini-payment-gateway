import { QueryClient } from "@tanstack/react-query";

export const sessionQueryKey = ["internal-session"] as const;

const dashboardQueryPrefixes = [
  ["dashboard-summary"],
  ["dashboard-charts"],
  ["merchants"],
  ["merchant-detail"],
  ["merchant-onboarding"],
  ["merchant-credentials"],
  ["payments"],
  ["payment-detail"],
  ["refunds"],
  ["refund-detail"],
  ["webhooks"],
  ["webhook-detail"],
  ["reconciliation"],
  ["reconciliation-detail"],
  ["audit-logs"],
  ["internal-users"],
] as const;

export async function invalidateOpsConsoleData(queryClient: QueryClient) {
  await Promise.all(
    dashboardQueryPrefixes.map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}
