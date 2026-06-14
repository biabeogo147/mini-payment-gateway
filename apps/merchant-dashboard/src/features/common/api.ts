export type MerchantUserRole = "MERCHANT_ADMIN" | "MERCHANT_VIEWER";
export type MerchantUserStatus = "ACTIVE" | "INACTIVE";
export type MerchantStatus =
  | "PENDING_REVIEW"
  | "ACTIVE"
  | "REJECTED"
  | "SUSPENDED"
  | "DISABLED";
export type CredentialStatus = "ACTIVE" | "INACTIVE" | "ROTATED";
export type PaymentStatus = "PENDING" | "SUCCESS" | "FAILED" | "EXPIRED";
export type RefundStatus = "REFUND_PENDING" | "REFUNDED" | "REFUND_FAILED";
export type WebhookEventStatus = "PENDING" | "DELIVERED" | "FAILED";
export type EntityType =
  | "PAYMENT"
  | "REFUND"
  | "MERCHANT"
  | "MERCHANT_CREDENTIAL"
  | "ONBOARDING_CASE"
  | "WEBHOOK_EVENT"
  | "RECONCILIATION"
  | "INTERNAL_USER"
  | "MERCHANT_USER";
export type DeliveryAttemptResult =
  | "SUCCESS"
  | "FAILED"
  | "TIMEOUT"
  | "NETWORK_ERROR";
export type CallbackSourceType =
  | "BANK"
  | "NAPAS"
  | "SIMULATOR"
  | "QR_PROVIDER";
export type CallbackType = "PAYMENT_RESULT" | "REFUND_RESULT";
export type CallbackProcessingResult =
  | "PROCESSED"
  | "IGNORED"
  | "FAILED"
  | "PENDING_REVIEW";

export type JsonObject = Record<string, unknown>;

export class ApiError extends Error {
  statusCode: number;
  errorCode: string;
  details?: unknown;

  constructor(
    message: string,
    options: { statusCode: number; errorCode?: string; details?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.statusCode = options.statusCode;
    this.errorCode = options.errorCode ?? "UNKNOWN_ERROR";
    this.details = options.details;
  }
}

export interface MerchantPortalUser {
  user_id: string;
  merchant_id: string;
  email: string;
  full_name: string;
  role: MerchantUserRole;
  status: MerchantUserStatus;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MerchantAuthSessionResponse {
  user: MerchantPortalUser;
  merchant_status: MerchantStatus;
}

export interface DashboardSummary {
  payments_last_24h: number;
  successful_payment_amount_last_24h: string;
  pending_payments: number;
  refunds_last_24h: number;
  open_webhook_events: number;
}

export interface PaymentStatusChartPoint {
  date: string;
  pending: number;
  success: number;
  failed: number;
  expired: number;
}

export interface PaymentAmountChartPoint {
  date: string;
  amount: string;
}

export interface RefundCountChartPoint {
  date: string;
  count: number;
}

export interface WebhookStatusChartPoint {
  date: string;
  pending: number;
  delivered: number;
  failed: number;
}

export interface DashboardCharts {
  payment_status_by_day: PaymentStatusChartPoint[];
  successful_payment_amount_by_day: PaymentAmountChartPoint[];
  refund_count_by_day: RefundCountChartPoint[];
  webhook_status_by_day: WebhookStatusChartPoint[];
}

export type AnalyticsDays = 7 | 30 | 90;

export interface MerchantAnalyticsRange {
  days: AnalyticsDays;
  start_date: string;
  end_date: string;
}

export interface MerchantAnalyticsTotals {
  payment_count: number;
  successful_payment_count: number;
  successful_payment_amount: string;
  success_rate: number;
  refund_count: number;
  refunded_amount: string;
  webhook_count: number;
  webhook_delivery_rate: number;
}

export interface MerchantPaymentAnalyticsPoint {
  date: string;
  pending: number;
  success: number;
  failed: number;
  expired: number;
  total: number;
  successful_amount: string;
  success_rate: number;
}

export interface MerchantRefundAnalyticsPoint {
  date: string;
  pending: number;
  refunded: number;
  failed: number;
  count: number;
  amount: string;
}

export interface MerchantWebhookAnalyticsPoint {
  date: string;
  pending: number;
  delivered: number;
  failed: number;
  total: number;
  delivery_rate: number;
}

export interface MerchantAnalyticsSeries {
  payment_by_day: MerchantPaymentAnalyticsPoint[];
  refund_by_day: MerchantRefundAnalyticsPoint[];
  webhook_by_day: MerchantWebhookAnalyticsPoint[];
}

export interface MerchantTopWebhookEventType {
  event_type: string;
  count: number;
  pending: number;
  failed: number;
}

export interface MerchantAnalyticsAttention {
  failed_or_expired_payments: number;
  refund_failures: number;
  open_webhooks: number;
  top_webhook_event_types: MerchantTopWebhookEventType[];
}

export interface MerchantAnalyticsResponse {
  range: MerchantAnalyticsRange;
  totals: MerchantAnalyticsTotals;
  series: MerchantAnalyticsSeries;
  attention: MerchantAnalyticsAttention;
}

export interface MerchantProfile {
  merchant_id: string;
  merchant_name: string;
  legal_name: string | null;
  contact_name: string | null;
  contact_email: string;
  contact_phone: string | null;
  webhook_url: string | null;
  allowed_ip_list: string[] | null;
  status: MerchantStatus;
  created_at: string;
  updated_at: string;
}

export interface MerchantCredential {
  credential_id: string;
  access_key: string;
  secret_key_last4: string;
  status: CredentialStatus;
  expired_at: string | null;
  rotated_at: string | null;
  created_at: string;
}

export interface CallbackEvidence {
  callback_id: string;
  source_type: CallbackSourceType;
  callback_type: CallbackType;
  external_reference: string | null;
  transaction_reference: string | null;
  normalized_status: string | null;
  processing_result: CallbackProcessingResult;
  error_message: string | null;
  raw_payload_json: JsonObject;
  received_at: string;
  processed_at: string | null;
}

export interface PaymentRefundLink {
  refund_transaction_id: string;
  refund_id: string;
  refund_amount: string;
  refund_status: RefundStatus;
  created_at: string;
}

export interface PaymentListItem {
  transaction_id: string;
  merchant_id: string;
  merchant_name: string;
  order_id: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  expire_at: string;
  paid_at: string | null;
  created_at: string;
}

export interface PaymentDetail extends PaymentListItem {
  description: string;
  qr_content: string;
  qr_image_url: string | null;
  qr_image_base64: string | null;
  external_reference: string | null;
  idempotency_key: string | null;
  failed_reason_code: string | null;
  failed_reason_message: string | null;
  callback_logs: CallbackEvidence[];
  refunds: PaymentRefundLink[];
}

export interface RefundListItem {
  refund_transaction_id: string;
  refund_id: string;
  merchant_id: string;
  merchant_name: string;
  original_transaction_id: string;
  refund_amount: string;
  refund_status: RefundStatus;
  reason: string;
  created_at: string;
}

export interface RefundDetail extends RefundListItem {
  external_reference: string | null;
  idempotency_key: string | null;
  processed_at: string | null;
  failed_reason_code: string | null;
  failed_reason_message: string | null;
  callback_logs: CallbackEvidence[];
}

export interface WebhookAttempt {
  attempt_id: string;
  attempt_no: number;
  request_url: string;
  response_status_code: number | null;
  response_body_snippet: string | null;
  error_message: string | null;
  result: DeliveryAttemptResult;
  started_at: string;
  finished_at: string | null;
}

export interface WebhookEventListItem {
  event_id: string;
  merchant_id: string;
  merchant_name: string;
  event_type: string;
  entity_type: EntityType;
  entity_id: string;
  status: WebhookEventStatus;
  attempt_count: number;
  next_retry_at: string | null;
  last_attempt_at: string | null;
  created_at: string;
}

export interface WebhookEventDetail extends WebhookEventListItem {
  payload_json: JsonObject;
  signature: string | null;
  attempts: WebhookAttempt[];
  latest_failure_reason: string | null;
}

type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Date;

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(
  /\/$/,
  "",
);

function toQueryString(values: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.set(key, value instanceof Date ? value.toISOString() : String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { bodyJson?: unknown },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.bodyJson !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    body:
      init?.bodyJson !== undefined
        ? JSON.stringify(init.bodyJson)
        : init?.body,
  });

  if (!response.ok) {
    let payload: Record<string, unknown> | null = null;
    try {
      payload = (await response.json()) as Record<string, unknown>;
    } catch {
      payload = null;
    }
    throw new ApiError(
      typeof payload?.message === "string"
        ? payload.message
        : `Request failed with status ${response.status}`,
      {
        statusCode: response.status,
        errorCode:
          typeof payload?.error_code === "string"
            ? payload.error_code
            : undefined,
        details: payload?.details,
      },
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function loginMerchantAuth(payload: {
  merchant_id: string;
  email: string;
  password: string;
}) {
  return apiFetch<MerchantAuthSessionResponse>("/v1/merchant-portal/auth/login", {
    method: "POST",
    bodyJson: payload,
  });
}

export async function logoutMerchantAuth() {
  return apiFetch<{ status: string }>("/v1/merchant-portal/auth/logout", {
    method: "POST",
  });
}

export async function getCurrentSession() {
  return apiFetch<MerchantAuthSessionResponse>("/v1/merchant-portal/auth/me");
}

export async function changeMerchantPassword(payload: {
  current_password: string;
  new_password: string;
}) {
  return apiFetch<MerchantAuthSessionResponse>(
    "/v1/merchant-portal/auth/change-password",
    {
      method: "POST",
      bodyJson: payload,
    },
  );
}

export async function getDashboardSummary() {
  return apiFetch<DashboardSummary>("/v1/merchant-portal/dashboard/summary");
}

export async function getDashboardCharts() {
  return apiFetch<DashboardCharts>("/v1/merchant-portal/dashboard/charts");
}

export async function getMerchantAnalytics(days: AnalyticsDays = 30) {
  return apiFetch<MerchantAnalyticsResponse>(
    `/v1/merchant-portal/analytics${toQueryString({ days })}`,
  );
}

export async function getProfile() {
  return apiFetch<MerchantProfile>("/v1/merchant-portal/profile");
}

export async function listCredentials() {
  return apiFetch<{ credentials: MerchantCredential[] }>(
    "/v1/merchant-portal/credentials",
  );
}

export async function listPayments(filters: {
  transaction_id?: string;
  order_id?: string;
  status?: PaymentStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ payments: PaymentListItem[] }>(
    `/v1/merchant-portal/payments${toQueryString(filters)}`,
  );
}

export async function getPaymentDetail(transactionId: string) {
  return apiFetch<PaymentDetail>(`/v1/merchant-portal/payments/${transactionId}`);
}

export async function listRefunds(filters: {
  refund_transaction_id?: string;
  refund_id?: string;
  status?: RefundStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ refunds: RefundListItem[] }>(
    `/v1/merchant-portal/refunds${toQueryString(filters)}`,
  );
}

export async function getRefundDetail(refundTransactionId: string) {
  return apiFetch<RefundDetail>(
    `/v1/merchant-portal/refunds/${refundTransactionId}`,
  );
}

export async function listWebhooks(filters: {
  event_type?: string;
  status?: WebhookEventStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ events: WebhookEventListItem[] }>(
    `/v1/merchant-portal/webhooks${toQueryString(filters)}`,
  );
}

export async function getWebhookDetail(eventId: string) {
  return apiFetch<WebhookEventDetail>(`/v1/merchant-portal/webhooks/${eventId}`);
}
