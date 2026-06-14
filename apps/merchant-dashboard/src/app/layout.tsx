import { useState } from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { changeMerchantPassword, logoutMerchantAuth } from "../features/common/api";
import { sessionQueryKey } from "../features/common/query";
import { ErrorCard, InlineField, StatusBadge } from "../features/common/ui";
import { useSession } from "../features/auth/use-session";

const navigation = [
  { to: "/", label: "Overview" },
  { to: "/analytics", label: "Analytics" },
  { to: "/payments", label: "Payments" },
  { to: "/refunds", label: "Refunds" },
  { to: "/webhooks", label: "Webhooks" },
  { to: "/profile", label: "Profile" },
  { to: "/credentials", label: "Credentials" },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: session, isLoading, error } = useSession();
  const [lookup, setLookup] = useState("");
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const logoutMutation = useMutation({
    mutationFn: logoutMerchantAuth,
    onSuccess: async () => {
      await queryClient.setQueryData(sessionQueryKey, null);
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: changeMerchantPassword,
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
          <p className="eyebrow">Merchant Dashboard</p>
          <h1>Restoring session</h1>
          <p className="section-copy">Checking the secure merchant session.</p>
        </section>
      </div>
    );
  }

  if (error instanceof Error) {
    return (
      <div className="login-shell">
        <section className="login-card">
          <ErrorCard title="Session check failed" message={error.message} />
        </section>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  function submitLookup() {
    const value = lookup.trim();
    if (!value) {
      return;
    }
    if (value.startsWith("pay_")) {
      navigate(`/payments?transaction_id=${encodeURIComponent(value)}`);
    } else if (value.startsWith("rfnd_")) {
      navigate(`/refunds?refund_transaction_id=${encodeURIComponent(value)}`);
    } else if (value.toUpperCase().startsWith("REF-")) {
      navigate(`/refunds?refund_id=${encodeURIComponent(value)}`);
    } else {
      navigate(`/payments?order_id=${encodeURIComponent(value)}`);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Mini Payment Gateway</p>
          <h1>Merchant Dashboard</h1>
          <p className="lede">
            Read-only visibility for transactions, refunds, webhook delivery,
            and integration metadata.
          </p>
        </div>

        <div className="status-card session-card" aria-label="Merchant status">
          <p className="eyebrow">Merchant status</p>
          <h4>{session.user.merchant_id}</h4>
          <p>{session.user.email}</p>
          <div className="status-stack">
            <StatusBadge value={session.merchant_status} />
            <StatusBadge value={session.user.role} />
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary">
          {navigation.map((item) => (
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
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-heading">
            <p className="eyebrow">Merchant workspace</p>
            <h2>{session.user.full_name}</h2>
          </div>

          <div className="lookup-row">
            <input
              value={lookup}
              onChange={(event) => setLookup(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  submitLookup();
                }
              }}
              placeholder="Lookup pay_, rfnd_, ORDER-, REF-"
            />
            <button type="button" className="secondary-button" onClick={submitLookup}>
              Lookup
            </button>
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
              disabled={logoutMutation.isPending}
              onClick={() => logoutMutation.mutate()}
            >
              {logoutMutation.isPending ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </header>

        {showPasswordForm ? (
          <section className="content-card">
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
