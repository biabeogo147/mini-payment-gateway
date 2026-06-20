// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PortalUserRoleSelect } from "./portal-user-role-select";

describe("PortalUserRoleSelect", () => {
  it("lets an operator change an existing portal user's role", () => {
    const onChange = vi.fn();

    render(
      <PortalUserRoleSelect
        disabled={false}
        email="merchant@example.com"
        role="MERCHANT_VIEWER"
        onChange={onChange}
      />,
    );

    fireEvent.change(
      screen.getByRole("combobox", { name: "Role for merchant@example.com" }),
      { target: { value: "MERCHANT_ADMIN" } },
    );

    expect(onChange).toHaveBeenCalledWith("MERCHANT_ADMIN");
  });
});
