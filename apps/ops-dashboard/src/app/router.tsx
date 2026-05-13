import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "./layout";
import { LoginPage } from "../features/auth/login-page";
import { AuditPage } from "../features/audit/audit-page";
import { OverviewPage } from "../features/dashboard/overview-page";
import { InternalUsersPage } from "../features/internal-users/internal-users-page";
import { MerchantsPage } from "../features/merchants/merchants-page";
import { OnboardingPage } from "../features/onboarding/onboarding-page";
import { PaymentsPage } from "../features/payments/payments-page";
import { ReconciliationPage } from "../features/reconciliation/reconciliation-page";
import { RefundsPage } from "../features/refunds/refunds-page";
import { WebhooksPage } from "../features/webhooks/webhooks-page";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "merchants", element: <MerchantsPage /> },
      { path: "onboarding", element: <OnboardingPage /> },
      { path: "payments", element: <PaymentsPage /> },
      { path: "refunds", element: <RefundsPage /> },
      { path: "webhooks", element: <WebhooksPage /> },
      { path: "reconciliation", element: <ReconciliationPage /> },
      { path: "audit", element: <AuditPage /> },
      { path: "internal-users", element: <InternalUsersPage /> },
    ],
  },
]);
