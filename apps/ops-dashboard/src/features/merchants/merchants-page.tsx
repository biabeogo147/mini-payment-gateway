import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateMerchant,
  createCredential,
  createMerchant,
  disableMerchant,
  getMerchantDetail,
  listMerchants,
  rotateCredential,
  suspendMerchant,
  type CredentialOpsResponse,
  type MerchantStatus,
} from "../common/api";
import { formatDateTime } from "../common/format";
import { invalidateOpsConsoleData } from "../common/query";
import {
  ContentCard,
  DetailGrid,
  EmptyState,
  ErrorCard,
  InlineField,
  JsonBlock,
  PageHeader,
  StatusBadge,
} from "../common/ui";
import { useSession } from "../auth/use-session";

const merchantStatusOptions: Array<MerchantStatus | ""> = [
  "",
  "PENDING_REVIEW",
  "ACTIVE",
  "REJECTED",
  "SUSPENDED",
  "DISABLED",
];

export function MerchantsPage() {
  const queryClient = useQueryClient();
  const { data: session } = useSession();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<MerchantStatus | "">("");
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>("");
  const [createForm, setCreateForm] = useState({
    reason: "Create merchant from ops dashboard.",
    merchant_id: "",
    merchant_name: "",
    legal_name: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    webhook_url: "",
    settlement_account_name: "",
    settlement_account_number: "",
    settlement_bank_code: "",
  });
  const [actionReason, setActionReason] = useState("Lifecycle update from ops dashboard.");
  const [credentialForm, setCredentialForm] = useState({
    reason: "Issue merchant credential from ops dashboard.",
    access_key: "",
    secret_key: "",
  });
  const [rotationForm, setRotationForm] = useState({
    reason: "Rotate credential from ops dashboard.",
    access_key: "",
    secret_key: "",
  });

  const merchantListQuery = useQuery({
    queryKey: ["merchants", search, status],
    queryFn: () =>
      listMerchants({
        search: search || undefined,
        status,
        limit: 100,
      }),
  });

  const merchantDetailQuery = useQuery({
    queryKey: ["merchant-detail", selectedMerchantId],
    queryFn: () => getMerchantDetail(selectedMerchantId),
    enabled: Boolean(selectedMerchantId),
  });

  useEffect(() => {
    const firstMerchantId = merchantListQuery.data?.merchants[0]?.merchant_id;
    if (!selectedMerchantId && firstMerchantId) {
      setSelectedMerchantId(firstMerchantId);
    }
  }, [merchantListQuery.data, selectedMerchantId]);

  const createMerchantMutation = useMutation({
    mutationFn: createMerchant,
    onSuccess: async (payload) => {
      await invalidateOpsConsoleData(queryClient);
      setSelectedMerchantId(payload.merchant_id);
      setCreateForm({
        reason: "Create merchant from ops dashboard.",
        merchant_id: "",
        merchant_name: "",
        legal_name: "",
        contact_name: "",
        contact_email: "",
        contact_phone: "",
        webhook_url: "",
        settlement_account_name: "",
        settlement_account_number: "",
        settlement_bank_code: "",
      });
    },
  });

  const createCredentialMutation = useMutation({
    mutationFn: (merchantId: string) => createCredential(merchantId, credentialForm),
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setCredentialForm({
        reason: "Issue merchant credential from ops dashboard.",
        access_key: "",
        secret_key: "",
      });
    },
  });

  const rotateCredentialMutation = useMutation({
    mutationFn: (merchantId: string) => rotateCredential(merchantId, rotationForm),
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setRotationForm({
        reason: "Rotate credential from ops dashboard.",
        access_key: "",
        secret_key: "",
      });
    },
  });

  const activateMutation = useMutation({
    mutationFn: (merchantId: string) => activateMerchant(merchantId, actionReason),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });
  const suspendMutation = useMutation({
    mutationFn: (merchantId: string) => suspendMerchant(merchantId, actionReason),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });
  const disableMutation = useMutation({
    mutationFn: (merchantId: string) => disableMerchant(merchantId, actionReason),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });

  if (merchantListQuery.error instanceof Error) {
    return <ErrorCard message={merchantListQuery.error.message} />;
  }

  const merchants = merchantListQuery.data?.merchants ?? [];
  const merchantDetail = merchantDetailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Merchant workspace"
        title="Merchants"
        description="Review merchant profiles, inspect current readiness, and execute lifecycle plus credential actions."
      />

      <ContentCard title="Create merchant profile">
        <div className="form-grid form-grid-wide">
          <InlineField label="Reason">
            <input
              value={createForm.reason}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, reason: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Merchant id">
            <input
              value={createForm.merchant_id}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, merchant_id: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Merchant name">
            <input
              value={createForm.merchant_name}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, merchant_name: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Legal name">
            <input
              value={createForm.legal_name}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, legal_name: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Contact name">
            <input
              value={createForm.contact_name}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, contact_name: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Contact email">
            <input
              value={createForm.contact_email}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, contact_email: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Contact phone">
            <input
              value={createForm.contact_phone}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, contact_phone: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Webhook URL">
            <input
              value={createForm.webhook_url}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, webhook_url: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Settlement account name">
            <input
              value={createForm.settlement_account_name}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  settlement_account_name: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Settlement account number">
            <input
              value={createForm.settlement_account_number}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  settlement_account_number: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Settlement bank code">
            <input
              value={createForm.settlement_bank_code}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  settlement_bank_code: event.target.value,
                }))
              }
            />
          </InlineField>
        </div>
        <div className="inline-actions">
          <button
            type="button"
            className="primary-button"
            disabled={
              createMerchantMutation.isPending ||
              !createForm.reason ||
              !createForm.merchant_id ||
              !createForm.merchant_name ||
              !createForm.contact_email
            }
            onClick={() => createMerchantMutation.mutate(createForm)}
          >
            {createMerchantMutation.isPending ? "Creating..." : "Create merchant"}
          </button>
          {createMerchantMutation.error instanceof Error ? (
            <span className="feedback feedback-danger">
              {createMerchantMutation.error.message}
            </span>
          ) : null}
        </div>
      </ContentCard>

      <div className="panel-grid panel-grid-wide">
        <ContentCard title="Merchant list">
          <div className="filter-row">
            <InlineField label="Search">
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="merchant id, name, email"
              />
            </InlineField>
            <InlineField label="Status">
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as MerchantStatus | "")}
              >
                {merchantStatusOptions.map((option) => (
                  <option key={option || "ALL"} value={option}>
                    {option || "ALL"}
                  </option>
                ))}
              </select>
            </InlineField>
          </div>

          {merchants.length === 0 ? (
            <EmptyState
              title="No merchants found"
              message="Adjust the current filters or create a new merchant profile above."
            />
          ) : (
            <div className="stack-list">
              {merchants.map((merchant) => (
                <button
                  type="button"
                  key={merchant.merchant_id}
                  className={
                    selectedMerchantId === merchant.merchant_id
                      ? "table-row-button table-row-button-active"
                      : "table-row-button"
                  }
                  onClick={() => setSelectedMerchantId(merchant.merchant_id)}
                >
                  <div>
                    <strong>{merchant.merchant_name}</strong>
                    <p>
                      {merchant.merchant_id} · {merchant.contact_email}
                    </p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={merchant.status} />
                    {merchant.onboarding_status ? (
                      <StatusBadge value={merchant.onboarding_status} />
                    ) : null}
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Merchant detail">
          {!selectedMerchantId ? (
            <EmptyState
              title="Pick a merchant"
              message="Select a merchant from the list to inspect detail and actions."
            />
          ) : merchantDetailQuery.isLoading ? (
            <EmptyState
              title="Loading merchant detail"
              message="Fetching profile, readiness, recent activity, and credentials."
            />
          ) : merchantDetailQuery.error instanceof Error ? (
            <ErrorCard message={merchantDetailQuery.error.message} />
          ) : merchantDetail ? (
            <div className="page-stack">
              <DetailGrid
                items={[
                  { label: "Merchant id", value: merchantDetail.merchant_id },
                  { label: "Status", value: <StatusBadge value={merchantDetail.status} /> },
                  {
                    label: "Onboarding",
                    value: merchantDetail.onboarding_case ? (
                      <StatusBadge value={merchantDetail.onboarding_case.status} />
                    ) : (
                      "Not submitted"
                    ),
                  },
                  { label: "Webhook URL", value: merchantDetail.webhook_url ?? "N/A" },
                  { label: "Contact", value: merchantDetail.contact_email },
                  { label: "Updated", value: formatDateTime(merchantDetail.updated_at) },
                ]}
              />

              <div className="form-grid">
                <InlineField label="Action reason">
                  <input
                    value={actionReason}
                    onChange={(event) => setActionReason(event.target.value)}
                  />
                </InlineField>
              </div>
              <div className="inline-actions">
                <button
                  type="button"
                  className="primary-button"
                  disabled={activateMutation.isPending || !actionReason}
                  onClick={() => activateMutation.mutate(merchantDetail.merchant_id)}
                >
                  Activate
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={suspendMutation.isPending || !actionReason}
                  onClick={() => suspendMutation.mutate(merchantDetail.merchant_id)}
                >
                  Suspend
                </button>
                {session?.user.role === "ADMIN" ? (
                  <button
                    type="button"
                    className="danger-button"
                    disabled={disableMutation.isPending || !actionReason}
                    onClick={() => disableMutation.mutate(merchantDetail.merchant_id)}
                  >
                    Disable
                  </button>
                ) : null}
              </div>

              <div className="panel-grid">
                <ContentCard title="Credentials">
                  {merchantDetail.credentials.length === 0 ? (
                    <EmptyState
                      title="No credentials yet"
                      message="Issue the first credential after onboarding approval."
                    />
                  ) : (
                    <div className="stack-list">
                      {merchantDetail.credentials.map((credential) => (
                        <article key={credential.credential_id} className="stack-row">
                          <div>
                            <strong>{credential.access_key}</strong>
                            <p>••••{credential.secret_key_last4}</p>
                          </div>
                          <div className="stack-row-meta">
                            <StatusBadge value={credential.status} />
                            <span>{formatDateTime(credential.created_at)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>

                <ContentCard title="Onboarding case">
                  {merchantDetail.onboarding_case ? (
                    <div className="page-stack">
                      <DetailGrid
                        items={[
                          {
                            label: "Case status",
                            value: <StatusBadge value={merchantDetail.onboarding_case.status} />,
                          },
                          {
                            label: "Domain or app",
                            value: merchantDetail.onboarding_case.domain_or_app_name ?? "N/A",
                          },
                          {
                            label: "Reviewed at",
                            value: formatDateTime(merchantDetail.onboarding_case.reviewed_at),
                          },
                        ]}
                      />
                      <JsonBlock value={merchantDetail.onboarding_case.review_checks_json} />
                    </div>
                  ) : (
                    <EmptyState
                      title="No onboarding case"
                      message="Use the onboarding page to submit merchant readiness for review."
                    />
                  )}
                </ContentCard>
              </div>

              <div className="panel-grid">
                <ContentCard title="Issue credential">
                  <div className="form-grid">
                    <InlineField label="Reason">
                      <input
                        value={credentialForm.reason}
                        onChange={(event) =>
                          setCredentialForm((current) => ({
                            ...current,
                            reason: event.target.value,
                          }))
                        }
                      />
                    </InlineField>
                    <InlineField label="Access key">
                      <input
                        value={credentialForm.access_key}
                        onChange={(event) =>
                          setCredentialForm((current) => ({
                            ...current,
                            access_key: event.target.value,
                          }))
                        }
                      />
                    </InlineField>
                    <InlineField label="Secret key">
                      <input
                        value={credentialForm.secret_key}
                        onChange={(event) =>
                          setCredentialForm((current) => ({
                            ...current,
                            secret_key: event.target.value,
                          }))
                        }
                      />
                    </InlineField>
                  </div>
                  <div className="inline-actions">
                    <button
                      type="button"
                      className="primary-button"
                      disabled={
                        createCredentialMutation.isPending ||
                        !credentialForm.reason ||
                        !credentialForm.access_key ||
                        !credentialForm.secret_key
                      }
                      onClick={() => createCredentialMutation.mutate(merchantDetail.merchant_id)}
                    >
                      {createCredentialMutation.isPending
                        ? "Issuing..."
                        : "Create credential"}
                    </button>
                    {createCredentialMutation.error instanceof Error ? (
                      <span className="feedback feedback-danger">
                        {createCredentialMutation.error.message}
                      </span>
                    ) : null}
                  </div>
                </ContentCard>

                {session?.user.role === "ADMIN" ? (
                  <ContentCard title="Rotate credential">
                    <div className="form-grid">
                      <InlineField label="Reason">
                        <input
                          value={rotationForm.reason}
                          onChange={(event) =>
                            setRotationForm((current) => ({
                              ...current,
                              reason: event.target.value,
                            }))
                          }
                        />
                      </InlineField>
                      <InlineField label="New access key">
                        <input
                          value={rotationForm.access_key}
                          onChange={(event) =>
                            setRotationForm((current) => ({
                              ...current,
                              access_key: event.target.value,
                            }))
                          }
                        />
                      </InlineField>
                      <InlineField label="New secret key">
                        <input
                          value={rotationForm.secret_key}
                          onChange={(event) =>
                            setRotationForm((current) => ({
                              ...current,
                              secret_key: event.target.value,
                            }))
                          }
                        />
                      </InlineField>
                    </div>
                    <div className="inline-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={
                          rotateCredentialMutation.isPending ||
                          !rotationForm.reason ||
                          !rotationForm.access_key ||
                          !rotationForm.secret_key
                        }
                        onClick={() => rotateCredentialMutation.mutate(merchantDetail.merchant_id)}
                      >
                        {rotateCredentialMutation.isPending
                          ? "Rotating..."
                          : "Rotate credential"}
                      </button>
                      {rotateCredentialMutation.error instanceof Error ? (
                        <span className="feedback feedback-danger">
                          {rotateCredentialMutation.error.message}
                        </span>
                      ) : null}
                    </div>
                  </ContentCard>
                ) : null}
              </div>

              <div className="panel-grid">
                <ContentCard title="Recent payments">
                  {merchantDetail.recent_payments.length === 0 ? (
                    <EmptyState title="No payments yet" message="No recent payments on file." />
                  ) : (
                    <div className="stack-list">
                      {merchantDetail.recent_payments.map((payment) => (
                        <article key={payment.transaction_id} className="stack-row">
                          <div>
                            <strong>{payment.transaction_id}</strong>
                            <p>{payment.order_id}</p>
                          </div>
                          <div className="stack-row-meta">
                            <StatusBadge value={payment.status} />
                            <span>{formatDateTime(payment.created_at)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>

                <ContentCard title="Recent audit">
                  {merchantDetail.recent_audit_logs.length === 0 ? (
                    <EmptyState title="No audit rows" message="No audit history for this merchant yet." />
                  ) : (
                    <div className="stack-list">
                      {merchantDetail.recent_audit_logs.map((item) => (
                        <article key={item.log_id} className="stack-row">
                          <div>
                            <strong>{item.event_type}</strong>
                            <p>{item.reason ?? "No reason captured"}</p>
                          </div>
                          <div className="stack-row-meta">
                            <StatusBadge value={item.actor_type} />
                            <span>{formatDateTime(item.created_at)}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </ContentCard>
              </div>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
