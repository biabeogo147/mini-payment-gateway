type PlaceholderPageProps = {
  title: string;
  description: string;
  plannedItems: string[];
};

export function PlaceholderPage({
  title,
  description,
  plannedItems,
}: PlaceholderPageProps) {
  return (
    <section className="content-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Planned for phase 10</p>
          <h3>{title}</h3>
        </div>
        <span className="status-badge status-badge-muted">Scaffold only</span>
      </div>

      <p className="section-copy">{description}</p>

      <ul className="checklist">
        {plannedItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
