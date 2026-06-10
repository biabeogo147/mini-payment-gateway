import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { loginMerchantAuth } from "../common/api";
import { sessionQueryKey } from "../common/query";
import { InlineField } from "../common/ui";
import { useSession } from "./use-session";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: session, isLoading } = useSession();
  const [merchantId, setMerchantId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const destination =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof location.state.from === "string"
      ? location.state.from
      : "/";

  const loginMutation = useMutation({
    mutationFn: loginMerchantAuth,
    onSuccess: async (payload) => {
      queryClient.setQueryData(sessionQueryKey, payload);
      navigate(destination, { replace: true });
    },
  });

  if (!isLoading && session) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="login-shell">
      <section className="login-card">
        <div>
          <p className="eyebrow">Merchant access</p>
          <h1>Merchant Dashboard</h1>
          <p className="section-copy">
            Sign in to inspect payment, refund, webhook, and integration data for
            your merchant account.
          </p>
        </div>

        <div className="login-fields">
          <InlineField label="Merchant ID">
            <input
              value={merchantId}
              onChange={(event) => setMerchantId(event.target.value)}
              placeholder="m_demo_dashboard"
            />
          </InlineField>
          <InlineField label="Email">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="merchant@example.com"
            />
          </InlineField>
          <InlineField label="Password">
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
            />
          </InlineField>
        </div>

        <div className="login-actions">
          <button
            type="button"
            className="primary-button"
            disabled={loginMutation.isPending || !merchantId || !email || !password}
            onClick={() =>
              loginMutation.mutate({
                merchant_id: merchantId,
                email,
                password,
              })
            }
          >
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </button>
          {loginMutation.error instanceof Error ? (
            <span className="feedback feedback-danger">
              {loginMutation.error.message}
            </span>
          ) : null}
        </div>
      </section>
    </div>
  );
}
