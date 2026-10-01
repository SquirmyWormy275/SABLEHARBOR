import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  currentIntegrity,
  traceIntegrity,
  type OriginalIntegrity,
} from "./procedureIntegrity";

const engagement = { id: "ENG-1", revision: 4 } as Engagement;
const report: OriginalIntegrity = {
  schema_version: "1.0",
  engagement_id: "ENG-1",
  engagement_revision: 4,
  status: "VERIFIED_RETAINED_BYTES_ONLY",
  metadata_status: "AVAILABLE",
  automatic_testing_credit: false,
  counts: {
    referenced: 1,
    verified: 1,
    missing: 0,
    integrity_failure: 0,
    read_unavailable: 0,
  },
  artifacts: [{ artifact_id: "ART-1", status: "VERIFIED_RETAINED_BYTES" }],
  traces: [
    {
      id: "TRACE-1",
      status: "VERIFIED_RETAINED_BYTES",
      artifact_ids: ["ART-1"],
    },
  ],
};

describe("retained original UI boundaries", () => {
  it("rejects a stale engagement revision and any credit claim", () => {
    expect(currentIntegrity(report, engagement)).toBe(true);
    expect(
      currentIntegrity({ ...report, engagement_revision: 3 }, engagement),
    ).toBe(false);
    expect(
      currentIntegrity(
        {
          ...report,
          automatic_testing_credit: true,
        } as unknown as OriginalIntegrity,
        engagement,
      ),
    ).toBe(false);
  });

  it("does not attach an ambiguous trace result to a procedure", () => {
    expect(traceIntegrity(report, "TRACE-1")?.status).toBe(
      "VERIFIED_RETAINED_BYTES",
    );
    expect(
      traceIntegrity(
        { ...report, traces: [...report.traces, report.traces[0]] },
        "TRACE-1",
      ),
    ).toBeNull();
  });
});
