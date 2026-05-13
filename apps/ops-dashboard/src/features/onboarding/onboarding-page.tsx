import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveOnboardingCase,
  getMerchantDetail,
  listMerchants,
  rejectOnboardingCase,
  submitOnboardingCase,
} from "../common/api";
import { formatDateTime } from "../common/format";
import { invalidateOpsConsoleData } from "../common/query";
import {
  ContentCard,
  EmptyState,
  ErrorCard,
  InlineField,
  JsonBlock,
  PageHeader,
  StatusBadge,
} from "../common/ui";

function safeParseJson(value: string) {
  return value.trim() ? (JSON.parse(value) as Record<string, unknown>) : {};
}

export function OnboardingPage() {
  const queryClient = useQueryClient();
  const [selectedMerchantId, setSelectedMerchantId] = useState("");
  const [submitForm, setSubmitForm] = useState({
    reason: "Submit onboarding case from ops dashboard.",
    domain_or_app_name: "",
    submitted_profile_json: "{\n  \"business_type\": \"retail\"\n}",
    documents_json: "{\n  \"business_license\": \"license.pdf\"\n}",
    review_checks_json: "{\n  \"risk_level\": \"LOW\"\n}",
  });
  const [decisionReason, setDecisionReason] = useState("Onboarding review from ops dashboard.");
  const [decisionNote, setDecisionNote] = useState("");

  const queueQuery = useQuery({
    queryKey: ["merchants", "onboarding-queue"],
    queryFn: () =>
      listMerchants({
        onboarding_status: "PENDING_REVIEW",
        limit: 100,
      }),
  });

  const merchantDetailQuery = useQuery({
    queryKey: ["merchant-detail", selectedMerchantId, "onboarding"],
    queryFn: () => getMerchantDetail(selectedMerchantId),
    enabled: Boolean(selectedMerchantId),
  });

  useEffect(() => {
    const firstMerchantId = queueQuery.data?.merchants[0]?.merchant_id;
    if (!selectedMerchantId && firstMerchantId) {
      setSelectedMerchantId(firstMerchantId);
    }
  }, [queueQuery.data, selectedMerchantId]);

  const submitMutation = useMutation({
    mutationFn: (merchantId: string) =>
      submitOnboardingCase(merchantId, {
        reason: submitForm.reason,
        domain_or_app_name: submitForm.domain_or_app_name,
        submitted_profile_json: safeParseJson(submitForm.submitted_profile_json),
        documents_json: safeParseJson(submitForm.documents_json),
        review_checks_json: safeParseJson(submitForm.review_checks_json),
      }),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });

  const approveMutation = useMutation({
    mutationFn: (merchantId: string) =>
      approveOnboardingCase(merchantId, {
        reason: decisionReason,
        decision_note: decisionNote,
      }),
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setDecisionNote("");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (merchantId: string) =>
      rejectOnboardingCase(merchantId, {
        reason: decisionReason,
        decision_note: decisionNote,
      }),
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setDecisionNote("");
    },
  });

  if (queueQuery.error instanceof Error) {
    return <ErrorCard message={queueQuery.error.message} />;
  }

  const queue = queueQuery.data?.merchants ?? [];
  const merchantDetail = merchantDetailQuery.data;

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Review queue"
        title="Onboarding"
        description="Submit merchant readiness, inspect pending queue items, and make approval or rejection decisions with auditable notes."
      />

      <ContentCard title="Submit or refresh onboarding case">
        <div className="form-grid form-grid-wide">
          <InlineField label="Merchant id">
            <input
              value={selectedMerchantId}
              onChange={(event) => setSelectedMerchantId(event.target.value)}
              placeholder="m_demo"
            />
          </InlineField>
          <InlineField label="Reason">
            <input
              value={submitForm.reason}
              onChange={(event) =>
                setSubmitForm((current) => ({ ...current, reason: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Domain or app">
            <input
              value={submitForm.domain_or_app_name}
              onChange={(event) =>
                setSubmitForm((current) => ({
                  ...current,
                  domain_or_app_name: event.target.value,
                }))
              }
            />
          </InlineField>
          <label className="field field-span-two">
            <span>Submitted profile JSON</span>
            <textarea
              value={submitForm.submitted_profile_json}
              onChange={(event) =>
                setSubmitForm((current) => ({
                  ...current,
                  submitted_profile_json: event.target.value,
                }))
              }
              rows={8}
            />
          </label>
          <label className="field field-span-two">
            <span>Documents JSON</span>
            <textarea
              value={submitForm.documents_json}
              onChange={(event) =>
                setSubmitForm((current) => ({
                  ...current,
                  documents_json: event.target.value,
                }))
              }
              rows={8}
            />
          </label>
          <label className="field field-span-two">
            <span>Review checks JSON</span>
            <textarea
              value={submitForm.review_checks_json}
              onChange={(event) =>
                setSubmitForm((current) => ({
                  ...current,
                  review_checks_json: event.target.value,
                }))
              }
              rows={8}
            />
          </label>
        </div>
        <div className="inline-actions">
          <button
            type="button"
            className="primary-button"
            disabled={submitMutation.isPending || !selectedMerchantId || !submitForm.reason}
            onClick={() => submitMutation.mutate(selectedMerchantId)}
          >
            {submitMutation.isPending ? "Submitting..." : "Submit onboarding case"}
          </button>
          {submitMutation.error instanceof Error ? (
            <span className="feedback feedback-danger">
              {submitMutation.error.message}
            </span>
          ) : null}
        </div>
      </ContentCard>

      <div className="panel-grid panel-grid-wide">
        <ContentCard title="Pending queue">
          {queue.length === 0 ? (
            <EmptyState
              title="Queue is empty"
              message="No onboarding cases are currently waiting for review."
            />
          ) : (
            <div className="stack-list">
              {queue.map((merchant) => (
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
                    <p>{merchant.merchant_id}</p>
                  </div>
                  <div className="stack-row-meta">
                    {merchant.onboarding_status ? (
                      <StatusBadge value={merchant.onboarding_status} />
                    ) : null}
                    <span>{formatDateTime(merchant.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ContentCard>

        <ContentCard title="Case review detail">
          {!selectedMerchantId ? (
            <EmptyState
              title="Select a merchant"
              message="Choose a merchant from the queue or enter one above."
            />
          ) : merchantDetailQuery.isLoading ? (
            <EmptyState
              title="Loading case detail"
              message="Fetching submitted documents, review checks, and current status."
            />
          ) : merchantDetailQuery.error instanceof Error ? (
            <ErrorCard message={merchantDetailQuery.error.message} />
          ) : merchantDetail ? (
            <div className="page-stack">
              <div className="detail-grid">
                <div className="detail-item">
                  <span>Merchant</span>
                  <strong>{merchantDetail.merchant_name}</strong>
                </div>
                <div className="detail-item">
                  <span>Contact</span>
                  <strong>{merchantDetail.contact_email}</strong>
                </div>
                <div className="detail-item">
                  <span>Merchant status</span>
                  <strong>
                    <StatusBadge value={merchantDetail.status} />
                  </strong>
                </div>
                <div className="detail-item">
                  <span>Onboarding status</span>
                  <strong>
                    {merchantDetail.onboarding_case ? (
                      <StatusBadge value={merchantDetail.onboarding_case.status} />
                    ) : (
                      "No case"
                    )}
                  </strong>
                </div>
              </div>

              {merchantDetail.onboarding_case ? (
                <>
                  <ContentCard title="Submitted profile JSON">
                    <JsonBlock value={merchantDetail.onboarding_case.submitted_profile_json} />
                  </ContentCard>
                  <ContentCard title="Documents JSON">
                    <JsonBlock value={merchantDetail.onboarding_case.documents_json} />
                  </ContentCard>
                  <ContentCard title="Review checks JSON">
                    <JsonBlock value={merchantDetail.onboarding_case.review_checks_json} />
                  </ContentCard>
                </>
              ) : (
                <EmptyState
                  title="No onboarding case yet"
                  message="Submit a readiness case above before making an approval decision."
                />
              )}

              <ContentCard title="Decision">
                <div className="form-grid">
                  <InlineField label="Decision reason">
                    <input
                      value={decisionReason}
                      onChange={(event) => setDecisionReason(event.target.value)}
                    />
                  </InlineField>
                  <label className="field field-span-two">
                    <span>Decision note</span>
                    <textarea
                      value={decisionNote}
                      onChange={(event) => setDecisionNote(event.target.value)}
                      rows={5}
                    />
                  </label>
                </div>
                <div className="inline-actions">
                  <button
                    type="button"
                    className="primary-button"
                    disabled={approveMutation.isPending || !decisionReason || !decisionNote}
                    onClick={() => approveMutation.mutate(selectedMerchantId)}
                  >
                    {approveMutation.isPending ? "Approving..." : "Approve case"}
                  </button>
                  <button
                    type="button"
                    className="danger-button"
                    disabled={rejectMutation.isPending || !decisionReason || !decisionNote}
                    onClick={() => rejectMutation.mutate(selectedMerchantId)}
                  >
                    {rejectMutation.isPending ? "Rejecting..." : "Reject case"}
                  </button>
                </div>
                {approveMutation.error instanceof Error ? (
                  <span className="feedback feedback-danger">
                    {approveMutation.error.message}
                  </span>
                ) : null}
                {rejectMutation.error instanceof Error ? (
                  <span className="feedback feedback-danger">
                    {rejectMutation.error.message}
                  </span>
                ) : null}
              </ContentCard>
            </div>
          ) : null}
        </ContentCard>
      </div>
    </section>
  );
}
