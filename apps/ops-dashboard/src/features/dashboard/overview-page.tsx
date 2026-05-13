const cards = [
  "Pending merchant reviews",
  "Active merchants",
  "Payments in last 24 hours",
  "Successful amount in last 24 hours",
  "Refunds in last 24 hours",
  "Open webhook failures",
  "Pending reconciliation records",
];

export function OverviewPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dashboard shape</p>
          <h3>Overview</h3>
        </div>
        <span className="status-badge">Route ready</span>
      </div>

      <p className="section-copy">
        These cards and panels reserve the primary operating surface for phase
        10. They make the information architecture concrete before auth, API
        integration, and live charts are wired in.
      </p>

      <div className="metric-grid">
        {cards.map((card) => (
          <article key={card} className="metric-card">
            <p>{card}</p>
            <strong>API pending</strong>
          </article>
        ))}
      </div>

      <div className="panel-grid">
        <article className="content-card">
          <h4>Queue widgets</h4>
          <ul className="checklist">
            <li>Newest onboarding items waiting for review</li>
            <li>Newest failed webhooks</li>
            <li>Newest reconciliation cases needing action</li>
          </ul>
        </article>

        <article className="content-card">
          <h4>Chart slots</h4>
          <ul className="checklist">
            <li>Payment status trend over 7 days</li>
            <li>Refund trend over 7 days</li>
            <li>Webhook delivery outcomes over 7 days</li>
            <li>Reconciliation created vs resolved over 7 days</li>
          </ul>
        </article>
      </div>
    </section>
  );
}
