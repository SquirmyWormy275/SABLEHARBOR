import { describe, it, expect } from "vitest";
import { jobAction, jobsPath } from "./backgroundWork";
import type { BackgroundJob } from "./backgroundWork";
describe("background recovery", () => {
  it("never retries completed, running or conflicted commands", () => {
    for (const status of ["COMPLETED", "RUNNING", "CONFLICTED"] as const)
      expect(jobAction({ status } as BackgroundJob)).toBeNull();
  });
  it("requires distinct pending start and explicit interrupted retry", () => {
    expect(jobAction({ status: "PENDING" } as BackgroundJob)).toBe("start");
    for (const status of ["FAILED", "INTERRUPTED"] as const)
      expect(jobAction({ status } as BackgroundJob)).toBe("retry");
  });
  it("encodes exact engagement path", () =>
    expect(jobsPath("a/b")).toBe("/api/engagements/a%2Fb/jobs"));
});
