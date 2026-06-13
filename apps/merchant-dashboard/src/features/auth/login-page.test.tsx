import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError, getCurrentSession, loginMerchantAuth } from "../common/api";
import { LoginPage } from "./login-page";

vi.mock("../common/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../common/api")>();
  return {
    ...actual,
    getCurrentSession: vi.fn(),
    loginMerchantAuth: vi.fn(),
  };
});

describe("LoginPage", () => {
  it("uses explicit label associations for merchant login fields", async () => {
    vi.mocked(getCurrentSession).mockRejectedValue(
      new ApiError("Merchant authentication is required.", {
        statusCode: 401,
        errorCode: "MERCHANT_AUTH_REQUIRED",
      }),
    );
    vi.mocked(loginMerchantAuth).mockRejectedValue(new Error("not used"));

    const { container } = renderLogin();

    expect((await screen.findByLabelText("Merchant ID")).getAttribute("id")).toBe(
      "merchant-login-merchant-id",
    );
    expect(screen.getByLabelText("Email").getAttribute("id")).toBe(
      "merchant-login-email",
    );
    expect(screen.getByLabelText("Password").getAttribute("id")).toBe(
      "merchant-login-password",
    );
    expect(container.querySelector('label[for="merchant-login-merchant-id"]')).toBeTruthy();
    expect(container.querySelector('label[for="merchant-login-email"]')).toBeTruthy();
    expect(container.querySelector('label[for="merchant-login-password"]')).toBeTruthy();
  });
});

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter
      initialEntries={["/login"]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
