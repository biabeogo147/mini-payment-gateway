export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatMoney(value: string | number | null | undefined) {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return String(value ?? "0");
  }

  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function formatCompactNumber(value: number) {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}
