import { NavLink } from "react-router-dom";

export function LoginPage() {
  return (
    <div className="login-shell">
      <section className="login-card">
        <div>
          <p className="eyebrow">Phase 10 entry point</p>
          <h1>Internal operator login</h1>
          <p className="section-copy">
            This preview screen marks where secure internal auth will land. The
            phase 10 implementation will add server-backed sessions, password
            flows, and role-based route guards here.
          </p>
        </div>

        <div className="login-fields">
          <label className="field">
            <span>Email</span>
            <input type="email" placeholder="ops@example.com" disabled />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" placeholder="••••••••" disabled />
          </label>
        </div>

        <div className="login-actions">
          <button type="button" className="primary-button" disabled>
            Sign in
          </button>
          <NavLink className="secondary-link" to="/">
            Back to shell
          </NavLink>
        </div>
      </section>
    </div>
  );
}
