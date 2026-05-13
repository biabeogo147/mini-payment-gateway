import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  bootstrapInternalAuth,
  getBootstrapStatus,
  loginInternalAuth,
} from "../common/api";
import { ErrorCard, InlineField } from "../common/ui";
import { sessionQueryKey } from "../common/query";
import { useSession } from "./use-session";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: session, isLoading: sessionLoading } = useSession();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "bootstrap">("login");

  const bootstrapStatusQuery = useQuery({
    queryKey: ["bootstrap-status"],
    queryFn: getBootstrapStatus,
    retry: false,
  });

  const destination =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof location.state.from === "string"
      ? location.state.from
      : "/";

  const loginMutation = useMutation({
    mutationFn: loginInternalAuth,
    onSuccess: async (payload) => {
      queryClient.setQueryData(sessionQueryKey, payload);
      navigate(destination, { replace: true });
    },
  });

  const bootstrapMutation = useMutation({
    mutationFn: bootstrapInternalAuth,
    onSuccess: async (payload) => {
      queryClient.setQueryData(sessionQueryKey, payload);
      navigate("/", { replace: true });
    },
  });

  if (!sessionLoading && session) {
    return <Navigate to="/" replace />;
  }

  const bootstrapRequired = bootstrapStatusQuery.data?.bootstrap_required ?? false;
  const activeMode = bootstrapRequired ? "bootstrap" : mode;

  return (
    <div className="login-shell">
      <section className="login-card">
        <div>
          <p className="eyebrow">Phase 10 entry point</p>
          <h1>
            {activeMode === "bootstrap"
              ? "Bootstrap first admin"
              : "Internal operator login"}
          </h1>
          <p className="section-copy">
            Secure the ops console with an internal session. The first visit can
            bootstrap the initial admin; later visits use standard operator
            login.
          </p>
        </div>

        {bootstrapStatusQuery.error instanceof Error ? (
          <ErrorCard message={bootstrapStatusQuery.error.message} />
        ) : null}

        <div className="login-fields">
          {activeMode === "bootstrap" ? (
            <InlineField label="Full name">
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Admin User"
              />
            </InlineField>
          ) : null}

          <InlineField label="Email">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="ops@example.com"
            />
          </InlineField>

          <InlineField label="Password">
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter secure password"
            />
          </InlineField>
        </div>

        <div className="login-actions">
          {activeMode === "bootstrap" ? (
            <button
              type="button"
              className="primary-button"
              disabled={
                bootstrapMutation.isPending ||
                !email ||
                !fullName ||
                password.length < 8
              }
              onClick={() =>
                bootstrapMutation.mutate({
                  email,
                  full_name: fullName,
                  password,
                })
              }
            >
              {bootstrapMutation.isPending ? "Bootstrapping..." : "Create admin"}
            </button>
          ) : (
            <button
              type="button"
              className="primary-button"
              disabled={loginMutation.isPending || !email || !password}
              onClick={() => loginMutation.mutate({ email, password })}
            >
              {loginMutation.isPending ? "Signing in..." : "Sign in"}
            </button>
          )}

          {!bootstrapRequired ? (
            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                setMode((current) => (current === "login" ? "bootstrap" : "login"))
              }
            >
              {mode === "login" ? "Need bootstrap?" : "Back to login"}
            </button>
          ) : null}
        </div>

        {loginMutation.error instanceof Error ? (
          <span className="feedback feedback-danger">{loginMutation.error.message}</span>
        ) : null}
        {bootstrapMutation.error instanceof Error ? (
          <span className="feedback feedback-danger">
            {bootstrapMutation.error.message}
          </span>
        ) : null}
      </section>
    </div>
  );
}
