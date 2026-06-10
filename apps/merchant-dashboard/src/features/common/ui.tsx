import type { PropsWithChildren, ReactNode } from "react";

import type {
  CredentialStatus,
  MerchantStatus,
  MerchantUserRole,
  MerchantUserStatus,
  PaymentStatus,
  RefundStatus,
  WebhookEventStatus,
} from "./api";
import { formatPercent } from "./format";

type Tone =
  | CredentialStatus
  | MerchantStatus
  | MerchantUserRole
  | MerchantUserStatus
  | PaymentStatus
  | RefundStatus
  | WebhookEventStatus
  | "TIMEOUT"
  | "NETWORK_ERROR"
  | "info";

const toneClassMap: Record<Tone, string> = {
  ACTIVE: "status-tone-good",
  MERCHANT_ADMIN: "status-tone-good",
  MERCHANT_VIEWER: "status-tone-info",
  SUCCESS: "status-tone-good",
  DELIVERED: "status-tone-good",
  REFUNDED: "status-tone-good",
  PENDING: "status-tone-warn",
  PENDING_REVIEW: "status-tone-warn",
  REFUND_PENDING: "status-tone-warn",
  ROTATED: "status-tone-warn",
  INACTIVE: "status-tone-muted",
  EXPIRED: "status-tone-muted",
  REJECTED: "status-tone-danger",
  FAILED: "status-tone-danger",
  REFUND_FAILED: "status-tone-danger",
  DISABLED: "status-tone-danger",
  SUSPENDED: "status-tone-danger",
  TIMEOUT: "status-tone-danger",
  NETWORK_ERROR: "status-tone-danger",
  info: "status-tone-info",
};

export function PageHeader(props: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{props.eyebrow}</p>
        <h3>{props.title}</h3>
        <p className="section-copy">{props.description}</p>
      </div>
      {props.actions}
    </div>
  );
}

export function ContentCard(props: PropsWithChildren<{ title?: string; action?: ReactNode }>) {
  return (
    <section className="content-card">
      {props.title ? (
        <div className="card-title-row">
          <h4>{props.title}</h4>
          {props.action}
        </div>
      ) : null}
      {props.children}
    </section>
  );
}

export function MetricCard(props: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <article className="metric-card">
      <p>{props.label}</p>
      <strong>{props.value}</strong>
      {props.hint ? <span className="metric-hint">{props.hint}</span> : null}
    </article>
  );
}

export function StatusBadge(props: { value: Tone | string }) {
  const tone = toneClassMap[props.value as Tone] ?? "status-tone-info";
  return <span className={`status-inline ${tone}`}>{props.value}</span>;
}

export function ErrorCard(props: { title?: string; message: string }) {
  return (
    <ContentCard>
      <div className="empty-state empty-state-danger">
        <strong>{props.title ?? "Something went wrong"}</strong>
        <p>{props.message}</p>
      </div>
    </ContentCard>
  );
}

export function EmptyState(props: { title: string; message: string }) {
  return (
    <div className="empty-state">
      <strong>{props.title}</strong>
      <p>{props.message}</p>
    </div>
  );
}

export function InlineField(props: PropsWithChildren<{ label: string }>) {
  return (
    <label className="field">
      <span>{props.label}</span>
      {props.children}
    </label>
  );
}

export function DetailGrid(props: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="detail-grid">
      {props.items.map((item) => (
        <div key={item.label} className="detail-item">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function JsonBlock(props: { value: unknown }) {
  return <pre className="json-block">{JSON.stringify(props.value, null, 2)}</pre>;
}

export function ChartStrip(props: {
  title: string;
  rows: Array<{ label: string; value: number; tone?: string }>;
}) {
  const max = props.rows.reduce((current, row) => Math.max(current, row.value), 0) || 1;
  return (
    <ContentCard title={props.title}>
      <div className="chart-stack">
        {props.rows.map((row) => {
          const width = (row.value / max) * 100;
          return (
            <div key={`${props.title}-${row.label}`} className="chart-row">
              <div className="chart-row-head">
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </div>
              <div className="chart-bar-track">
                <div
                  className={`chart-bar-fill ${row.tone ?? ""}`}
                  style={{ width: formatPercent(width) }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </ContentCard>
  );
}
