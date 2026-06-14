import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "./layout";
import { LoginPage } from "../features/auth/login-page";
import { OverviewPage } from "../features/dashboard/overview-page";
import { PaymentsPage } from "../features/payments/payments-page";
import { RefundsPage } from "../features/refunds/refunds-page";
import { WebhooksPage } from "../features/webhooks/webhooks-page";
import { ProfilePage } from "../features/profile/profile-page";
import { CredentialsPage } from "../features/credentials/credentials-page";
import { ContentCard, EmptyState } from "../features/common/ui";

const AnalyticsPage = lazy(() =>
  import("../features/analytics/analytics-page").then((module) => ({
    default: module.AnalyticsPage,
  })),
);

function LazyRoute(props: { label: string; children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <section className="page-stack">
          <ContentCard>
            <EmptyState title={`Loading ${props.label}`} message="Preparing this workspace view." />
          </ContentCard>
        </section>
      }
    >
      {props.children}
    </Suspense>
  );
}

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
      {
        path: "analytics",
        element: (
          <LazyRoute label="analytics">
            <AnalyticsPage />
          </LazyRoute>
        ),
      },
      { path: "payments", element: <PaymentsPage /> },
      { path: "refunds", element: <RefundsPage /> },
      { path: "webhooks", element: <WebhooksPage /> },
      { path: "profile", element: <ProfilePage /> },
      { path: "credentials", element: <CredentialsPage /> },
    ],
  },
]);
