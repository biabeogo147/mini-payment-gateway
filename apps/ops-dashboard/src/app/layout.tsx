import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { to: "/", label: "Overview" },
  { to: "/merchants", label: "Merchants" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/payments", label: "Payments" },
  { to: "/refunds", label: "Refunds" },
  { to: "/webhooks", label: "Webhooks" },
  { to: "/reconciliation", label: "Reconciliation" },
  { to: "/audit", label: "Audit" },
  { to: "/internal-users", label: "Internal Users" },
];

export function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Mini Payment Gateway</p>
          <h1>Ops Console</h1>
          <p className="lede">
            Phase 10 scaffold is ready. Auth, RBAC, and live data wiring land
            in the implementation phase.
          </p>
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

        <div className="status-card">
          <span className="status-badge">Sandbox Ready</span>
          <p>
            This shell gives phase 10 a stable place to land without deciding
            UI structure mid-implementation.
          </p>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Prepared ahead of phase 10</p>
            <h2>Internal Ops Dashboard</h2>
          </div>

          <div className="topbar-meta">
            <span className="env-pill">role model: ADMIN / OPS</span>
            <NavLink className="topbar-link" to="/login">
              Preview login
            </NavLink>
          </div>
        </header>

        <Outlet />
      </main>
    </div>
  );
}
