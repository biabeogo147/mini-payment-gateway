import { useQuery } from "@tanstack/react-query";

import { listCredentials } from "../common/api";
import { formatDateTime } from "../common/format";
import { ContentCard, EmptyState, ErrorCard, PageHeader, StatusBadge } from "../common/ui";

export function CredentialsPage() {
  const credentialsQuery = useQuery({
    queryKey: ["credentials"],
    queryFn: listCredentials,
  });

  if (credentialsQuery.isLoading) {
    return (
      <section className="page-stack">
        <PageHeader
          eyebrow="Credentials"
          title="Credential Metadata"
          description="Read-only credential status and rotation metadata."
        />
        <ContentCard>
          <EmptyState title="Loading credentials" message="Fetching credential metadata." />
        </ContentCard>
      </section>
    );
  }

  if (credentialsQuery.error instanceof Error) {
    return <ErrorCard message={credentialsQuery.error.message} />;
  }

  const credentials = credentialsQuery.data?.credentials ?? [];

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Credentials"
        title="Credential Metadata"
        description="Read-only credential status and rotation metadata."
      />
      <ContentCard title="Credentials">
        {credentials.length === 0 ? (
          <EmptyState title="No credentials" message="No credential metadata is available for this merchant." />
        ) : (
          <div
            className="stack-list scrollable-list credential-list"
            role="list"
            aria-label="Credential metadata"
          >
            {credentials.map((credential) => (
              <article key={credential.credential_id} className="stack-row" role="listitem">
                <div>
                  <strong>{credential.access_key}</strong>
                  <p>Secret suffix: {credential.secret_key_last4}</p>
                </div>
                <div className="stack-row-meta">
                  <StatusBadge value={credential.status} />
                  <span>Created {formatDateTime(credential.created_at)}</span>
                  <span>Rotated {formatDateTime(credential.rotated_at)}</span>
                  <span>Expires {formatDateTime(credential.expired_at)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </ContentCard>
    </section>
  );
}
