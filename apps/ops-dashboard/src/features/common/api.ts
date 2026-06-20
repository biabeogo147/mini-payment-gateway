export type InternalUserRole = "ADMIN" | "OPS";
export type InternalUserStatus = "ACTIVE" | "INACTIVE";
export type MerchantUserRole = "MERCHANT_ADMIN" | "MERCHANT_VIEWER";
export type MerchantUserStatus = "ACTIVE" | "INACTIVE";
export type MerchantStatus =
  | "PENDING_REVIEW"
  | "ACTIVE"
  | "REJECTED"
  | "SUSPENDED"
  | "DISABLED";
export type OnboardingCaseStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED";
export type CredentialStatus = "ACTIVE" | "INACTIVE" | "ROTATED";
export type QrProvider = "VIETQR";
export type MerchantQrAccountStatus = "ACTIVE" | "INACTIVE";
export type PaymentStatus = "PENDING" | "SUCCESS" | "FAILED" | "EXPIRED";
export type RefundStatus =
  | "REFUND_PENDING"
  | "REFUNDED"
  | "REFUND_FAILED";
export type WebhookEventStatus = "PENDING" | "DELIVERED" | "FAILED";
export type ReconciliationStatus =
  | "MATCHED"
  | "MISMATCHED"
  | "PENDING_REVIEW"
  | "RESOLVED";
export type ActorType = "SYSTEM" | "ADMIN" | "OPS" | "MERCHANT";
export type EntityType =
  | "PAYMENT"
  | "REFUND"
  | "MERCHANT"
  | "MERCHANT_CREDENTIAL"
  | "MERCHANT_QR_ACCOUNT"
  | "ONBOARDING_CASE"
  | "WEBHOOK_EVENT"
  | "RECONCILIATION"
  | "INTERNAL_USER"
  | "MERCHANT_USER";
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
export type DeliveryAttemptResult =
  | "SUCCESS"
  | "FAILED"
  | "TIMEOUT"
  | "NETWORK_ERROR";

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

export interface InternalUser {
  user_id: string;
  email: string;
  full_name: string;
  role: InternalUserRole;
  status: InternalUserStatus;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
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

export interface MerchantPortalGeneratedPasswordResponse {
  user: MerchantPortalUser;
  generated_password: string;
}

export interface InternalAuthSessionResponse {
  user: InternalUser;
}

export interface BootstrapStatusResponse {
  bootstrap_required: boolean;
}

export interface MerchantListItem {
  merchant_id: string;
  merchant_name: string;
  contact_email: string;
  contact_name: string | null;
  webhook_url: string | null;
  status: MerchantStatus;
  onboarding_status: OnboardingCaseStatus | null;
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

export interface MerchantQrAccount {
  qr_account_id: string;
  merchant_id?: string;
  provider: QrProvider;
  bank_code: string;
  bank_bin: string;
  account_number: string;
  account_name: string;
  template: string;
  status: MerchantQrAccountStatus;
  created_at: string | null;
  updated_at: string | null;
}

export interface OnboardingCaseDetail {
  case_id: string;
  status: OnboardingCaseStatus;
  domain_or_app_name: string | null;
  submitted_profile_json: JsonObject;
  documents_json: JsonObject;
  review_checks_json: JsonObject;
  decision_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLogItem {
  log_id: string;
  event_type: string;
  entity_type: EntityType;
  entity_id: string;
  actor_type: ActorType;
  actor_id: string | null;
  reason: string | null;
  before_state_json: JsonObject | null;
  after_state_json: JsonObject | null;
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

export interface ReconciliationRecord {
  record_id: string;
  entity_type: EntityType;
  entity_id: string;
  internal_status: string;
  external_status: string;
  internal_amount: string;
  external_amount: string;
  match_result: ReconciliationStatus;
  mismatch_reason_code: string | null;
  mismatch_reason_message: string | null;
  reviewed_by: string | null;
  review_note: string | null;
  created_at: string | null;
  updated_at: string | null;
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
  qr_reference: string | null;
  qr_content: string;
  qr_image_url: string | null;
  qr_image_base64: string | null;
  external_reference: string | null;
  idempotency_key: string | null;
  failed_reason_code: string | null;
  failed_reason_message: string | null;
  callback_logs: CallbackEvidence[];
  refunds: PaymentRefundLink[];
  reconciliation: ReconciliationRecord | null;
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
  reconciliation: ReconciliationRecord | null;
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

export interface MerchantDetail {
  merchant_id: string;
  merchant_name: string;
  legal_name: string | null;
  contact_name: string | null;
  contact_email: string;
  contact_phone: string | null;
  webhook_url: string | null;
  allowed_ip_list: string[] | null;
  status: MerchantStatus;
  settlement_account_name: string | null;
  settlement_account_number: string | null;
  settlement_bank_code: string | null;
  created_at: string;
  updated_at: string;
  onboarding_case: OnboardingCaseDetail | null;
  credentials: MerchantCredential[];
  qr_accounts: MerchantQrAccount[];
  recent_payments: PaymentListItem[];
  recent_refunds: RefundListItem[];
  recent_webhooks: WebhookEventListItem[];
  recent_audit_logs: AuditLogItem[];
}

export interface DashboardMerchantQueueItem {
  merchant_id: string;
  merchant_name: string;
  onboarding_status: OnboardingCaseStatus;
  domain_or_app_name: string | null;
  updated_at: string;
}

export interface DashboardWebhookQueueItem {
  event_id: string;
  merchant_id: string;
  merchant_name: string;
  event_type: string;
  status: WebhookEventStatus;
  attempt_count: number;
  updated_at: string;
}

export interface DashboardReconciliationQueueItem {
  record_id: string;
  entity_type: EntityType;
  match_result: ReconciliationStatus;
  mismatch_reason_code: string | null;
  created_at: string | null;
}

export interface DashboardSummary {
  merchants_pending_review: number;
  merchants_active: number;
  payments_last_24h: number;
  successful_payment_amount_last_24h: string;
  refunds_last_24h: number;
  failed_webhook_events_open: number;
  reconciliation_open: number;
  onboarding_queue: DashboardMerchantQueueItem[];
  failed_webhooks: DashboardWebhookQueueItem[];
  reconciliation_queue: DashboardReconciliationQueueItem[];
}

export interface PaymentStatusChartPoint {
  date: string;
  pending: number;
  success: number;
  failed: number;
  expired: number;
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

export interface ReconciliationChartPoint {
  date: string;
  created: number;
  resolved: number;
}

export interface DashboardCharts {
  payment_status_by_day: PaymentStatusChartPoint[];
  refund_count_by_day: RefundCountChartPoint[];
  webhook_status_by_day: WebhookStatusChartPoint[];
  reconciliation_by_day: ReconciliationChartPoint[];
}

export interface MerchantOpsResponse {
  merchant_id: string;
  merchant_name: string;
  status: MerchantStatus;
}

export interface OnboardingCaseResponse {
  case_id: string;
  merchant_id: string;
  status: OnboardingCaseStatus;
  domain_or_app_name: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  decision_note: string | null;
}

export interface CredentialOpsResponse {
  credential_id: string;
  merchant_id: string;
  access_key: string;
  secret_key_last4: string;
  status: CredentialStatus;
  expired_at: string | null;
  rotated_at: string | null;
}

export type QrAccountOpsResponse = MerchantQrAccount & {
  merchant_id: string;
};

export interface WebhookRetryResponse {
  event_id: string;
  status: WebhookEventStatus;
  attempt_count: number;
  last_attempt_result: DeliveryAttemptResult | null;
  next_retry_at: string | null;
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
    if (value instanceof Date) {
      params.set(key, value.toISOString());
      continue;
    }
    params.set(key, String(value));
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

function buildActor(reason: string | null) {
  return {
    actor_type: "OPS" as const,
    actor_id: null,
    reason: reason || null,
  };
}

function buildOpsBody<T extends Record<string, unknown>>(payload: T, reason: string) {
  return {
    ...payload,
    actor: buildActor(reason),
  };
}

export async function getBootstrapStatus() {
  return apiFetch<BootstrapStatusResponse>("/v1/internal/auth/bootstrap-status");
}

export async function bootstrapInternalAuth(payload: {
  email: string;
  full_name: string;
  password: string;
}) {
  return apiFetch<InternalAuthSessionResponse>("/v1/internal/auth/bootstrap", {
    method: "POST",
    bodyJson: payload,
  });
}

export async function loginInternalAuth(payload: {
  email: string;
  password: string;
}) {
  return apiFetch<InternalAuthSessionResponse>("/v1/internal/auth/login", {
    method: "POST",
    bodyJson: payload,
  });
}

export async function logoutInternalAuth() {
  return apiFetch<{ status: string }>("/v1/internal/auth/logout", {
    method: "POST",
  });
}

export async function getCurrentSession() {
  return apiFetch<InternalAuthSessionResponse>("/v1/internal/auth/me");
}

export async function changeInternalPassword(payload: {
  current_password: string;
  new_password: string;
}) {
  return apiFetch<InternalAuthSessionResponse>("/v1/internal/auth/change-password", {
    method: "POST",
    bodyJson: payload,
  });
}

export async function listInternalUsers() {
  return apiFetch<{ users: InternalUser[] }>("/v1/internal/users");
}

export async function createInternalUser(payload: {
  email: string;
  full_name: string;
  role: InternalUserRole;
  password: string;
  status: InternalUserStatus;
}) {
  return apiFetch<InternalUser>("/v1/internal/users", {
    method: "POST",
    bodyJson: payload,
  });
}

export async function updateInternalUser(
  userId: string,
  payload: {
    full_name?: string;
    role?: InternalUserRole;
    status?: InternalUserStatus;
  },
) {
  return apiFetch<InternalUser>(`/v1/internal/users/${userId}`, {
    method: "PATCH",
    bodyJson: payload,
  });
}

export async function resetInternalUserPassword(
  userId: string,
  payload: { new_password: string },
) {
  return apiFetch<InternalUser>(`/v1/internal/users/${userId}/reset-password`, {
    method: "POST",
    bodyJson: payload,
  });
}

export async function getDashboardSummary() {
  return apiFetch<DashboardSummary>("/v1/ops/dashboard/summary");
}

export async function getDashboardCharts() {
  return apiFetch<DashboardCharts>("/v1/ops/dashboard/charts");
}

export async function listMerchants(filters: {
  search?: string;
  status?: MerchantStatus | "";
  onboarding_status?: OnboardingCaseStatus | "";
  limit?: number;
}) {
  return apiFetch<{ merchants: MerchantListItem[] }>(
    `/v1/ops/merchants${toQueryString(filters)}`,
  );
}

export async function getMerchantDetail(merchantId: string) {
  return apiFetch<MerchantDetail>(`/v1/ops/merchants/${merchantId}`);
}

export async function getMerchantOnboardingCase(merchantId: string) {
  return apiFetch<OnboardingCaseDetail>(
    `/v1/ops/merchants/${merchantId}/onboarding-case`,
  );
}

export async function listMerchantCredentials(merchantId: string) {
  return apiFetch<{ credentials: MerchantCredential[] }>(
    `/v1/ops/merchants/${merchantId}/credentials`,
  );
}

export async function createQrAccount(
  merchantId: string,
  payload: {
    reason: string;
    provider?: QrProvider;
    bank_code: string;
    bank_bin: string;
    account_number: string;
    account_name: string;
    template: string;
    status: MerchantQrAccountStatus;
  },
) {
  const { reason, ...rest } = payload;
  return apiFetch<QrAccountOpsResponse>(
    `/v1/ops/merchants/${merchantId}/qr-accounts`,
    {
      method: "POST",
      bodyJson: buildOpsBody(rest, reason),
    },
  );
}

export async function updateQrAccount(
  merchantId: string,
  qrAccountId: string,
  payload: {
    reason: string;
    bank_code?: string;
    bank_bin?: string;
    account_number?: string;
    account_name?: string;
    template?: string;
  },
) {
  const { reason, ...rest } = payload;
  return apiFetch<QrAccountOpsResponse>(
    `/v1/ops/merchants/${merchantId}/qr-accounts/${qrAccountId}`,
    {
      method: "PATCH",
      bodyJson: buildOpsBody(rest, reason),
    },
  );
}

export async function activateQrAccount(
  merchantId: string,
  qrAccountId: string,
  reason: string,
) {
  return apiFetch<QrAccountOpsResponse>(
    `/v1/ops/merchants/${merchantId}/qr-accounts/${qrAccountId}/activate`,
    {
      method: "POST",
      bodyJson: { actor: buildActor(reason) },
    },
  );
}

export async function deactivateQrAccount(
  merchantId: string,
  qrAccountId: string,
  reason: string,
) {
  return apiFetch<QrAccountOpsResponse>(
    `/v1/ops/merchants/${merchantId}/qr-accounts/${qrAccountId}/deactivate`,
    {
      method: "POST",
      bodyJson: { actor: buildActor(reason) },
    },
  );
}

export async function listMerchantPortalUsers(merchantId: string) {
  return apiFetch<{ users: MerchantPortalUser[] }>(
    `/v1/ops/merchants/${merchantId}/portal-users`,
  );
}

export async function createMerchantPortalUser(
  merchantId: string,
  payload: {
    email: string;
    full_name: string;
    role: MerchantUserRole;
    status: MerchantUserStatus;
  },
) {
  return apiFetch<MerchantPortalGeneratedPasswordResponse>(
    `/v1/ops/merchants/${merchantId}/portal-users`,
    {
      method: "POST",
      bodyJson: payload,
    },
  );
}

export async function updateMerchantPortalUser(
  merchantId: string,
  userId: string,
  payload: {
    full_name?: string;
    role?: MerchantUserRole;
    status?: MerchantUserStatus;
  },
) {
  return apiFetch<MerchantPortalUser>(
    `/v1/ops/merchants/${merchantId}/portal-users/${userId}`,
    {
      method: "PATCH",
      bodyJson: payload,
    },
  );
}

export async function resetMerchantPortalUserPassword(
  merchantId: string,
  userId: string,
) {
  return apiFetch<MerchantPortalGeneratedPasswordResponse>(
    `/v1/ops/merchants/${merchantId}/portal-users/${userId}/reset-password`,
    {
      method: "POST",
    },
  );
}

export async function createMerchant(payload: {
  reason: string;
  merchant_id: string;
  merchant_name: string;
  legal_name?: string;
  contact_name?: string;
  contact_email: string;
  contact_phone?: string;
  webhook_url?: string;
  settlement_account_name?: string;
  settlement_account_number?: string;
  settlement_bank_code?: string;
}) {
  const { reason, ...rest } = payload;
  return apiFetch<MerchantOpsResponse>("/v1/ops/merchants", {
    method: "POST",
    bodyJson: buildOpsBody(rest, reason),
  });
}

export async function submitOnboardingCase(
  merchantId: string,
  payload: {
    reason: string;
    domain_or_app_name?: string;
    submitted_profile_json: JsonObject;
    documents_json: JsonObject;
    review_checks_json: JsonObject;
  },
) {
  const { reason, ...rest } = payload;
  return apiFetch<OnboardingCaseResponse>(
    `/v1/ops/merchants/${merchantId}/onboarding-case`,
    {
      method: "PUT",
      bodyJson: buildOpsBody(rest, reason),
    },
  );
}

export async function approveOnboardingCase(
  merchantId: string,
  payload: { reason: string; decision_note: string },
) {
  return apiFetch<OnboardingCaseResponse>(
    `/v1/ops/merchants/${merchantId}/onboarding-case/approve`,
    {
      method: "POST",
      bodyJson: buildOpsBody(
        { reviewed_by: null, decision_note: payload.decision_note },
        payload.reason,
      ),
    },
  );
}

export async function rejectOnboardingCase(
  merchantId: string,
  payload: { reason: string; decision_note: string },
) {
  return apiFetch<OnboardingCaseResponse>(
    `/v1/ops/merchants/${merchantId}/onboarding-case/reject`,
    {
      method: "POST",
      bodyJson: buildOpsBody(
        { reviewed_by: null, decision_note: payload.decision_note },
        payload.reason,
      ),
    },
  );
}

export async function createCredential(
  merchantId: string,
  payload: { reason: string; access_key: string; secret_key: string },
) {
  const { reason, ...rest } = payload;
  return apiFetch<CredentialOpsResponse>(
    `/v1/ops/merchants/${merchantId}/credentials`,
    {
      method: "POST",
      bodyJson: buildOpsBody(rest, reason),
    },
  );
}

export async function rotateCredential(
  merchantId: string,
  payload: { reason: string; access_key: string; secret_key: string },
) {
  const { reason, ...rest } = payload;
  return apiFetch<CredentialOpsResponse>(
    `/v1/ops/merchants/${merchantId}/credentials/rotate`,
    {
      method: "POST",
      bodyJson: buildOpsBody(rest, reason),
    },
  );
}

export async function activateMerchant(merchantId: string, reason: string) {
  return apiFetch<MerchantOpsResponse>(`/v1/ops/merchants/${merchantId}/activate`, {
    method: "POST",
    bodyJson: { actor: buildActor(reason) },
  });
}

export async function suspendMerchant(merchantId: string, reason: string) {
  return apiFetch<MerchantOpsResponse>(`/v1/ops/merchants/${merchantId}/suspend`, {
    method: "POST",
    bodyJson: { actor: buildActor(reason) },
  });
}

export async function disableMerchant(merchantId: string, reason: string) {
  return apiFetch<MerchantOpsResponse>(`/v1/ops/merchants/${merchantId}/disable`, {
    method: "POST",
    bodyJson: { actor: buildActor(reason) },
  });
}

export async function listPayments(filters: {
  transaction_id?: string;
  order_id?: string;
  merchant_id?: string;
  status?: PaymentStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ payments: PaymentListItem[] }>(
    `/v1/ops/payments${toQueryString(filters)}`,
  );
}

export async function getPaymentDetail(transactionId: string) {
  return apiFetch<PaymentDetail>(`/v1/ops/payments/${transactionId}`);
}

export async function listRefunds(filters: {
  refund_transaction_id?: string;
  refund_id?: string;
  merchant_id?: string;
  status?: RefundStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ refunds: RefundListItem[] }>(
    `/v1/ops/refunds${toQueryString(filters)}`,
  );
}

export async function getRefundDetail(refundTransactionId: string) {
  return apiFetch<RefundDetail>(`/v1/ops/refunds/${refundTransactionId}`);
}

export async function listWebhooks(filters: {
  event_type?: string;
  status?: WebhookEventStatus | "";
  merchant_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ events: WebhookEventListItem[] }>(
    `/v1/ops/webhooks${toQueryString(filters)}`,
  );
}

export async function getWebhookDetail(eventId: string) {
  return apiFetch<WebhookEventDetail>(`/v1/ops/webhooks/${eventId}`);
}

export async function listWebhookAttempts(eventId: string) {
  return apiFetch<{ attempts: WebhookAttempt[] }>(
    `/v1/ops/webhooks/${eventId}/attempts`,
  );
}

export async function retryWebhook(eventId: string, reason: string) {
  return apiFetch<WebhookRetryResponse>(`/v1/ops/webhooks/${eventId}/retry`, {
    method: "POST",
    bodyJson: buildActor(reason),
  });
}

export async function listReconciliationRecords(filters: {
  match_result?: ReconciliationStatus | "";
  entity_type?: EntityType | "";
  entity_id?: string;
  limit?: number;
}) {
  return apiFetch<{ records: ReconciliationRecord[] }>(
    `/v1/ops/reconciliation${toQueryString(filters)}`,
  );
}

export async function getReconciliationRecord(recordId: string) {
  return apiFetch<ReconciliationRecord>(`/v1/ops/reconciliation/${recordId}`);
}

export async function resolveReconciliationRecord(
  recordId: string,
  payload: { reason: string; review_note: string },
) {
  return apiFetch<ReconciliationRecord>(
    `/v1/ops/reconciliation/${recordId}/resolve`,
    {
      method: "POST",
      bodyJson: buildOpsBody(
        { reviewed_by: null, review_note: payload.review_note },
        payload.reason,
      ),
    },
  );
}

export async function listAuditLogs(filters: {
  actor_type?: ActorType | "";
  actor_id?: string;
  entity_type?: EntityType | "";
  entity_id?: string;
  event_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<{ logs: AuditLogItem[] }>(
    `/v1/ops/audit-logs${toQueryString(filters)}`,
  );
}
