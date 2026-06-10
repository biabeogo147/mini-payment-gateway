import { describe, expect, it, vi } from "vitest";

vi.mock("../features/analytics/analytics-page", () => {
  throw new Error("Analytics page should be lazy-loaded by the router.");
});

describe("merchant dashboard router", () => {
  it("does not import the analytics page in the initial route bundle", async () => {
    await expect(import("./router")).resolves.toHaveProperty("router");
  });
});
