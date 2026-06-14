import { useState, type ReactNode } from "react";

import { ContentCard, EmptyState } from "../common/ui";
import type {
  AmountTrend,
  ChartTone,
  StackedChartRow,
  VolumeChart,
  WebhookHealthRow,
} from "./chart-data";

const trendWidth = 360;
const trendHeight = 160;
const trendPadding = {
  top: 18,
  right: 14,
  bottom: 28,
  left: 18,
};

export function StackedStatusBars(props: { rows: StackedChartRow[] }) {
  const total = props.rows.reduce((sum, row) => sum + row.total, 0);
  const success = props.rows.reduce((sum, row) => sum + valueFor(row, "success"), 0);
  const successRate = total > 0 ? Math.round((success / total) * 100) : 0;

  return (
    <ChartCard
      title="Payment status mix"
      summary={`${successRate}% success`}
      tableHeaders={["Date", "Success", "Pending", "Failed", "Expired", "Total"]}
      tableRows={props.rows.map((row) => [
        row.label,
        valueFor(row, "success"),
        valueFor(row, "pending"),
        valueFor(row, "failed"),
        valueFor(row, "expired"),
        row.total,
      ])}
    >
      <StackedMiniChart
        label="Payment status mix chart"
        rows={props.rows}
        emptyLabel="No payment activity in this range."
      />
      <SegmentLegend
        items={[
          { label: "Success", tone: "good" },
          { label: "Pending", tone: "warn" },
          { label: "Failed", tone: "danger" },
          { label: "Expired", tone: "muted" },
        ]}
      />
    </ChartCard>
  );
}

export function AmountTrendChart(props: { trend: AmountTrend }) {
  if (props.trend.points.length === 0) {
    return (
      <ContentCard title="Successful amount trend">
        <EmptyState
          title="No amount data"
          message="Successful payment amount will appear here after activity."
        />
      </ContentCard>
    );
  }

  const latestPoint = props.trend.points[props.trend.points.length - 1];

  return (
    <ChartCard
      title="Successful amount trend"
      summary={`${formatCompactMoney(latestPoint?.value ?? 0)} latest`}
      tableHeaders={["Date", "Successful amount"]}
      tableRows={props.trend.points.map((point) => [
        point.label,
        cleanMoney(point.displayValue),
      ])}
    >
      <div className="visual-summary-row">
        <span>Latest</span>
        <strong>{cleanMoney(latestPoint?.displayValue ?? "0")}</strong>
      </div>
      <AmountMiniTrend trend={props.trend} />
    </ChartCard>
  );
}

export function RefundVolumeChart(props: { chart: VolumeChart }) {
  return (
    <ChartCard
      title="Refund volume"
      summary={`${props.chart.totalValue} refunds`}
      tableHeaders={["Date", "Refund count"]}
      tableRows={props.chart.points.map((point) => [point.label, point.value])}
    >
      <VolumeMiniChart label="Refund volume chart" chart={props.chart} tone="warn" />
    </ChartCard>
  );
}

export function WebhookHealthChart(props: { rows: WebhookHealthRow[] }) {
  const openCount = props.rows.reduce((sum, row) => sum + row.openCount, 0);

  return (
    <ChartCard
      title="Webhook delivery health"
      summary={`${openCount} open`}
      tableHeaders={["Date", "Delivered", "Pending", "Failed", "Total"]}
      tableRows={props.rows.map((row) => [
        row.label,
        valueFor(row, "delivered"),
        valueFor(row, "pending"),
        valueFor(row, "failed"),
        row.total,
      ])}
    >
      <StackedMiniChart
        label="Webhook delivery health chart"
        rows={props.rows}
        emptyLabel="No webhook events in this range."
      />
      <SegmentLegend
        items={[
          { label: "Delivered", tone: "good" },
          { label: "Pending", tone: "warn" },
          { label: "Failed", tone: "danger" },
        ]}
      />
    </ChartCard>
  );
}

function ChartCard(props: {
  title: string;
  summary: string;
  children: ReactNode;
  tableHeaders: string[];
  tableRows: Array<Array<string | number>>;
}) {
  const [showData, setShowData] = useState(false);
  return (
    <ContentCard
      title={props.title}
      action={<span className="visual-card-summary">{props.summary}</span>}
    >
      {props.children}
      <button
        type="button"
        className="secondary-button chart-data-toggle"
        onClick={() => setShowData((current) => !current)}
      >
        {showData ? "Hide data" : "View data"}
      </button>
      {showData ? (
        <div className="chart-data-table-wrap">
          <table className="chart-data-table">
            <thead>
              <tr>
                {props.tableHeaders.map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {props.tableRows.map((row, rowIndex) => (
                <tr key={`${row[0]}-${rowIndex}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${row[0]}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </ContentCard>
  );
}

function StackedMiniChart(props: {
  label: string;
  rows: StackedChartRow[];
  emptyLabel: string;
}) {
  const description = props.rows
    .map((row) => {
      const values = row.segments
        .map((segment) => `${segment.label} ${segment.value}`)
        .join(", ");
      return `${row.label}: ${values}`;
    })
    .join(". ");

  return (
    <div
      className="mini-stacked-chart"
      role="img"
      aria-label={`${props.label}. ${description || props.emptyLabel}`}
    >
      {props.rows.map((row) => (
        <div
          key={`${props.label}-${row.date}`}
          className="mini-stacked-row"
          aria-label={`${row.label}: ${row.total} total`}
        >
          <span className="mini-row-label">{row.label}</span>
          <div className="mini-stacked-track" aria-hidden="true">
            {row.total > 0 ? (
              row.segments.map((segment) =>
                segment.value > 0 ? (
                  <span
                    key={`${row.date}-${segment.key}`}
                    className={`mini-stacked-segment mini-tone-${segment.tone}`}
                    style={{ width: `${segment.percent}%` }}
                    title={`${row.label}: ${segment.value} ${segment.label}`}
                  />
                ) : null,
              )
            ) : (
              <span className="mini-stacked-empty" />
            )}
          </div>
          <strong>{row.total}</strong>
        </div>
      ))}
    </div>
  );
}

function AmountMiniTrend(props: { trend: AmountTrend }) {
  const points = props.trend.points.map((point, index) => {
    const x = xPosition(index, props.trend.points.length);
    const y =
      trendPadding.top +
      (1 - point.ratio) *
        (trendHeight - trendPadding.top - trendPadding.bottom);
    return {
      ...point,
      x,
      y,
    };
  });
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area =
    points.length > 0
      ? `${points.map((point) => `${point.x},${point.y}`).join(" ")} ${
          points[points.length - 1].x
        },${trendHeight - trendPadding.bottom} ${points[0].x},${
          trendHeight - trendPadding.bottom
        }`
      : "";
  const ariaLabel = points
    .map((point) => `${point.label}: ${cleanMoney(point.displayValue)}`)
    .join(". ");

  return (
    <svg
      className="mini-trend-chart"
      viewBox={`0 0 ${trendWidth} ${trendHeight}`}
      role="img"
      aria-label={`Successful amount trend chart. ${ariaLabel}`}
    >
      <line
        className="mini-axis-line"
        x1={trendPadding.left}
        y1={trendHeight - trendPadding.bottom}
        x2={trendWidth - trendPadding.right}
        y2={trendHeight - trendPadding.bottom}
      />
      <line
        className="mini-grid-line"
        x1={trendPadding.left}
        y1={trendPadding.top}
        x2={trendWidth - trendPadding.right}
        y2={trendPadding.top}
      />
      <polygon className="mini-trend-area" points={area} />
      <polyline className="mini-trend-line" points={line} />
      {points.map((point) => (
        <g key={point.date} aria-label={`${point.label}: ${cleanMoney(point.displayValue)}`}>
          <circle className="mini-trend-dot" cx={point.x} cy={point.y} r="4">
            <title>
              {point.label}: {cleanMoney(point.displayValue)}
            </title>
          </circle>
        </g>
      ))}
      {points.length > 0 ? (
        <>
          <text className="mini-axis-label" x={points[0].x} y={trendHeight - 7}>
            {points[0].label}
          </text>
          <text
            className="mini-axis-label mini-axis-label-end"
            x={points[points.length - 1].x}
            y={trendHeight - 7}
          >
            {points[points.length - 1].label}
          </text>
        </>
      ) : null}
    </svg>
  );
}

function VolumeMiniChart(props: {
  label: string;
  chart: VolumeChart;
  tone: ChartTone;
}) {
  const ariaLabel = props.chart.points
    .map((point) => `${point.label}: ${point.value}`)
    .join(". ");

  return (
    <div
      className="mini-volume-chart"
      role="img"
      aria-label={`${props.label}. ${ariaLabel || "No values."}`}
    >
      {props.chart.points.map((point) => (
        <div key={`${props.label}-${point.date}`} className="mini-volume-column">
          <div className="mini-volume-track" aria-hidden="true">
            <span
              className={`mini-volume-bar mini-tone-${props.tone}`}
              style={{
                height: point.value > 0 ? `${Math.max(point.ratio * 100, 8)}%` : "0%",
              }}
              title={`${point.label}: ${point.value}`}
            />
          </div>
          <span className="mini-volume-label">{point.label}</span>
        </div>
      ))}
    </div>
  );
}

function SegmentLegend(props: { items: Array<{ label: string; tone: ChartTone }> }) {
  return (
    <div className="mini-legend" aria-hidden="true">
      {props.items.map((item) => (
        <span key={item.label}>
          <i className={`mini-legend-swatch mini-tone-${item.tone}`} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function xPosition(index: number, count: number) {
  if (count <= 1) {
    return trendWidth / 2;
  }
  return (
    trendPadding.left +
    (index / (count - 1)) *
      (trendWidth - trendPadding.left - trendPadding.right)
  );
}

function valueFor(row: StackedChartRow, key: string) {
  return row.segments.find((segment) => segment.key === key)?.value ?? 0;
}

function cleanMoney(value: unknown) {
  return String(value).replace(/\u00a0/g, " ");
}

function formatCompactMoney(value: number) {
  if (value >= 1_000_000) {
    return `${Math.round(value / 1_000_000)}m`;
  }
  if (value >= 1_000) {
    return `${Math.round(value / 1_000)}k`;
  }
  return `${value}`;
}
