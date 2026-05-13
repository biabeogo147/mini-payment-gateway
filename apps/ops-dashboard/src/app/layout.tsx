import { useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { changeInternalPassword, logoutInternalAuth } from "../features/common/api";
import { sessionQueryKey } from "../features/common/query";
import { ErrorCard, InlineField, StatusBadge } from "../features/common/ui";
import { useSession } from "../features/auth/use-session";

const navigation = [
  { to: "/", label: "Overview" },
  { to: "/merchants", label: "Merchants" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/payments", label: "Payments" },
  { to: "/refunds", label: "Refunds" },
  { to: "/webhooks", label: "Webhooks" },
  { to: "/reconciliation", label: "Reconciliation" },
  { to: "/audit", label: "Audit" },
  { to: "/internal-users", label: "Internal Users", adminOnly: true },
];

export function AppLayout() {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: session, isLoading, error } = useSession();
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const logoutMutation = useMutation({
    mutationFn: logoutInternalAuth,
    onSuccess: async () => {
      await queryClient.setQueryData(sessionQueryKey, null);
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: changeInternalPassword,
    onSuccess: async (payload) => {
      queryClient.setQueryData(sessionQueryKey, payload);
      setCurrentPassword("");
      setNewPassword("");
      setShowPasswordForm(false);
    },
  });

  if (isLoading) {
    return (
      <div className="login-shell">
        <section className="login-card">
          <p className="eyebrow">Ops Console</p>
          <h1>Restoring internal session</h1>
          <p className="section-copy">
            The console is checking the secure operator session before it
            unlocks the live data surface.
          </p>
        </section>
      </div>
    );
  }

  if (error instanceof Error) {
    return (
      <div className="login-shell">
        <section className="login-card">
          <ErrorCard
            title="Session check failed"
            message={error.message}
          />
        </section>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  const visibleNavigation = navigation.filter(
    (item) => !item.adminOnly || session.user.role === "ADMIN",
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Mini Payment Gateway</p>
          <h1>Ops Console</h1>
          <p className="lede">
            Internal operating surface for onboarding, transaction support,
            webhook recovery, reconciliation, and audit review.
          </p>
        </div>

        <nav className="nav-list" aria-label="Primary">
          {visibleNavigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
              end={item.to === "/"}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="status-card">
          <p className="eyebrow">Active session</p>
          <h4>{session.user.full_name}</h4>
          <p>{session.user.email}</p>
          <div className="status-stack">
            <StatusBadge value={session.user.role} />
            <StatusBadge value={session.user.status} />
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Authenticated operator</p>
            <h2>Internal Ops Dashboard</h2>
          </div>

          <div className="topbar-meta">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setShowPasswordForm((current) => !current)}
            >
              {showPasswordForm ? "Hide password form" : "Change password"}
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            >
              {logoutMutation.isPending ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </header>

        {showPasswordForm ? (
          <section className="content-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Credential hygiene</p>
                <h3>Change internal password</h3>
              </div>
            </div>
            <div className="form-grid">
              <InlineField label="Current password">
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                />
              </InlineField>
              <InlineField label="New password">
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </InlineField>
            </div>
            <div className="inline-actions">
              <button
                type="button"
                className="primary-button"
                disabled={
                  changePasswordMutation.isPending ||
                  currentPassword.length < 1 ||
                  newPassword.length < 8
                }
                onClick={() =>
                  changePasswordMutation.mutate({
                    current_password: currentPassword,
                    new_password: newPassword,
                  })
                }
              >
                {changePasswordMutation.isPending
                  ? "Updating..."
                  : "Update password"}
              </button>
              {changePasswordMutation.error instanceof Error ? (
                <span className="feedback feedback-danger">
                  {changePasswordMutation.error.message}
                </span>
              ) : null}
            </div>
          </section>
        ) : null}

        <Outlet />
      </main>
    </div>
  );
}
