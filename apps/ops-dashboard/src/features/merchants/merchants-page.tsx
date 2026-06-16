import { type ReactNode, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateQrAccount,
  activateMerchant,
  createQrAccount,
  createMerchantPortalUser,
  createCredential,
  createMerchant,
  deactivateQrAccount,
  disableMerchant,
  getMerchantDetail,
  listMerchants,
  listMerchantPortalUsers,
  resetMerchantPortalUserPassword,
  rotateCredential,
  suspendMerchant,
  updateQrAccount,
  updateMerchantPortalUser,
  type MerchantQrAccount,
  type MerchantQrAccountStatus,
  type MerchantUserRole,
  type MerchantUserStatus,
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

function MerchantSection(props: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={props.className ? `section-panel ${props.className}` : "section-panel"}>
      <div className="card-title-row">
        <h4>{props.title}</h4>
      </div>
      {props.children}
    </section>
  );
}

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
  const [portalUserForm, setPortalUserForm] = useState({
    email: "",
    full_name: "",
    role: "MERCHANT_ADMIN" as MerchantUserRole,
    status: "ACTIVE" as MerchantUserStatus,
  });
  const [generatedPortalPassword, setGeneratedPortalPassword] = useState("");
  const [qrAccountForm, setQrAccountForm] = useState({
    reason: "Configure VietQR receiving account from ops dashboard.",
    bank_code: "",
    bank_bin: "",
    account_number: "",
    account_name: "",
    template: "compact",
    status: "ACTIVE" as MerchantQrAccountStatus,
  });
  const [selectedQrAccountId, setSelectedQrAccountId] = useState("");
  const [qrAccountUpdateForm, setQrAccountUpdateForm] = useState({
    reason: "Update VietQR receiving account from ops dashboard.",
    bank_code: "",
    bank_bin: "",
    account_number: "",
    account_name: "",
    template: "compact",
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

  const portalUsersQuery = useQuery({
    queryKey: ["merchant-portal-users", selectedMerchantId],
    queryFn: () => listMerchantPortalUsers(selectedMerchantId),
    enabled: Boolean(selectedMerchantId) && session?.user.role === "ADMIN",
  });

  useEffect(() => {
    const firstMerchantId = merchantListQuery.data?.merchants[0]?.merchant_id;
    if (!selectedMerchantId && firstMerchantId) {
      setSelectedMerchantId(firstMerchantId);
    }
  }, [merchantListQuery.data, selectedMerchantId]);

  useEffect(() => {
    const qrAccounts = merchantDetailQuery.data?.qr_accounts ?? [];
    const firstQrAccount = qrAccounts[0];
    if (!firstQrAccount) {
      if (selectedQrAccountId) {
        setSelectedQrAccountId("");
      }
      return;
    }
    const selectedStillExists = qrAccounts.some(
      (account) => account.qr_account_id === selectedQrAccountId,
    );
    if (!selectedQrAccountId || !selectedStillExists) {
      loadQrAccountForEditing(firstQrAccount);
    }
  }, [merchantDetailQuery.data, selectedQrAccountId]);

  function loadQrAccountForEditing(account: MerchantQrAccount) {
    setSelectedQrAccountId(account.qr_account_id);
    setQrAccountUpdateForm({
      reason: "Update VietQR receiving account from ops dashboard.",
      bank_code: account.bank_code,
      bank_bin: account.bank_bin,
      account_number: account.account_number,
      account_name: account.account_name,
      template: account.template,
    });
  }

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

  const createQrAccountMutation = useMutation({
    mutationFn: (merchantId: string) =>
      createQrAccount(merchantId, {
        ...qrAccountForm,
        provider: "VIETQR",
      }),
    onSuccess: async (payload) => {
      await invalidateOpsConsoleData(queryClient);
      loadQrAccountForEditing(payload);
      setQrAccountForm({
        reason: "Configure VietQR receiving account from ops dashboard.",
        bank_code: "",
        bank_bin: "",
        account_number: "",
        account_name: "",
        template: "compact",
        status: "ACTIVE",
      });
    },
  });

  const updateQrAccountMutation = useMutation({
    mutationFn: (input: { merchantId: string; qrAccountId: string }) =>
      updateQrAccount(input.merchantId, input.qrAccountId, qrAccountUpdateForm),
    onSuccess: async (payload) => {
      await invalidateOpsConsoleData(queryClient);
      loadQrAccountForEditing(payload);
    },
  });

  const activateQrAccountMutation = useMutation({
    mutationFn: (input: { merchantId: string; qrAccountId: string }) =>
      activateQrAccount(input.merchantId, input.qrAccountId, actionReason),
    onSuccess: async (payload) => {
      await invalidateOpsConsoleData(queryClient);
      loadQrAccountForEditing(payload);
    },
  });

  const deactivateQrAccountMutation = useMutation({
    mutationFn: (input: { merchantId: string; qrAccountId: string }) =>
      deactivateQrAccount(input.merchantId, input.qrAccountId, actionReason),
    onSuccess: async (payload) => {
      await invalidateOpsConsoleData(queryClient);
      loadQrAccountForEditing(payload);
    },
  });

  const createPortalUserMutation = useMutation({
    mutationFn: (merchantId: string) =>
      createMerchantPortalUser(merchantId, portalUserForm),
    onSuccess: async (payload) => {
      setGeneratedPortalPassword(payload.generated_password);
      await invalidateOpsConsoleData(queryClient);
      setPortalUserForm({
        email: "",
        full_name: "",
        role: "MERCHANT_ADMIN",
        status: "ACTIVE",
      });
    },
  });

  const updatePortalUserMutation = useMutation({
    mutationFn: (input: {
      merchantId: string;
      userId: string;
      status: MerchantUserStatus;
    }) =>
      updateMerchantPortalUser(input.merchantId, input.userId, {
        status: input.status,
      }),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });

  const resetPortalPasswordMutation = useMutation({
    mutationFn: (input: { merchantId: string; userId: string }) =>
      resetMerchantPortalUserPassword(input.merchantId, input.userId),
    onSuccess: async (payload) => {
      setGeneratedPortalPassword(payload.generated_password);
      await invalidateOpsConsoleData(queryClient);
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
  const selectedQrAccount = merchantDetail?.qr_accounts.find(
    (account) => account.qr_account_id === selectedQrAccountId,
  );

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

              <div
                className={
                  session?.user.role === "ADMIN"
                    ? "merchant-access-grid"
                    : "merchant-access-grid merchant-access-grid-single"
                }
              >
                <div className="merchant-access-column">
                  <MerchantSection title="Credentials">
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
                  </MerchantSection>

                  <MerchantSection title="QR receiving accounts">
                    {merchantDetail.qr_accounts.length === 0 ? (
                      <EmptyState
                        title="No QR account configured"
                        message="Create an active VietQR receiving account before pilot payment creation."
                      />
                    ) : (
                      <div
                        className="stack-list activity-list-scroll qr-account-list"
                        role="list"
                        aria-label="QR receiving accounts"
                      >
                        {merchantDetail.qr_accounts.map((account) => (
                          <article
                            key={account.qr_account_id}
                            className="stack-row portal-user-row"
                            role="listitem"
                          >
                            <div>
                              <strong>
                                {account.bank_code} {account.account_number}
                              </strong>
                              <p>
                                {account.provider} · {account.account_name} · BIN {account.bank_bin}
                              </p>
                            </div>
                            <div className="portal-user-actions">
                              <div className="portal-user-badges">
                                <StatusBadge value={account.status} />
                                <span className="feedback">{account.template}</span>
                              </div>
                              <div className="portal-user-buttons">
                                <button
                                  type="button"
                                  className="secondary-button"
                                  onClick={() => loadQrAccountForEditing(account)}
                                >
                                  Edit
                                </button>
                                {account.status === "ACTIVE" ? (
                                  <button
                                    type="button"
                                    className="secondary-button"
                                    disabled={
                                      deactivateQrAccountMutation.isPending || !actionReason
                                    }
                                    onClick={() =>
                                      deactivateQrAccountMutation.mutate({
                                        merchantId: merchantDetail.merchant_id,
                                        qrAccountId: account.qr_account_id,
                                      })
                                    }
                                  >
                                    Deactivate
                                  </button>
                                ) : (
                                  <button
                                    type="button"
                                    className="primary-button"
                                    disabled={activateQrAccountMutation.isPending || !actionReason}
                                    onClick={() =>
                                      activateQrAccountMutation.mutate({
                                        merchantId: merchantDetail.merchant_id,
                                        qrAccountId: account.qr_account_id,
                                      })
                                    }
                                  >
                                    Activate
                                  </button>
                                )}
                              </div>
                            </div>
                          </article>
                        ))}
                      </div>
                    )}

                    <div className="qr-account-form-panel">
                      <div className="form-grid">
                        <InlineField label="Reason">
                          <input
                            value={qrAccountForm.reason}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                reason: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Bank code">
                          <input
                            value={qrAccountForm.bank_code}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                bank_code: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Bank BIN">
                          <input
                            value={qrAccountForm.bank_bin}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                bank_bin: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Account number">
                          <input
                            value={qrAccountForm.account_number}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                account_number: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Account name">
                          <input
                            value={qrAccountForm.account_name}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                account_name: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Template">
                          <input
                            value={qrAccountForm.template}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                template: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Initial status">
                          <select
                            value={qrAccountForm.status}
                            onChange={(event) =>
                              setQrAccountForm((current) => ({
                                ...current,
                                status: event.target.value as MerchantQrAccountStatus,
                              }))
                            }
                          >
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="INACTIVE">INACTIVE</option>
                          </select>
                        </InlineField>
                      </div>
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="primary-button"
                          disabled={
                            createQrAccountMutation.isPending ||
                            !qrAccountForm.reason ||
                            !qrAccountForm.bank_code ||
                            !qrAccountForm.bank_bin ||
                            !qrAccountForm.account_number ||
                            !qrAccountForm.account_name ||
                            !qrAccountForm.template
                          }
                          onClick={() =>
                            createQrAccountMutation.mutate(merchantDetail.merchant_id)
                          }
                        >
                          {createQrAccountMutation.isPending
                            ? "Creating..."
                            : "Create QR account"}
                        </button>
                        {createQrAccountMutation.error instanceof Error ? (
                          <span className="feedback feedback-danger">
                            {createQrAccountMutation.error.message}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {merchantDetail.qr_accounts.length > 0 ? (
                      <div className="qr-account-form-panel">
                        <div className="form-grid">
                          <InlineField label="QR account">
                            <select
                              value={selectedQrAccountId}
                              onChange={(event) => {
                                const next = merchantDetail.qr_accounts.find(
                                  (account) => account.qr_account_id === event.target.value,
                                );
                                if (next) {
                                  loadQrAccountForEditing(next);
                                }
                              }}
                            >
                              {merchantDetail.qr_accounts.map((account) => (
                                <option
                                  key={account.qr_account_id}
                                  value={account.qr_account_id}
                                >
                                  {account.bank_code} {account.account_number}
                                </option>
                              ))}
                            </select>
                          </InlineField>
                          <InlineField label="Reason">
                            <input
                              value={qrAccountUpdateForm.reason}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  reason: event.target.value,
                                }))
                              }
                            />
                          </InlineField>
                          <InlineField label="Bank code">
                            <input
                              value={qrAccountUpdateForm.bank_code}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  bank_code: event.target.value,
                                }))
                              }
                            />
                          </InlineField>
                          <InlineField label="Bank BIN">
                            <input
                              value={qrAccountUpdateForm.bank_bin}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  bank_bin: event.target.value,
                                }))
                              }
                            />
                          </InlineField>
                          <InlineField label="Account number">
                            <input
                              value={qrAccountUpdateForm.account_number}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  account_number: event.target.value,
                                }))
                              }
                            />
                          </InlineField>
                          <InlineField label="Account name">
                            <input
                              value={qrAccountUpdateForm.account_name}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  account_name: event.target.value,
                                }))
                              }
                            />
                          </InlineField>
                          <InlineField label="Template">
                            <input
                              value={qrAccountUpdateForm.template}
                              onChange={(event) =>
                                setQrAccountUpdateForm((current) => ({
                                  ...current,
                                  template: event.target.value,
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
                              updateQrAccountMutation.isPending ||
                              !selectedQrAccount ||
                              !qrAccountUpdateForm.reason ||
                              !qrAccountUpdateForm.bank_code ||
                              !qrAccountUpdateForm.bank_bin ||
                              !qrAccountUpdateForm.account_number ||
                              !qrAccountUpdateForm.account_name ||
                              !qrAccountUpdateForm.template
                            }
                            onClick={() => {
                              if (!selectedQrAccount) {
                                return;
                              }
                              updateQrAccountMutation.mutate({
                                merchantId: merchantDetail.merchant_id,
                                qrAccountId: selectedQrAccount.qr_account_id,
                              });
                            }}
                          >
                            {updateQrAccountMutation.isPending
                              ? "Updating..."
                              : "Update QR account"}
                          </button>
                          {updateQrAccountMutation.error instanceof Error ? (
                            <span className="feedback feedback-danger">
                              {updateQrAccountMutation.error.message}
                            </span>
                          ) : null}
                          {activateQrAccountMutation.error instanceof Error ? (
                            <span className="feedback feedback-danger">
                              {activateQrAccountMutation.error.message}
                            </span>
                          ) : null}
                          {deactivateQrAccountMutation.error instanceof Error ? (
                            <span className="feedback feedback-danger">
                              {deactivateQrAccountMutation.error.message}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </MerchantSection>

                  <MerchantSection title="Onboarding case">
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
                  </MerchantSection>
                </div>

                {session?.user.role === "ADMIN" ? (
                  <MerchantSection title="Merchant portal users" className="portal-users-panel">
                    {portalUsersQuery.isLoading ? (
                      <EmptyState
                        title="Loading portal users"
                        message="Fetching merchant dashboard access accounts."
                      />
                    ) : portalUsersQuery.error instanceof Error ? (
                      <ErrorCard message={portalUsersQuery.error.message} />
                    ) : portalUsersQuery.data?.users.length ? (
                      <div
                        className="stack-list activity-list-scroll portal-users-list"
                        role="list"
                        aria-label="Merchant portal users"
                      >
                        {portalUsersQuery.data.users.map((user) => (
                          <article
                            key={user.user_id}
                            className="stack-row portal-user-row"
                            role="listitem"
                          >
                            <div>
                              <strong>{user.full_name}</strong>
                              <p>{user.email}</p>
                            </div>
                            <div className="portal-user-actions">
                              <div className="portal-user-badges">
                                <StatusBadge value={user.role} />
                                <StatusBadge value={user.status} />
                              </div>
                              <div className="portal-user-buttons">
                                <button
                                  type="button"
                                  className="secondary-button"
                                  disabled={updatePortalUserMutation.isPending}
                                  onClick={() =>
                                    updatePortalUserMutation.mutate({
                                      merchantId: merchantDetail.merchant_id,
                                      userId: user.user_id,
                                      status:
                                        user.status === "ACTIVE"
                                          ? "INACTIVE"
                                          : "ACTIVE",
                                    })
                                  }
                                >
                                  {user.status === "ACTIVE" ? "Deactivate" : "Activate"}
                                </button>
                                <button
                                  type="button"
                                  className="secondary-button"
                                  disabled={resetPortalPasswordMutation.isPending}
                                  onClick={() =>
                                    resetPortalPasswordMutation.mutate({
                                      merchantId: merchantDetail.merchant_id,
                                      userId: user.user_id,
                                    })
                                  }
                                >
                                  Reset password
                                </button>
                              </div>
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <EmptyState
                        title="No portal users"
                        message="Create a merchant dashboard user when the merchant is ready for read-only access."
                      />
                    )}

                    <div className="portal-user-create-panel">
                      <div className="form-grid">
                        <InlineField label="Email">
                          <input
                            value={portalUserForm.email}
                            onChange={(event) =>
                              setPortalUserForm((current) => ({
                                ...current,
                                email: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Full name">
                          <input
                            value={portalUserForm.full_name}
                            onChange={(event) =>
                              setPortalUserForm((current) => ({
                                ...current,
                                full_name: event.target.value,
                              }))
                            }
                          />
                        </InlineField>
                        <InlineField label="Role">
                          <select
                            value={portalUserForm.role}
                            onChange={(event) =>
                              setPortalUserForm((current) => ({
                                ...current,
                                role: event.target.value as MerchantUserRole,
                              }))
                            }
                          >
                            <option value="MERCHANT_ADMIN">MERCHANT_ADMIN</option>
                            <option value="MERCHANT_VIEWER">MERCHANT_VIEWER</option>
                          </select>
                        </InlineField>
                        <InlineField label="Status">
                          <select
                            value={portalUserForm.status}
                            onChange={(event) =>
                              setPortalUserForm((current) => ({
                                ...current,
                                status: event.target.value as MerchantUserStatus,
                              }))
                            }
                          >
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="INACTIVE">INACTIVE</option>
                          </select>
                        </InlineField>
                      </div>
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="primary-button"
                          disabled={
                            createPortalUserMutation.isPending ||
                            !portalUserForm.email ||
                            !portalUserForm.full_name
                          }
                          onClick={() =>
                            createPortalUserMutation.mutate(merchantDetail.merchant_id)
                          }
                        >
                          {createPortalUserMutation.isPending
                            ? "Creating..."
                            : "Create portal user"}
                        </button>
                        {generatedPortalPassword ? (
                          <span className="feedback">
                            Temporary password: {generatedPortalPassword}
                          </span>
                        ) : null}
                        {createPortalUserMutation.error instanceof Error ? (
                          <span className="feedback feedback-danger">
                            {createPortalUserMutation.error.message}
                          </span>
                        ) : null}
                        {updatePortalUserMutation.error instanceof Error ? (
                          <span className="feedback feedback-danger">
                            {updatePortalUserMutation.error.message}
                          </span>
                        ) : null}
                        {resetPortalPasswordMutation.error instanceof Error ? (
                          <span className="feedback feedback-danger">
                            {resetPortalPasswordMutation.error.message}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </MerchantSection>
                ) : null}
              </div>

              <div className="panel-grid">
                <MerchantSection title="Issue credential">
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
                </MerchantSection>

                {session?.user.role === "ADMIN" ? (
                  <MerchantSection title="Rotate credential">
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
                  </MerchantSection>
                ) : null}
              </div>

              <div className="panel-grid">
                <MerchantSection title="Recent payments" className="activity-section">
                  {merchantDetail.recent_payments.length === 0 ? (
                    <EmptyState title="No payments yet" message="No recent payments on file." />
                  ) : (
                    <div
                      className="stack-list activity-list-scroll recent-payments-list"
                      role="list"
                      aria-label="Recent payments"
                    >
                      {merchantDetail.recent_payments.map((payment) => (
                        <article
                          key={payment.transaction_id}
                          className="stack-row"
                          role="listitem"
                        >
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
                </MerchantSection>

                <MerchantSection title="Recent audit" className="activity-section">
                  {merchantDetail.recent_audit_logs.length === 0 ? (
                    <EmptyState title="No audit rows" message="No audit history for this merchant yet." />
                  ) : (
                    <div
                      className="stack-list activity-list-scroll recent-audit-list"
                      role="list"
                      aria-label="Recent audit rows"
                    >
                      {merchantDetail.recent_audit_logs.map((item) => (
                        <article key={item.log_id} className="stack-row" role="listitem">
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
                </MerchantSection>
              </div>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
