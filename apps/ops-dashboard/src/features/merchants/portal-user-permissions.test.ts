import { describe, expect, it } from "vitest";

import { canManageMerchantPortalUsers } from "./portal-user-permissions";

describe("merchant portal user permissions", () => {
  it.each(["ADMIN", "OPS"] as const)("allows %s to manage portal users", (role) => {
    expect(canManageMerchantPortalUsers(role)).toBe(true);
  });

  it("rejects an unauthenticated session", () => {
    expect(canManageMerchantPortalUsers(undefined)).toBe(false);
  });
});
