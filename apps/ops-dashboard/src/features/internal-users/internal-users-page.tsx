import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createInternalUser,
  listInternalUsers,
  resetInternalUserPassword,
  updateInternalUser,
  type InternalUserRole,
  type InternalUserStatus,
} from "../common/api";
import { formatDateTime } from "../common/format";
import { invalidateOpsConsoleData } from "../common/query";
import {
  ContentCard,
  EmptyState,
  ErrorCard,
  InlineField,
  PageHeader,
  StatusBadge,
} from "../common/ui";
import { useSession } from "../auth/use-session";

const roleOptions: InternalUserRole[] = ["ADMIN", "OPS"];
const statusOptions: InternalUserStatus[] = ["ACTIVE", "INACTIVE"];

export function InternalUsersPage() {
  const queryClient = useQueryClient();
  const { data: session } = useSession();
  const [createForm, setCreateForm] = useState({
    email: "",
    full_name: "",
    role: "OPS" as InternalUserRole,
    password: "",
    status: "ACTIVE" as InternalUserStatus,
  });
  const [resetPasswords, setResetPasswords] = useState<Record<string, string>>({});

  const usersQuery = useQuery({
    queryKey: ["internal-users"],
    queryFn: listInternalUsers,
    enabled: session?.user.role === "ADMIN",
  });

  const createMutation = useMutation({
    mutationFn: createInternalUser,
    onSuccess: async () => {
      await invalidateOpsConsoleData(queryClient);
      setCreateForm({
        email: "",
        full_name: "",
        role: "OPS",
        password: "",
        status: "ACTIVE",
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: {
        full_name?: string;
        role?: InternalUserRole;
        status?: InternalUserStatus;
      };
    }) => updateInternalUser(userId, payload),
    onSuccess: async () => invalidateOpsConsoleData(queryClient),
  });

  const resetMutation = useMutation({
    mutationFn: ({
      userId,
      newPassword,
    }: {
      userId: string;
      newPassword: string;
    }) => resetInternalUserPassword(userId, { new_password: newPassword }),
    onSuccess: async (_, variables) => {
      await invalidateOpsConsoleData(queryClient);
      setResetPasswords((current) => ({ ...current, [variables.userId]: "" }));
    },
  });

  if (session?.user.role !== "ADMIN") {
    return (
      <ErrorCard
        title="Admin access required"
        message="Only ADMIN users can manage internal operator accounts."
      />
    );
  }

  if (usersQuery.error instanceof Error) {
    return <ErrorCard message={usersQuery.error.message} />;
  }

  const users = usersQuery.data?.users ?? [];

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="Operator control"
        title="Internal users"
        description="Admin-only workspace for creating operators, adjusting role or status, and resetting internal passwords."
      />

      <ContentCard title="Create internal user">
        <div className="form-grid">
          <InlineField label="Email">
            <input
              value={createForm.email}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, email: event.target.value }))
              }
            />
          </InlineField>
          <InlineField label="Full name">
            <input
              value={createForm.full_name}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  full_name: event.target.value,
                }))
              }
            />
          </InlineField>
          <InlineField label="Role">
            <select
              value={createForm.role}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  role: event.target.value as InternalUserRole,
                }))
              }
            >
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Status">
            <select
              value={createForm.status}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  status: event.target.value as InternalUserStatus,
                }))
              }
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </InlineField>
          <InlineField label="Initial password">
            <input
              type="password"
              value={createForm.password}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  password: event.target.value,
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
              createMutation.isPending ||
              !createForm.email ||
              !createForm.full_name ||
              createForm.password.length < 8
            }
            onClick={() => createMutation.mutate(createForm)}
          >
            {createMutation.isPending ? "Creating..." : "Create user"}
          </button>
          {createMutation.error instanceof Error ? (
            <span className="feedback feedback-danger">
              {createMutation.error.message}
            </span>
          ) : null}
        </div>
      </ContentCard>

      <ContentCard title="Internal user list">
        {users.length === 0 ? (
          <EmptyState
            title="No internal users"
            message="Create the next operator account from the form above."
          />
        ) : (
          <div className="stack-list">
            {users.map((user) => (
              <article key={user.user_id} className="content-card nested-card">
                <div className="timeline-head">
                  <div>
                    <strong>{user.full_name}</strong>
                    <p>{user.email}</p>
                  </div>
                  <div className="stack-row-meta">
                    <StatusBadge value={user.role} />
                    <StatusBadge value={user.status} />
                  </div>
                </div>

                <div className="form-grid">
                  <InlineField label="Role">
                    <select
                      value={user.role}
                      onChange={(event) =>
                        updateMutation.mutate({
                          userId: user.user_id,
                          payload: { role: event.target.value as InternalUserRole },
                        })
                      }
                    >
                      {roleOptions.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </InlineField>
                  <InlineField label="Status">
                    <select
                      value={user.status}
                      onChange={(event) =>
                        updateMutation.mutate({
                          userId: user.user_id,
                          payload: {
                            status: event.target.value as InternalUserStatus,
                          },
                        })
                      }
                    >
                      {statusOptions.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </InlineField>
                  <InlineField label="Reset password">
                    <input
                      type="password"
                      value={resetPasswords[user.user_id] ?? ""}
                      onChange={(event) =>
                        setResetPasswords((current) => ({
                          ...current,
                          [user.user_id]: event.target.value,
                        }))
                      }
                    />
                  </InlineField>
                </div>

                <div className="inline-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={(resetPasswords[user.user_id] ?? "").length < 8}
                    onClick={() =>
                      resetMutation.mutate({
                        userId: user.user_id,
                        newPassword: resetPasswords[user.user_id] ?? "",
                      })
                    }
                  >
                    Reset password
                  </button>
                  <span className="section-copy">
                    Last login {formatDateTime(user.last_login_at)} · Updated{" "}
                    {formatDateTime(user.updated_at)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}

        {updateMutation.error instanceof Error ? (
          <span className="feedback feedback-danger">
            {updateMutation.error.message}
          </span>
        ) : null}
        {resetMutation.error instanceof Error ? (
          <span className="feedback feedback-danger">
            {resetMutation.error.message}
          </span>
        ) : null}
      </ContentCard>
    </section>
  );
}
