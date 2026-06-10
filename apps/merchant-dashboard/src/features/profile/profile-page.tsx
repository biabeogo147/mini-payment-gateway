import { useQuery } from "@tanstack/react-query";

import { getProfile } from "../common/api";
import { formatDateTime } from "../common/format";
import { ContentCard, DetailGrid, EmptyState, ErrorCard, PageHeader, StatusBadge } from "../common/ui";

export function ProfilePage() {
  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  });

  if (profileQuery.isLoading) {
    return (
      <section className="page-stack">
        <PageHeader
          eyebrow="Profile"
          title="Merchant Profile"
          description="Read-only merchant identity and integration configuration."
        />
        <ContentCard>
          <EmptyState title="Loading profile" message="Fetching merchant profile metadata." />
        </ContentCard>
      </section>
    );
  }

  if (profileQuery.error instanceof Error) {
    return <ErrorCard message={profileQuery.error.message} />;
  }

  const profile = profileQuery.data;
  if (!profile) {
    return <ErrorCard message="Profile is unavailable." />;
  }

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Profile"
        title="Merchant Profile"
        description="Read-only merchant identity and integration configuration."
      />
      <ContentCard title="Merchant information">
        <DetailGrid
          items={[
            { label: "Merchant id", value: profile.merchant_id },
            { label: "Merchant name", value: profile.merchant_name },
            { label: "Legal name", value: profile.legal_name ?? "N/A" },
            { label: "Status", value: <StatusBadge value={profile.status} /> },
            { label: "Contact email", value: profile.contact_email },
            { label: "Contact phone", value: profile.contact_phone ?? "N/A" },
            { label: "Webhook URL", value: profile.webhook_url ?? "N/A" },
            { label: "Allowed IPs", value: profile.allowed_ip_list?.join(", ") || "N/A" },
            { label: "Created", value: formatDateTime(profile.created_at) },
            { label: "Updated", value: formatDateTime(profile.updated_at) },
          ]}
        />
      </ContentCard>
    </section>
  );
}
