import { describe, it, expect } from "vitest";
import {
  impactContext,
  validateImpact,
  type ImpactReport,
} from "./sourceImpact";
import type { Engagement } from "./api";
const e = {
  id: "E",
  revision: 4,
  simulated_at: "2027-12-31",
  artifacts: [{ id: "A" }],
  scope: {},
  permissions: ["learn"],
} as Engagement;
const report = {
  engagement_id: "E",
  engagement_revision: 4,
  simulated_as_of: "2027-12-31",
  changes: [{ id: "x", artifact_id: "A", references: [] }],
  compared_artifacts: 2,
  unavailable_comparisons: 3,
  snapshot_isolation: "PER_SOURCE_OPERATION_NOT_GLOBAL",
  limitations: [],
  started_at: "2026-01-01",
  completed_at: "2026-01-01",
} as ImpactReport;
describe("source impact report pins", () => {
  it("keeps unavailable separate from successfully compared artifacts", () => {
    expect(validateImpact(report, e).unavailable_comparisons).toBe(3);
    expect(validateImpact(report, e).compared_artifacts).toBe(2);
  });
  it("rejects stale, wrong engagement or cutoff results", () => {
    for (const delta of [
      { engagement_id: "OTHER" },
      { engagement_revision: 3 },
      { simulated_as_of: "2026-01-01" },
    ])
      expect(() => validateImpact({ ...report, ...delta }, e)).toThrow(
        /outdated/,
      );
  });
  it("rejects invalid counts and out of workspace references", () => {
    expect(() =>
      validateImpact({ ...report, compared_artifacts: 0 }, e),
    ).toThrow();
    expect(() =>
      validateImpact({ ...report, unavailable_comparisons: -1 }, e),
    ).toThrow();
    expect(() =>
      validateImpact(
        {
          ...report,
          changes: [{ id: "x", artifact_id: "OTHER", references: [] }],
        },
        e,
      ),
    ).toThrow();
  });
  it("invalidates context on role, binding and acquisition changes even at same revision", () => {
    for (const delta of [
      { permissions: ["review"] },
      { company_source_binding: { branch: "other" } },
      { evidence_acquisition: { mode: "other" } },
    ])
      expect(impactContext({ ...e, ...delta } as Engagement)).not.toBe(
        impactContext(e),
      );
  });
});
